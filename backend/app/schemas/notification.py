from pydantic import BaseModel
from typing import Optional


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    document_id: str
    type: str
    payload: dict
    delivered: bool
    created_at: str
    read_at: Optional[str]

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]


class MarkNotificationReadRequest(BaseModel):
    pass


class MarkNotificationReadResponse(BaseModel):
    success: bool
    message: str


class MarkAllNotificationsReadResponse(BaseModel):
    success: bool
    message: str
    count: int
