from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DeliveryStatus(str, Enum):
    assigned = "assigned"
    accepted = "accepted"
    arrived_at_restaurant = "arrived_at_restaurant"
    picked_up = "picked_up"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    failed = "failed"


class IssueType(str, Enum):
    restaurant_delay = "restaurant_delay"
    customer_unavailable = "customer_unavailable"
    incorrect_address = "incorrect_address"
    vehicle_issue = "vehicle_issue"
    missing_item = "missing_item"
    safety_concern = "safety_concern"
    other = "other"


class DeliveryIssue(BaseModel):
    type: IssueType
    description: Optional[str] = None
    reported_at: datetime = Field(default_factory=datetime.utcnow)


class Delivery(BaseModel):
    id: str
    order_id: str
    rider_id: Optional[str] = None
    restaurant_id: str
    pickup_address: str
    drop_off_address: str
    status: DeliveryStatus = DeliveryStatus.assigned
    estimated_distance_km: float = 3.0
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    picked_up_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    issues: list[DeliveryIssue] = Field(default_factory=list)
