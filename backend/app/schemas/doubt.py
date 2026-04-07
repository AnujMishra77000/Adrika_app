from datetime import datetime

from pydantic import BaseModel, Field


class CreateDoubtDTO(BaseModel):
    subject_id: str
    topic: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=5)


class AddDoubtMessageDTO(BaseModel):
    message: str = Field(min_length=1)


class DoubtItemDTO(BaseModel):
    id: str
    subject_id: str
    topic: str
    status: str
    priority: str
    created_at: datetime


class DoubtMessageDTO(BaseModel):
    id: str
    sender_user_id: str | None
    message: str
    created_at: datetime
