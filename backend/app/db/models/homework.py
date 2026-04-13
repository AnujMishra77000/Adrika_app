from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import HomeworkStatus, HomeworkSubmissionStatus
from app.db.models.mixins import TimestampMixin, UUIDPKMixin


class Homework(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "homework"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[HomeworkStatus] = mapped_column(
        Enum(HomeworkStatus, name="homework_status", native_enum=False),
        default=HomeworkStatus.DRAFT,
        nullable=False,
    )
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        Index("ix_homework_due_date", "due_date"),
        Index("ix_homework_due_at", "due_at"),
        Index("ix_homework_status_expires", "status", "expires_at"),
        Index("ix_homework_subject_due", "subject_id", "due_date"),
    )


class HomeworkTarget(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "homework_targets"

    homework_id: Mapped[str] = mapped_column(ForeignKey("homework.id", ondelete="CASCADE"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("homework_id", "target_type", "target_id", name="uq_homework_target"),
        Index("ix_homework_targets_scope", "target_type", "target_id"),
    )


class HomeworkAttachment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "homework_attachments"

    homework_id: Mapped[str] = mapped_column(ForeignKey("homework.id", ondelete="CASCADE"), nullable=False)
    attachment_type: Mapped[str] = mapped_column(String(16), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("ix_homework_attachments_homework", "homework_id"),
        Index("ix_homework_attachments_homework_created", "homework_id", "created_at"),
    )


class HomeworkRead(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "homework_reads"

    homework_id: Mapped[str] = mapped_column(ForeignKey("homework.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("homework_id", "user_id", name="uq_homework_read"),
        Index("ix_homework_reads_user_read", "user_id", "read_at"),
    )


class HomeworkSubmission(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "homework_submissions"

    homework_id: Mapped[str] = mapped_column(ForeignKey("homework.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[str] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    submitted_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[HomeworkSubmissionStatus] = mapped_column(
        Enum(HomeworkSubmissionStatus, name="homework_submission_status", native_enum=False),
        default=HomeworkSubmissionStatus.SUBMITTED,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("homework_id", "student_id", name="uq_homework_submission_student"),
        Index("ix_homework_submissions_student_status", "student_id", "status", "submitted_at"),
        Index("ix_homework_submissions_homework_status", "homework_id", "status"),
    )


class HomeworkSubmissionAttachment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "homework_submission_attachments"

    submission_id: Mapped[str] = mapped_column(
        ForeignKey("homework_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        Index("ix_homework_submission_attachments_submission", "submission_id"),
        Index("ix_homework_submission_attachments_submission_created", "submission_id", "created_at"),
    )
