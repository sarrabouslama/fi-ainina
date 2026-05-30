from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    review_type: str
    subject: str
    content: str
    alert_id: int | None = None
    assigned_admin_id: str | None = None


class ReviewReply(BaseModel):
    content: str | None = None


class ReviewMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    review_id: int
    sender_user_id: str
    sender_role: str
    message_type: str
    content: str
    timestamp: datetime


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_by_user_id: str
    assigned_admin_id: str | None
    alert_id: int | None
    review_type: str
    subject: str
    status: str
    created_at: datetime
    updated_at: datetime
    messages: list[ReviewMessageResponse] = Field(default_factory=list)