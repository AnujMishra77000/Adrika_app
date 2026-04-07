from datetime import date, datetime

from pydantic import BaseModel


class ResultItemDTO(BaseModel):
    id: str
    assessment_id: str
    score: float
    total_marks: float
    rank: int | None
    published_at: datetime


class ProgressSnapshotDTO(BaseModel):
    period_type: str
    period_start: date
    metrics: dict
