from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDPKMixin


class ParentProfile(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "parent_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    user = relationship("User", lazy="joined")


class ParentStudentLink(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "parent_student_links"

    parent_id: Mapped[str] = mapped_column(ForeignKey("parent_profiles.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[str] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(30), default="guardian", nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("parent_id", "student_id", name="uq_parent_student_link"),
        Index("ix_parent_link_parent_active", "parent_id", "is_active"),
        Index("ix_parent_link_student_active", "student_id", "is_active"),
    )


class ParentCommunicationPreference(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "parent_communication_preferences"

    parent_id: Mapped[str] = mapped_column(ForeignKey("parent_profiles.id", ondelete="CASCADE"), nullable=False, unique=True)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fee_reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
