from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import HomeworkStatus
from app.db.models.mixins import TimestampMixin, UUIDPKMixin


class Homework(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "homework"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[HomeworkStatus] = mapped_column(
        Enum(HomeworkStatus, name="homework_status", native_enum=False),
        default=HomeworkStatus.DRAFT,
        nullable=False,
    )
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        Index("ix_homework_due_date", "due_date"),
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
