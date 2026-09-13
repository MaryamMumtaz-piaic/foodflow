from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import require_role
from app.schemas.order import AddCartItemRequest, UpdateCartItemRequest
from app.services import order_service

router = APIRouter(prefix="/api/cart", tags=["cart"])


@router.get("")
def get_cart(user: dict = Depends(require_role("customer"))):
    cart = order_service.get_cart(user["id"])
    return order_service.price_cart(cart)


@router.post("/items")
def add_item(payload: AddCartItemRequest, user: dict = Depends(require_role("customer"))):
    try:
        order_service.add_cart_item(
            user["id"], payload.menu_item_id, payload.quantity, payload.selected_add_ons, payload.special_instructions
        )
    except order_service.OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    return order_service.price_cart(order_service.get_cart(user["id"]))


@router.put("/items/{item_id}")
def update_item(item_id: str, payload: UpdateCartItemRequest, user: dict = Depends(require_role("customer"))):
    try:
        order_service.update_cart_item(
            user["id"], item_id, payload.quantity, payload.selected_add_ons, payload.special_instructions
        )
    except order_service.OrderError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    return order_service.price_cart(order_service.get_cart(user["id"]))


@router.delete("/items/{item_id}")
def remove_item(item_id: str, user: dict = Depends(require_role("customer"))):
    order_service.remove_cart_item(user["id"], item_id)
    return order_service.price_cart(order_service.get_cart(user["id"]))


@router.delete("")
def clear_cart(user: dict = Depends(require_role("customer"))):
    order_service.clear_cart(user["id"])
    return order_service.price_cart(order_service.get_cart(user["id"]))
