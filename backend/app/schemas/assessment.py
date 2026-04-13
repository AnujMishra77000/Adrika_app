from datetime import datetime

from pydantic import BaseModel, Field


class AssessmentItemDTO(BaseModel):
    id: str
    title: str
    subject_id: str
    assessment_type: str
    starts_at: datetime | None
    ends_at: datetime | None
    duration_sec: int


class AssessmentAnswerDTO(BaseModel):
    selected_key: str = Field(min_length=1, max_length=4)


class StartAttemptRequestDTO(BaseModel):
    idempotency_key: str | None = None


class SubmitAttemptDTO(BaseModel):
    idempotency_key: str | None = None


class AttemptResponseDTO(BaseModel):
    attempt_id: str
    status: str
    started_at: datetime
    expires_at: datetime
