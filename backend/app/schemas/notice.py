from datetime import datetime

from pydantic import BaseModel


class NoticeItemDTO(BaseModel):
    id: str
    title: str
    body_preview: str
    priority: int
    publish_at: datetime | None
    is_read: bool


class NoticeDetailDTO(BaseModel):
    id: str
    title: str
    body: str
    priority: int
    publish_at: datetime | None
    is_read: bool
