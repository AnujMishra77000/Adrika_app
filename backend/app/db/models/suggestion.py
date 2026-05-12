from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDPKMixin


class SuggestionThread(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "suggestion_threads"

    student_id: Mapped[str] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")

    last_message_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sender_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    admin_last_read_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    student_last_read_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("student_id", name="uq_suggestion_thread_student"),
        Index("ix_suggestion_threads_last_message", "last_message_at"),
        Index("ix_suggestion_threads_student", "student_id"),
        Index("ix_suggestion_threads_admin_read", "admin_last_read_at", "last_message_at"),
    )


class SuggestionMessage(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "suggestion_messages"

    thread_id: Mapped[str] = mapped_column(
        ForeignKey("suggestion_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("ix_suggestion_messages_thread_created", "thread_id", "created_at"),
    )
