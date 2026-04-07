from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDPKMixin


class Result(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "results"

    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[str] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    total_marks: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("assessment_id", "student_id", name="uq_result_assessment_student"),
        Index("ix_result_student_published", "student_id", "published_at"),
    )


class StudentProgressSnapshot(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "student_progress_snapshots"

    student_id: Mapped[str] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "period_type", "period_start", name="uq_progress_student_period"),
        Index("ix_progress_student_period_start", "student_id", "period_start"),
    )
