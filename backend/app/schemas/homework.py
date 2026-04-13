from datetime import date, datetime

from pydantic import BaseModel, Field


class HomeworkAttachmentDTO(BaseModel):
    id: str
    attachment_type: str
    file_name: str
    file_url: str
    content_type: str
    file_size_bytes: int
    is_generated: bool


class HomeworkSubmissionAttachmentDTO(BaseModel):
    id: str
    file_name: str
    file_url: str
    content_type: str
    file_size_bytes: int


class HomeworkSubmissionDTO(BaseModel):
    id: str
    status: str
    submitted_at: datetime
    notes: str | None = None
    attachments: list[HomeworkSubmissionAttachmentDTO] = Field(default_factory=list)


class HomeworkItemDTO(BaseModel):
    id: str
    title: str
    description: str
    subject_id: str
    due_date: date
    due_at: datetime | None = None
    expires_at: datetime | None = None
    status: str
    is_read: bool = False
    attachment_count: int = 0
    attachments: list[HomeworkAttachmentDTO] = Field(default_factory=list)
    is_submitted: bool = False
    submission: HomeworkSubmissionDTO | None = None
