from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class AdminLectureScheduleCreateDTO(BaseModel):
    class_level: int = Field(ge=10, le=12)
    stream: str | None = Field(default=None, pattern="^(science|commerce)$")
    subject_id: str
    teacher_id: str
    topic: str = Field(min_length=2, max_length=255)
    lecture_notes: str | None = Field(default=None, max_length=5000)
    scheduled_at: datetime
    student_ids: list[str] | None = None
    all_students_in_scope: bool = True

    @model_validator(mode="after")
    def validate_scope(self):
        if self.class_level == 10 and self.stream is not None:
            raise ValueError("stream is not allowed for class 10")
        if self.class_level in {11, 12} and self.stream is None:
            raise ValueError("stream is required for class 11 and 12")

        if not self.all_students_in_scope:
            ids = self.student_ids or []
            if len(ids) == 0:
                raise ValueError("student_ids is required when all_students_in_scope is false")

        return self


class AdminLectureScheduleStatusUpdateDTO(BaseModel):
    status: str = Field(pattern="^(scheduled|done|canceled)$")


class AdminLectureScheduleStudentAssignDTO(BaseModel):
    student_ids: list[str] = Field(min_length=1)
