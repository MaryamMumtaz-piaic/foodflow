from typing import Optional

from pydantic import BaseModel, Field


class RestaurantCreate(BaseModel):
    name: str
    description: str = ""
    cuisine_types: list[str] = Field(default_factory=list)
    address: str
    city: str = "Karachi"
    delivery_fee: float = 99.0
    minimum_order: float = 500.0
    estimated_delivery_time_minutes: int = 35
    phone: Optional[str] = None
    email: Optional[str] = None
    logo: Optional[str] = None
    cover_image: Optional[str] = None


class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cuisine_types: Optional[list[str]] = None
    address: Optional[str] = None
    city: Optional[str] = None
    delivery_fee: Optional[float] = None
    minimum_order: Optional[float] = None
    estimated_delivery_time_minutes: Optional[int] = None
    opening_hours: Optional[dict] = None
    availability_status: Optional[bool] = None
    is_open: Optional[bool] = None
    logo: Optional[str] = None
    cover_image: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class ReviewCreate(BaseModel):
    order_id: Optional[str] = None
    rating: int = Field(ge=1, le=5)
    comment: str = ""


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = None
    moderation_status: Optional[str] = None
