from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import NoticeStatus
from app.db.models.mixins import TimestampMixin, UUIDPKMixin


class Notice(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "notices"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[NoticeStatus] = mapped_column(
        Enum(NoticeStatus, name="notice_status", native_enum=False), default=NoticeStatus.DRAFT, nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (Index("ix_notices_status_publish", "status", "publish_at"),)


class NoticeTarget(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "notice_targets"

    notice_id: Mapped[str] = mapped_column(ForeignKey("notices.id", ondelete="CASCADE"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("notice_id", "target_type", "target_id", name="uq_notice_target"),
        Index("ix_notice_targets_scope", "target_type", "target_id"),
    )


class NoticeAttachment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "notice_attachments"

    notice_id: Mapped[str] = mapped_column(ForeignKey("notices.id", ondelete="CASCADE"), nullable=False)
    attachment_type: Mapped[str] = mapped_column(String(16), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    image_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_notice_attachments_notice", "notice_id"),
        Index("ix_notice_attachments_notice_created", "notice_id", "created_at"),
    )


class NoticeRead(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "notice_reads"

    notice_id: Mapped[str] = mapped_column(ForeignKey("notices.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("notice_id", "user_id", name="uq_notice_read"),
        Index("ix_notice_reads_user_read", "user_id", "read_at"),
    )


class Banner(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "banners"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    media_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    action_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    active_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    active_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_popup: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (Index("ix_banners_active_window", "active_from", "active_to"),)


class DailyThought(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "daily_thoughts"

    thought_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
