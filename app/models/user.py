from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    customer = "customer"
    restaurant = "restaurant"
    rider = "rider"
    admin = "admin"


class AccountStatus(str, Enum):
    active = "active"
    suspended = "suspended"
    pending = "pending"


class User(BaseModel):
    id: str
    name: str
    email: EmailStr
    password_hash: str
    role: UserRole
    phone: Optional[str] = None
    status: AccountStatus = AccountStatus.active
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Optional linkage fields for role-specific records
    restaurant_id: Optional[str] = None  # set when role == restaurant
    rider_online: Optional[bool] = False  # set when role == rider
    rider_approved: Optional[bool] = True
    favorites_restaurants: list[str] = Field(default_factory=list)
    favorites_meals: list[str] = Field(default_factory=list)


class Address(BaseModel):
    id: str
    user_id: str
    label: str = "Home"
    recipient_name: str
    phone: str
    street_address: str
    area: Optional[str] = None
    city: str
    delivery_instructions: Optional[str] = None
    is_default: bool = False
