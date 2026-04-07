from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import DoubtStatus
from app.db.models.mixins import TimestampMixin, UUIDPKMixin


class Doubt(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "doubts"

    student_id: Mapped[str] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DoubtStatus] = mapped_column(
        Enum(DoubtStatus, name="doubt_status", native_enum=False),
        default=DoubtStatus.OPEN,
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)

    __table_args__ = (
        Index("ix_doubt_student_created", "student_id", "created_at"),
        Index("ix_doubt_status_updated", "status", "updated_at"),
        Index("ix_doubt_subject_status", "subject_id", "status"),
    )


class DoubtMessage(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "doubt_messages"

    doubt_id: Mapped[str] = mapped_column(ForeignKey("doubts.id", ondelete="CASCADE"), nullable=False)
    sender_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (Index("ix_doubt_message_doubt_created", "doubt_id", "created_at"),)
