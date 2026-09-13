from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user, require_role
from app.schemas.order import OrderCancelRequest, OrderCreateRequest, OrderStatusUpdateRequest
from app.services import order_service
from app.utils.json_store import addresses_store
from app.utils.validation import is_valid_phone

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", status_code=201)
def create_order(payload: OrderCreateRequest, user: dict = Depends(require_role("customer"))):
    delivery_address = payload.delivery_address
    if payload.address_id:
        addr = addresses_store.get(payload.address_id)
        if not addr or addr["user_id"] != user["id"]:
            raise HTTPException(status_code=404, detail="Address not found.")
        delivery_address = addr
    if not delivery_address:
        raise HTTPException(status_code=422, detail="A delivery address is required.")

    if payload.contact_phone and not is_valid_phone(payload.contact_phone):
        raise HTTPException(status_code=422, detail="Invalid contact phone number.")

    raw_items = [i.model_dump() for i in payload.items] if payload.items else None

    try:
        order = order_service.create_order(
            customer_id=user["id"],
            raw_items=raw_items,
            delivery_address=delivery_address,
            contact_phone=payload.contact_phone,
            delivery_instructions=payload.delivery_instructions,
            coupon_code=payload.coupon_code,
            payment_method=payload.payment_method,
            restaurant_id_hint=payload.restaurant_id,
        )
    except order_service.OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    return order


@router.get("")
def list_orders(user: dict = Depends(get_current_user)):
    return order_service.list_orders_for_user(user)


@router.get("/{order_id}")
def get_order(order_id: str, user: dict = Depends(get_current_user)):
    order = order_service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    if not order_service.can_view_order(user, order):
        raise HTTPException(status_code=403, detail="You do not have access to this order.")
    return order


@router.patch("/{order_id}/status")
def update_status(order_id: str, payload: OrderStatusUpdateRequest, user: dict = Depends(require_role("restaurant", "admin", "rider"))):
    order = order_service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    if not order_service.can_view_order(user, order):
        raise HTTPException(status_code=403, detail="You do not manage this order.")
    try:
        return order_service.update_order_status(order_id, payload.status, user, payload.reason)
    except order_service.OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.post("/{order_id}/cancel")
def cancel_order(order_id: str, payload: OrderCancelRequest, user: dict = Depends(get_current_user)):
    order = order_service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    if not order_service.can_view_order(user, order):
        raise HTTPException(status_code=403, detail="You do not have access to this order.")
    try:
        return order_service.cancel_order(order_id, user, payload.reason)
    except order_service.OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.post("/{order_id}/reorder", status_code=201)
def reorder(order_id: str, user: dict = Depends(require_role("customer"))):
    try:
        return order_service.reorder(order_id, user["id"])
    except order_service.OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
