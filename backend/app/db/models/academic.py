from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDPKMixin


class Branch(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "branches"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class Standard(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "standards"

    branch_id: Mapped[str] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (UniqueConstraint("branch_id", "name", name="uq_standard_branch_name"),)


class Batch(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "batches"

    standard_id: Mapped[str] = mapped_column(ForeignKey("standards.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    academic_year: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("standard_id", "name", "academic_year", name="uq_batch_standard_name_year"),
        Index("ix_batches_standard", "standard_id"),
        Index("ix_batches_year", "academic_year"),
    )


class Subject(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "subjects"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class BatchSubject(Base, TimestampMixin):
    __tablename__ = "batch_subjects"

    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"), primary_key=True)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True)

    __table_args__ = (UniqueConstraint("batch_id", "subject_id", name="uq_batch_subject"),)


class StudentProfile(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "student_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    admission_no: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    roll_no: Mapped[str] = mapped_column(String(50), nullable=False)
    current_batch_id: Mapped[str | None] = mapped_column(
        ForeignKey("batches.id", ondelete="SET NULL"), nullable=True
    )

    user = relationship("User", lazy="joined")

    __table_args__ = (Index("ix_student_profiles_batch", "current_batch_id"),)


class TeacherProfile(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "teacher_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    employee_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    designation: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user = relationship("User", lazy="joined")


class TeacherBatchAssignment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "teacher_batch_assignments"

    teacher_id: Mapped[str] = mapped_column(ForeignKey("teacher_profiles.id", ondelete="CASCADE"), nullable=False)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)

    __table_args__ = (
        UniqueConstraint("teacher_id", "batch_id", "subject_id", name="uq_teacher_batch_subject"),
        Index("ix_teacher_assignment_teacher", "teacher_id"),
        Index("ix_teacher_assignment_batch", "batch_id"),
        Index("ix_teacher_assignment_subject", "subject_id"),
    )


class StudentBatchEnrollment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "student_batch_enrollments"

    student_id: Mapped[str] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        Index("ix_enrollment_student_to_date", "student_id", "to_date"),
        Index("ix_enrollment_batch_to_date", "batch_id", "to_date"),
    )
