from datetime import datetime

from pydantic import BaseModel


class AssessmentItemDTO(BaseModel):
    id: str
    title: str
    subject_id: str
    assessment_type: str
    starts_at: datetime | None
    ends_at: datetime | None
    duration_sec: int


class StartAttemptRequestDTO(BaseModel):
    idempotency_key: str


class SubmitAttemptDTO(BaseModel):
    idempotency_key: str


class AttemptResponseDTO(BaseModel):
    attempt_id: str
    status: str
    started_at: datetime
    expires_at: datetime
