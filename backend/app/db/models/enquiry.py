from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDPKMixin


class StudentEnquiry(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "student_enquiries"

    student_name: Mapped[str] = mapped_column(String(255), nullable=False)
    class_level: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_class: Mapped[str | None] = mapped_column(String(50), nullable=True)
    previous_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    school_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="english")
    contact_number: Mapped[str] = mapped_column(String(20), nullable=False)
    parent_contact_number: Mapped[str] = mapped_column(String(20), nullable=False)
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    batch_id: Mapped[str | None] = mapped_column(
        ForeignKey("batches.id", ondelete="SET NULL"),
        nullable=True,
    )

    fee_class_level: Mapped[int] = mapped_column(Integer, nullable=False)
    fee_stream: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fee_structure_id: Mapped[str | None] = mapped_column(
        ForeignKey("fee_structures.id", ondelete="SET NULL"),
        nullable=True,
    )
    manual_fee_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    manual_fee_installment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fee_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    negotiable_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    installment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    initial_fee_paid_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    initial_fee_paid_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    initial_fee_payment_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    initial_fee_reference_no: Mapped[str | None] = mapped_column(String(120), nullable=True)
    initial_fee_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="follow_up")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    converted_student_id: Mapped[str | None] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint("class_level IN (6, 7, 8, 9, 10, 11, 12)", name="ck_student_enquiry_class_level"),
        CheckConstraint("fee_class_level IN (6, 7, 8, 9, 10, 11, 12)", name="ck_student_enquiry_fee_class_level"),
        CheckConstraint("fee_stream IS NULL OR fee_stream IN ('science', 'commerce')", name="ck_student_enquiry_fee_stream"),
        CheckConstraint("language IN ('hindi', 'english')", name="ck_student_enquiry_language"),
        CheckConstraint(
            "status IN ('interested', 'follow_up', 'confirmed', 'not_interested')",
            name="ck_student_enquiry_status",
        ),
        Index("ix_student_enquiry_status_followup", "status", "follow_up_at"),
        Index("ix_student_enquiry_class_stream", "class_level", "fee_stream"),
        Index("ix_student_enquiry_contact", "contact_number", "parent_contact_number"),
        Index("ix_student_enquiry_batch", "batch_id"),
        Index("ix_student_enquiry_converted_student", "converted_student_id"),
    )


class StudentEnquiryStatusHistory(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "student_enquiry_status_history"

    enquiry_id: Mapped[str] = mapped_column(
        ForeignKey("student_enquiries.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("from_status IS NULL OR from_status IN ('interested', 'follow_up', 'confirmed', 'not_interested')", name="ck_enquiry_history_from_status"),
        CheckConstraint("to_status IN ('interested', 'follow_up', 'confirmed', 'not_interested')", name="ck_enquiry_history_to_status"),
        Index("ix_enquiry_history_enquiry_changed", "enquiry_id", "changed_at"),
    )
