from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import LectureScheduleStatus
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


class SubjectAcademicScope(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "subject_academic_scopes"

    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    class_level: Mapped[int] = mapped_column(Integer, nullable=False)
    # common -> class 10, science/commerce -> class 11/12 streams.
    stream: Mapped[str] = mapped_column(String(20), nullable=False, default="common")

    __table_args__ = (
        UniqueConstraint("subject_id", "class_level", "stream", name="uq_subject_scope"),
        Index("ix_subject_scope_class_stream", "class_level", "stream"),
        Index("ix_subject_scope_subject", "subject_id"),
    )


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

    # Self-registration fields (phase extension).
    class_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    stream: Mapped[str | None] = mapped_column(String(20), nullable=True)
    parent_contact_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    school_details: Mapped[str | None] = mapped_column(String(255), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    user = relationship("User", lazy="joined")

    __table_args__ = (Index("ix_student_profiles_batch", "current_batch_id"),)


class TeacherProfile(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "teacher_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    employee_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    designation: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Self-registration fields (phase extension).
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    qualification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    school_college: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

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


class LectureSchedule(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "lecture_schedules"

    class_level: Mapped[int] = mapped_column(Integer, nullable=False)
    stream: Mapped[str] = mapped_column(String(20), nullable=False, default="common")
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("teacher_profiles.id", ondelete="RESTRICT"), nullable=False)
    batch_id: Mapped[str | None] = mapped_column(ForeignKey("batches.id", ondelete="SET NULL"), nullable=True)

    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    lecture_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[LectureScheduleStatus] = mapped_column(
        Enum(LectureScheduleStatus, name="lecture_schedule_status", native_enum=False),
        nullable=False,
        default=LectureScheduleStatus.SCHEDULED,
    )
    all_students_in_scope: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_lecture_schedules_status_scheduled", "status", "scheduled_at"),
        Index("ix_lecture_schedules_scope_scheduled", "class_level", "stream", "scheduled_at"),
        Index("ix_lecture_schedules_teacher_scheduled", "teacher_id", "scheduled_at"),
        Index("ix_lecture_schedules_subject_scheduled", "subject_id", "scheduled_at"),
    )


class LectureScheduleStudent(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "lecture_schedule_students"

    lecture_schedule_id: Mapped[str] = mapped_column(
        ForeignKey("lecture_schedules.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[str] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("lecture_schedule_id", "student_id", name="uq_lecture_schedule_student"),
        Index("ix_lecture_schedule_students_schedule", "lecture_schedule_id"),
        Index("ix_lecture_schedule_students_student", "student_id"),
    )


class CompletedLecture(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "completed_lectures"

    teacher_id: Mapped[str] = mapped_column(ForeignKey("teacher_profiles.id", ondelete="RESTRICT"), nullable=False)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    batch_id: Mapped[str | None] = mapped_column(ForeignKey("batches.id", ondelete="SET NULL"), nullable=True)
    schedule_id: Mapped[str | None] = mapped_column(
        ForeignKey("lecture_schedules.id", ondelete="SET NULL"),
        nullable=True,
    )

    class_level: Mapped[int] = mapped_column(Integer, nullable=False)
    stream: Mapped[str] = mapped_column(String(20), nullable=False, default="common")
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_completed_lectures_teacher_completed", "teacher_id", "completed_at"),
        Index("ix_completed_lectures_batch_completed", "batch_id", "completed_at"),
        Index("ix_completed_lectures_scope_completed", "class_level", "stream", "completed_at"),
        Index("ix_completed_lectures_subject_completed", "subject_id", "completed_at"),
        Index("ix_completed_lectures_schedule", "schedule_id"),
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
