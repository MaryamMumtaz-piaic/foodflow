from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    suspended = "suspended"


class OpeningHours(BaseModel):
    open: str = "09:00"
    close: str = "23:00"


class Restaurant(BaseModel):
    id: str
    name: str
    description: str = ""
    logo: str = "/static/images/restaurants/default-logo.png"
    cover_image: str = "/static/images/restaurants/default-cover.png"
    cuisine_types: list[str] = Field(default_factory=list)
    address: str
    city: str = "Karachi"
    rating: float = 0.0
    review_count: int = 0
    delivery_fee: float = 99.0
    minimum_order: float = 500.0
    estimated_delivery_time_minutes: int = 35
    opening_hours: OpeningHours = Field(default_factory=OpeningHours)
    is_open: bool = True
    availability_status: bool = True
    approval_status: ApprovalStatus = ApprovalStatus.approved
    owner_user_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    popular_dish: Optional[str] = None
    price_range: str = "$$"
    created_at: datetime = Field(default_factory=datetime.utcnow)
