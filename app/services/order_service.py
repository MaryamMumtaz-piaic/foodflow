"""Order lifecycle business logic.

Enforces the Section 13 order-status state machine strictly and always
recalculates prices server-side (Section 18) — client-submitted prices
are never trusted.
"""
from datetime import datetime
from typing import Optional

from app.models.order import OrderStatus, PaymentMethod, PaymentStatus
from app.services import coupon_service, delivery_service, payment_service
from app.services.payment_service import PaymentDeclined
from app.utils.json_store import (
    carts_store,
    menu_items_store,
    orders_store,
    restaurants_store,
)
from app.utils.pricing import compute_breakdown, compute_item_total
from app.utils.status_rules import StatusTransitionError, can_cancel, validate_transition
from app.utils.validation import new_id


class OrderError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.status_code = status_code
        super().__init__(message)


def _price_cart_items(raw_items: list[dict]) -> tuple[list[dict], float, str]:
    """Given [{menu_item_id, quantity, selected_add_ons, special_instructions}],
    look up authoritative prices and build priced cart-item dicts. Returns
    (priced_items, subtotal, restaurant_id)."""
    if not raw_items:
        raise OrderError("Cart is empty.")

    priced_items = []
    subtotal = 0.0
    restaurant_id = None

    for raw in raw_items:
        item = menu_items_store.get(raw["menu_item_id"])
        if not item:
            raise OrderError(f"Menu item {raw['menu_item_id']} not found.")
        if not item.get("is_available", True):
            raise OrderError(f"'{item['name']}' is currently unavailable.")
        if restaurant_id is None:
            restaurant_id = item["restaurant_id"]
        elif restaurant_id != item["restaurant_id"]:
            raise OrderError("All items in one order must belong to the same restaurant.")

        unit_price = item.get("promotional_price") or item["price"]
        add_on_lookup = {a["id"]: a["price"] for a in item.get("add_ons", [])}
        selected_add_ons = raw.get("selected_add_ons", [])
        add_on_prices = [add_on_lookup[a] for a in selected_add_ons if a in add_on_lookup]
        quantity = raw.get("quantity", 1)
        total_price = compute_item_total(unit_price, quantity, add_on_prices)
        subtotal += total_price

        priced_items.append({
            "menu_item_id": item["id"],
            "restaurant_id": item["restaurant_id"],
            "name": item["name"],
            "quantity": quantity,
            "selected_add_ons": selected_add_ons,
            "special_instructions": raw.get("special_instructions"),
            "unit_price": unit_price,
            "total_price": total_price,
        })

    return priced_items, round(subtotal, 2), restaurant_id


def get_cart(user_id: str) -> dict:
    cart = carts_store.get(user_id, id_field="user_id")
    if not cart:
        cart = {"user_id": user_id, "restaurant_id": None, "items": [], "coupon_code": None}
        carts_store.create(cart)
    return cart


def price_cart(cart: dict) -> dict:
    """Returns cart with server-computed breakdown, safe to show to client."""
    items = cart.get("items", [])
    if not items:
        return {
            "items": [],
            "subtotal": 0.0,
            "delivery_fee": 0.0,
            "discount": 0.0,
            "tax": 0.0,
            "final_total": 0.0,
            "coupon_code": cart.get("coupon_code"),
        }
    subtotal = round(sum(i["total_price"] for i in items), 2)
    restaurant_id = cart.get("restaurant_id")
    restaurant = restaurants_store.get(restaurant_id) if restaurant_id else None
    delivery_fee = restaurant.get("delivery_fee", 99.0) if restaurant else 99.0

    discount = 0.0
    coupon_code = cart.get("coupon_code")
    if coupon_code:
        try:
            _, discount = coupon_service.validate_coupon(coupon_code, subtotal, restaurant_id)
        except coupon_service.CouponError:
            discount = 0.0

    breakdown = compute_breakdown(subtotal, delivery_fee, discount)
    return {
        "items": items,
        "subtotal": breakdown.subtotal,
        "delivery_fee": breakdown.delivery_fee,
        "discount": breakdown.discount,
        "tax": breakdown.tax,
        "final_total": breakdown.final_total,
        "coupon_code": coupon_code,
    }


def add_cart_item(user_id: str, menu_item_id: str, quantity: int, selected_add_ons: list[str], special_instructions: Optional[str]) -> dict:
    item = menu_items_store.get(menu_item_id)
    if not item:
        raise OrderError("Menu item not found.", 404)
    if not item.get("is_available", True):
        raise OrderError(f"'{item['name']}' is currently unavailable.")

    cart = get_cart(user_id)
    if cart.get("items") and cart.get("restaurant_id") and cart["restaurant_id"] != item["restaurant_id"]:
        # Starting a new restaurant clears the previous cart (common food-delivery UX)
        cart["items"] = []

    priced_items, _, _ = _price_cart_items([{
        "menu_item_id": menu_item_id,
        "quantity": quantity,
        "selected_add_ons": selected_add_ons,
        "special_instructions": special_instructions,
    }])
    cart_items = cart.get("items", [])
    cart_items.append(priced_items[0])
    cart["items"] = cart_items
    cart["restaurant_id"] = item["restaurant_id"]
    carts_store.replace(user_id, cart, id_field="user_id")
    return cart


def update_cart_item(user_id: str, menu_item_id: str, quantity: Optional[int], selected_add_ons: Optional[list[str]], special_instructions: Optional[str]) -> dict:
    cart = get_cart(user_id)
    items = cart.get("items", [])
    match_idx = None
    for i, ci in enumerate(items):
        if ci["menu_item_id"] == menu_item_id:
            match_idx = i
            break
    if match_idx is None:
        raise OrderError("Item not found in cart.", 404)

    existing = items[match_idx]
    new_quantity = quantity if quantity is not None else existing["quantity"]
    new_add_ons = selected_add_ons if selected_add_ons is not None else existing["selected_add_ons"]
    new_instructions = special_instructions if special_instructions is not None else existing["special_instructions"]

    priced_items, _, _ = _price_cart_items([{
        "menu_item_id": menu_item_id,
        "quantity": new_quantity,
        "selected_add_ons": new_add_ons,
        "special_instructions": new_instructions,
    }])
    items[match_idx] = priced_items[0]
    cart["items"] = items
    carts_store.replace(user_id, cart, id_field="user_id")
    return cart


def remove_cart_item(user_id: str, menu_item_id: str) -> dict:
    cart = get_cart(user_id)
    items = [i for i in cart.get("items", []) if i["menu_item_id"] != menu_item_id]
    cart["items"] = items
    if not items:
        cart["restaurant_id"] = None
        cart["coupon_code"] = None
    carts_store.replace(user_id, cart, id_field="user_id")
    return cart


def clear_cart(user_id: str) -> dict:
    cart = {"user_id": user_id, "restaurant_id": None, "items": [], "coupon_code": None}
    carts_store.replace(user_id, cart, id_field="user_id")
    return cart


def create_order(
    customer_id: str,
    raw_items: Optional[list[dict]],
    delivery_address: dict,
    contact_phone: Optional[str],
    delivery_instructions: Optional[str],
    coupon_code: Optional[str],
    payment_method: PaymentMethod,
    restaurant_id_hint: Optional[str] = None,
) -> dict:
    # Use provided items (e.g. reorder) or fall back to the user's server-side cart.
    if raw_items:
        priced_items, subtotal, restaurant_id = _price_cart_items(raw_items)
    else:
        cart = get_cart(customer_id)
        priced_items, subtotal, restaurant_id = _price_cart_items(cart.get("items", []))
        coupon_code = coupon_code or cart.get("coupon_code")

    restaurant_id = restaurant_id or restaurant_id_hint
    restaurant = restaurants_store.get(restaurant_id)
    if not restaurant:
        raise OrderError("Restaurant not found.", 404)
    if not restaurant.get("availability_status", True) or not restaurant.get("is_open", True):
        raise OrderError("This restaurant is currently not accepting orders.")

    discount = 0.0
    valid_coupon_code = None
    if coupon_code:
        try:
            _, discount = coupon_service.validate_coupon(coupon_code, subtotal, restaurant_id)
            valid_coupon_code = coupon_code
        except coupon_service.CouponError as e:
            raise OrderError(str(e))

    breakdown = compute_breakdown(subtotal, restaurant.get("delivery_fee", 99.0), discount)

    # Payment must be permitted/confirmed before the order is created.
    try:
        payment_status = payment_service.process_payment(payment_method, breakdown.final_total)
    except PaymentDeclined as e:
        raise OrderError(str(e), 402)

    order_id = new_id("ord_")
    now = datetime.utcnow().isoformat()
    order = {
        "id": order_id,
        "customer_id": customer_id,
        "restaurant_id": restaurant_id,
        "rider_id": None,
        "items": priced_items,
        "delivery_address": delivery_address,
        "contact_phone": contact_phone,
        "delivery_instructions": delivery_instructions,
        "subtotal": breakdown.subtotal,
        "delivery_fee": breakdown.delivery_fee,
        "discount": breakdown.discount,
        "tax": breakdown.tax,
        "final_total": breakdown.final_total,
        "coupon_code": valid_coupon_code,
        "payment_method": payment_method.value if isinstance(payment_method, PaymentMethod) else payment_method,
        "payment_status": payment_status.value if isinstance(payment_status, PaymentStatus) else payment_status,
        "status": OrderStatus.pending.value,
        "rejection_reason": None,
        "cancellation_reason": None,
        "estimated_delivery_time_minutes": restaurant.get("estimated_delivery_time_minutes", 40),
        "created_at": now,
        "updated_at": now,
    }
    orders_store.create(order)

    if valid_coupon_code:
        coupon_service.mark_coupon_used(valid_coupon_code)

    # Clear the customer's cart after successful order placement
    clear_cart(customer_id)

    return order


def list_orders_for_user(user: dict) -> list[dict]:
    role = user.get("role")
    if role == "customer":
        return sorted(orders_store.find_many(lambda o: o["customer_id"] == user["id"]), key=lambda o: o["created_at"], reverse=True)
    if role == "restaurant":
        return sorted(orders_store.find_many(lambda o: o["restaurant_id"] == user.get("restaurant_id")), key=lambda o: o["created_at"], reverse=True)
    if role == "rider":
        return sorted(orders_store.find_many(lambda o: o.get("rider_id") == user["id"]), key=lambda o: o["created_at"], reverse=True)
    # admin
    return sorted(orders_store.list_all(), key=lambda o: o["created_at"], reverse=True)


def get_order(order_id: str) -> Optional[dict]:
    return orders_store.get(order_id)


def can_view_order(user: dict, order: dict) -> bool:
    role = user.get("role")
    if role == "admin":
        return True
    if role == "customer":
        return order["customer_id"] == user["id"]
    if role == "restaurant":
        return order["restaurant_id"] == user.get("restaurant_id")
    if role == "rider":
        return order.get("rider_id") == user["id"]
    return False


def update_order_status(order_id: str, target_status: OrderStatus, actor: dict, reason: Optional[str] = None) -> dict:
    order = orders_store.get(order_id)
    if not order:
        raise OrderError("Order not found.", 404)

    current_status = OrderStatus(order["status"])
    try:
        validate_transition(current_status, target_status)
    except StatusTransitionError as e:
        raise OrderError(str(e))

    patch = {"status": target_status.value, "updated_at": datetime.utcnow().isoformat()}
    if target_status == OrderStatus.rejected:
        patch["rejection_reason"] = reason or "Rejected by restaurant."
    if target_status == OrderStatus.cancelled:
        patch["cancellation_reason"] = reason or "Cancelled."

    updated = orders_store.update(order_id, patch)

    if target_status == OrderStatus.ready_for_pickup:
        restaurant = restaurants_store.get(order["restaurant_id"])
        delivery_service.create_delivery_for_order(updated, restaurant or {})

    return updated


def cancel_order(order_id: str, actor: dict, reason: Optional[str]) -> dict:
    order = orders_store.get(order_id)
    if not order:
        raise OrderError("Order not found.", 404)
    current_status = OrderStatus(order["status"])
    if not can_cancel(current_status):
        raise OrderError(f"Order in status '{current_status.value}' can no longer be cancelled.")
    return update_order_status(order_id, OrderStatus.cancelled, actor, reason)


def reorder(order_id: str, customer_id: str) -> dict:
    original = orders_store.get(order_id)
    if not original:
        raise OrderError("Order not found.", 404)
    if original["customer_id"] != customer_id:
        raise OrderError("You can only reorder your own past orders.", 403)

    raw_items = [
        {
            "menu_item_id": i["menu_item_id"],
            "quantity": i["quantity"],
            "selected_add_ons": i.get("selected_add_ons", []),
            "special_instructions": i.get("special_instructions"),
        }
        for i in original["items"]
    ]
    return create_order(
        customer_id=customer_id,
        raw_items=raw_items,
        delivery_address=original["delivery_address"],
        contact_phone=original.get("contact_phone"),
        delivery_instructions=original.get("delivery_instructions"),
        coupon_code=None,
        payment_method=PaymentMethod(original.get("payment_method", "cash_on_delivery")),
    )
