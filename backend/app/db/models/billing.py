from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDPKMixin


class FeeInvoice(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "fee_invoices"

    student_id: Mapped[str] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    invoice_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    period_label: Mapped[str] = mapped_column(String(50), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_fee_invoice_student_due", "student_id", "due_date"),
        Index("ix_fee_invoice_student_status", "student_id", "status"),
    )


class PaymentTransaction(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "payment_transactions"

    invoice_id: Mapped[str] = mapped_column(ForeignKey("fee_invoices.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[str] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("provider", "external_ref", name="uq_payment_provider_ref"),
        Index("ix_payment_student_created", "student_id", "created_at"),
        Index("ix_payment_invoice_status", "invoice_id", "status"),
    )
