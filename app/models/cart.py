from typing import Optional

from pydantic import BaseModel, Field


class CartItem(BaseModel):
    menu_item_id: str
    restaurant_id: str
    name: str
    quantity: int = 1
    selected_add_ons: list[str] = Field(default_factory=list)
    special_instructions: Optional[str] = None
    unit_price: float
    total_price: float


class Cart(BaseModel):
    user_id: str
    restaurant_id: Optional[str] = None
    items: list[CartItem] = Field(default_factory=list)
    coupon_code: Optional[str] = None
