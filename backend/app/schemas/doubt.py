from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class CreateDoubtDTO(BaseModel):
    subject_id: str | None = None
    lecture_id: str | None = None
    teacher_id: str | None = None
    topic: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=5)

    @model_validator(mode="after")
    def validate_scope(self):
        if not self.subject_id and not self.lecture_id:
            raise ValueError("either subject_id or lecture_id is required")
        return self


class CreateLectureDoubtDTO(BaseModel):
    topic: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=5)


class AddDoubtMessageDTO(BaseModel):
    message: str = Field(min_length=1)


class TeacherCompleteLectureDTO(BaseModel):
    subject_id: str
    topic: str = Field(min_length=2, max_length=255)
    summary: str | None = Field(default=None, max_length=5000)
    class_level: int = Field(ge=10, le=12)
    stream: str | None = Field(default=None, pattern="^(science|commerce)$")
    batch_id: str | None = None
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_stream(self):
        if self.class_level == 10 and self.stream is not None:
            raise ValueError("stream is not allowed for class 10")
        if self.class_level in {11, 12} and self.stream is None:
            raise ValueError("stream is required for class 11 and 12")
        return self


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
