from typing import Optional

from pydantic import BaseModel

from app.models.delivery import DeliveryStatus, IssueType


class RiderStatusUpdate(BaseModel):
    online: bool


class DeliveryStatusUpdateRequest(BaseModel):
    status: DeliveryStatus


class DeliveryIssueRequest(BaseModel):
    type: IssueType
    description: Optional[str] = None


class RestaurantApprovalRequest(BaseModel):
    approval_status: str  # approved | rejected | suspended


class RiderApprovalRequest(BaseModel):
    approved: bool
