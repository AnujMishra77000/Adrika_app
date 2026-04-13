from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDPKMixin


class FeeStructure(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "fee_structures"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    class_level: Mapped[int] = mapped_column(Integer, nullable=False)
    stream: Mapped[str | None] = mapped_column(String(20), nullable=True)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    installment_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        CheckConstraint("class_level IN (10, 11, 12)", name="ck_fee_structure_class_level"),
        CheckConstraint("stream IS NULL OR stream IN ('science', 'commerce')", name="ck_fee_structure_stream"),
        Index("ix_fee_structure_class_stream_active", "class_level", "stream", "is_active"),
    )


class StudentFeeStructureAssignment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "student_fee_structure_assignments"

    student_id: Mapped[str] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    fee_structure_id: Mapped[str] = mapped_column(
        ForeignKey("fee_structures.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("ix_student_fee_assignment_structure_active", "fee_structure_id", "is_active"),
    )


class FeeInvoice(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "fee_invoices"

    student_id: Mapped[str] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)

    # Phase-4 fee-account mapping fields. Kept nullable for backward compatibility
    # with already issued invoices and older datasets.
    student_fee_account_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    installment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    installment_no: Mapped[int | None] = mapped_column(nullable=True)

    invoice_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    period_label: Mapped[str] = mapped_column(String(50), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    balance_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_link: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    next_installment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_fee_invoice_student_due", "student_id", "due_date"),
        Index("ix_fee_invoice_student_status", "student_id", "status"),
        Index("ix_fee_invoice_reminder_due", "reminder_enabled", "next_installment_date", "due_date"),
        Index("ix_fee_invoice_account_status", "student_fee_account_id", "status"),
    )


class PaymentTransaction(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "payment_transactions"

    invoice_id: Mapped[str] = mapped_column(ForeignKey("fee_invoices.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[str] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)

    # Optional link to student fee account for ledger traversal.
    student_fee_account_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(30), default="manual", nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("provider", "external_ref", name="uq_payment_provider_ref"),
        Index("ix_payment_student_created", "student_id", "created_at"),
        Index("ix_payment_invoice_status", "invoice_id", "status"),
        Index("ix_payment_account_status", "student_fee_account_id", "status"),
    )
