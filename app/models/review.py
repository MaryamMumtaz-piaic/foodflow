from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ModerationStatus(str, Enum):
    visible = "visible"
    hidden = "hidden"
    flagged = "flagged"


class Review(BaseModel):
    id: str
    customer_id: str
    customer_name: Optional[str] = None
    restaurant_id: str
    order_id: Optional[str] = None
    rating: int = Field(ge=1, le=5)
    comment: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    moderation_status: ModerationStatus = ModerationStatus.visible
