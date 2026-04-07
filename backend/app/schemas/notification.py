from datetime import datetime

from pydantic import BaseModel


class NotificationItemDTO(BaseModel):
    id: str
    notification_type: str
    title: str
    body: str
    is_read: bool
    created_at: datetime
