from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationItemDTO(BaseModel):
    id: str
    notification_type: str
    title: str
    body: str
    metadata: dict | None = None
    source: str | None = None
    notice_id: str | None = None
    is_read: bool
    created_at: datetime


class NotificationTargetDTO(BaseModel):
    target_type: str = Field(pattern="^(all|all_students|batch|student|teacher|grade)$")
    target_id: str


class NotificationSendDTO(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    body: str = Field(min_length=2)
    notification_type: str = Field(pattern="^(notice|homework|test|result|doubt|system)$")
    targets: list[NotificationTargetDTO] = Field(min_length=1, max_length=200)
    metadata: dict | None = None


class DeviceRegisterDTO(BaseModel):
    device_id: str = Field(min_length=3, max_length=255)
    platform: str = Field(min_length=2, max_length=20)
    push_token: str = Field(min_length=12, max_length=512)
    app_version: str | None = Field(default=None, max_length=40)


class DeviceRegisterResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    device_id: str
    platform: str
    push_token: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
