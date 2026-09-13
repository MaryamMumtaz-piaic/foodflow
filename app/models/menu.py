from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SpiceLevel(str, Enum):
    none = "none"
    mild = "mild"
    medium = "medium"
    hot = "hot"
    extra_hot = "extra_hot"


class DietaryLabel(str, Enum):
    vegetarian = "vegetarian"
    vegan = "vegan"
    halal = "halal"
    gluten_free = "gluten_free"
    dairy_free = "dairy_free"
    nut_free = "nut_free"
    keto = "keto"
    non_vegetarian = "non_vegetarian"


class MenuCategory(BaseModel):
    id: str
    restaurant_id: str
    name: str
    description: str = ""
    display_order: int = 0


class AddOn(BaseModel):
    id: str
    name: str
    price: float = 0.0


class MenuItem(BaseModel):
    id: str
    restaurant_id: str
    category_id: str
    name: str
    description: str = ""
    image: str = "/static/images/food/default-food.png"
    price: float
    promotional_price: Optional[float] = None
    ingredients: list[str] = Field(default_factory=list)
    allergens: list[str] = Field(default_factory=list)
    dietary_labels: list[DietaryLabel] = Field(default_factory=list)
    spice_level: SpiceLevel = SpiceLevel.none
    portion_size: str = "Regular"
    add_ons: list[AddOn] = Field(default_factory=list)
    is_available: bool = True
    rating: float = 0.0
    order_count: int = 0


class Coupon(BaseModel):
    id: str
    code: str
    discount_type: str  # "percentage" | "fixed"
    discount_value: float
    minimum_order_value: float = 0.0
    maximum_discount: Optional[float] = None
    expiry_date: str
    usage_limit: int = 100
    used_count: int = 0
    is_active: bool = True
    restaurant_id: Optional[str] = None  # None => platform-wide coupon
