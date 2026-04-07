from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import AttendanceStatus
from app.db.models.mixins import TimestampMixin, UUIDPKMixin


class AttendanceRecord(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "attendance_records"

    student_id: Mapped[str] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    session_code: Mapped[str] = mapped_column(String(50), default="day", nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="attendance_status", native_enum=False), nullable=False
    )
    source: Mapped[str] = mapped_column(String(30), default="manual", nullable=False)
    marked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "attendance_date", "session_code", name="uq_attendance_student_day_session"),
        Index("ix_attendance_batch_date", "batch_id", "attendance_date"),
        Index("ix_attendance_student_date", "student_id", "attendance_date"),
    )


class AttendanceCorrection(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "attendance_corrections"

    attendance_record_id: Mapped[str] = mapped_column(
        ForeignKey("attendance_records.id", ondelete="CASCADE"), nullable=False
    )
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)

    __table_args__ = (Index("ix_attendance_corrections_status_created", "status", "created_at"),)
