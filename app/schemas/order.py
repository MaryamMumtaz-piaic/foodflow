from typing import Optional

from pydantic import BaseModel, Field

from app.models.order import OrderStatus, PaymentMethod


class CartItemInput(BaseModel):
    menu_item_id: str
    quantity: int = Field(gt=0, default=1)
    selected_add_ons: list[str] = Field(default_factory=list)
    special_instructions: Optional[str] = None


class AddCartItemRequest(CartItemInput):
    pass


class UpdateCartItemRequest(BaseModel):
    quantity: Optional[int] = Field(default=None, gt=0)
    selected_add_ons: Optional[list[str]] = None
    special_instructions: Optional[str] = None


class OrderCreateRequest(BaseModel):
    """Order is created from the server-side cart; client may optionally
    submit items directly (e.g. reorder), but prices are ALWAYS
    recalculated server-side and never trusted from the client."""
    restaurant_id: Optional[str] = None
    items: Optional[list[CartItemInput]] = None
    address_id: Optional[str] = None
    delivery_address: Optional[dict] = None
    contact_phone: Optional[str] = None
    delivery_instructions: Optional[str] = None
    coupon_code: Optional[str] = None
    payment_method: PaymentMethod = PaymentMethod.cash_on_delivery


class OrderStatusUpdateRequest(BaseModel):
    status: OrderStatus
    reason: Optional[str] = None


class OrderCancelRequest(BaseModel):
    reason: Optional[str] = None
