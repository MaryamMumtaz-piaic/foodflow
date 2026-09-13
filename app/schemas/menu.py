from typing import Optional

from pydantic import BaseModel, Field

from app.models.menu import AddOn, DietaryLabel, SpiceLevel


class MenuItemCreate(BaseModel):
    category_id: str
    name: str
    description: str = ""
    price: float = Field(gt=0)
    promotional_price: Optional[float] = None
    ingredients: list[str] = Field(default_factory=list)
    allergens: list[str] = Field(default_factory=list)
    dietary_labels: list[DietaryLabel] = Field(default_factory=list)
    spice_level: SpiceLevel = SpiceLevel.none
    portion_size: str = "Regular"
    add_ons: list[AddOn] = Field(default_factory=list)
    image: Optional[str] = None
    is_available: bool = True


class MenuItemUpdate(BaseModel):
    category_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    promotional_price: Optional[float] = None
    ingredients: Optional[list[str]] = None
    allergens: Optional[list[str]] = None
    dietary_labels: Optional[list[DietaryLabel]] = None
    spice_level: Optional[SpiceLevel] = None
    portion_size: Optional[str] = None
    add_ons: Optional[list[AddOn]] = None
    image: Optional[str] = None
    is_available: Optional[bool] = None


class AvailabilityUpdate(BaseModel):
    is_available: bool


class CategoryCreate(BaseModel):
    name: str
    description: str = ""
    display_order: int = 0


class CouponCreate(BaseModel):
    code: str
    discount_type: str  # percentage | fixed
    discount_value: float
    minimum_order_value: float = 0.0
    maximum_discount: Optional[float] = None
    expiry_date: str
    usage_limit: int = 100
    restaurant_id: Optional[str] = None
    is_active: bool = True


class CouponUpdate(BaseModel):
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    minimum_order_value: Optional[float] = None
    maximum_discount: Optional[float] = None
    expiry_date: Optional[str] = None
    usage_limit: Optional[int] = None
    is_active: Optional[bool] = None


class CouponValidateRequest(BaseModel):
    code: str
    subtotal: float
    restaurant_id: Optional[str] = None


class CouponValidateResponse(BaseModel):
    valid: bool
    reason: Optional[str] = None
    discount_amount: float = 0.0
    coupon_code: Optional[str] = None
