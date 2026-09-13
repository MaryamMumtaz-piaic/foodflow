from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.models.cart import CartItem


class OrderStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    preparing = "preparing"
    ready_for_pickup = "ready_for_pickup"
    rider_assigned = "rider_assigned"
    picked_up = "picked_up"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"
    failed = "failed"
    rejected = "rejected"


class PaymentMethod(str, Enum):
    cash_on_delivery = "cash_on_delivery"
    card = "card"
    wallet = "wallet"


class PaymentStatus(str, Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


class Order(BaseModel):
    id: str
    customer_id: str
    restaurant_id: str
    rider_id: Optional[str] = None
    items: list[CartItem] = Field(default_factory=list)
    delivery_address: dict
    contact_phone: Optional[str] = None
    delivery_instructions: Optional[str] = None
    subtotal: float
    delivery_fee: float
    discount: float = 0.0
    tax: float = 0.0
    final_total: float
    coupon_code: Optional[str] = None
    payment_method: PaymentMethod = PaymentMethod.cash_on_delivery
    payment_status: PaymentStatus = PaymentStatus.pending
    status: OrderStatus = OrderStatus.pending
    rejection_reason: Optional[str] = None
    cancellation_reason: Optional[str] = None
    estimated_delivery_time_minutes: int = 40
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
