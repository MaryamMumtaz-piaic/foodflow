from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: UserRole = UserRole.customer
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    phone: Optional[str] = None
    status: str
    restaurant_id: Optional[str] = None


class AuthResponse(BaseModel):
    token: str
    user: UserPublic


class AddressCreate(BaseModel):
    label: str = "Home"
    recipient_name: str
    phone: str
    street_address: str
    area: Optional[str] = None
    city: str
    delivery_instructions: Optional[str] = None
    is_default: bool = False


class AddressUpdate(BaseModel):
    label: Optional[str] = None
    recipient_name: Optional[str] = None
    phone: Optional[str] = None
    street_address: Optional[str] = None
    area: Optional[str] = None
    city: Optional[str] = None
    delivery_instructions: Optional[str] = None
    is_default: Optional[bool] = None


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
