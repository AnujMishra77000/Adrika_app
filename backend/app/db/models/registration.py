from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import RegistrationRequestStatus, RoleCode
from app.db.models.mixins import TimestampMixin, UUIDPKMixin


class RegistrationRequest(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "registration_requests"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    requested_role: Mapped[RoleCode] = mapped_column(
        Enum(RoleCode, name="registration_requested_role", native_enum=False),
        nullable=False,
    )
    status: Mapped[RegistrationRequestStatus] = mapped_column(
        Enum(RegistrationRequestStatus, name="registration_request_status", native_enum=False),
        default=RegistrationRequestStatus.PENDING,
        nullable=False,
    )
    reviewed_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship("User", foreign_keys=[user_id], lazy="joined")

    __table_args__ = (
        Index("ix_registration_requests_status_role_created", "status", "requested_role", "created_at"),
    )
