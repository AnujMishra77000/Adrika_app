from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import AssessmentStatus, AssessmentType, AttemptStatus
from app.db.models.mixins import TimestampMixin, UUIDPKMixin


class Assessment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "assessments"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    class_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stream: Mapped[str | None] = mapped_column(String(20), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(150), nullable=True)
    assessment_type: Mapped[AssessmentType] = mapped_column(
        Enum(AssessmentType, name="assessment_type", native_enum=False), nullable=False
    )
    status: Mapped[AssessmentStatus] = mapped_column(
        Enum(AssessmentStatus, name="assessment_status", native_enum=False),
        default=AssessmentStatus.DRAFT,
        nullable=False,
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_limit: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_marks: Mapped[float] = mapped_column(Numeric(8, 2), default=0, nullable=False)
    passing_marks: Mapped[float] = mapped_column(Numeric(8, 2), default=0, nullable=False)
    negative_marking_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("ix_assessment_type_starts", "assessment_type", "starts_at"),
        Index("ix_assessment_subject_starts", "subject_id", "starts_at"),
        Index("ix_assessment_status", "status"),
        Index("ix_assessment_academic_scope", "class_level", "stream", "subject_id"),
        Index("ix_assessment_status_window", "status", "starts_at", "ends_at"),
    )


class AssessmentAssignment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "assessment_assignments"

    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("assessment_id", "target_type", "target_id", name="uq_assessment_assignment"),
        Index("ix_assessment_assignment_scope", "target_type", "target_id"),
    )


class QuestionBank(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "question_bank"

    class_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stream: Mapped[str | None] = mapped_column(String(20), nullable=True)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    topic: Mapped[str | None] = mapped_column(String(150), nullable=True)
    question_type: Mapped[str] = mapped_column(String(30), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    answer_key: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    default_marks: Mapped[float] = mapped_column(Numeric(8, 2), default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("ix_question_subject_active", "subject_id", "is_active"),
        Index("ix_question_bank_scope", "class_level", "stream", "subject_id", "is_active"),
        Index("ix_question_bank_topic", "topic"),
    )


class AssessmentQuestion(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "assessment_questions"

    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[str] = mapped_column(ForeignKey("question_bank.id", ondelete="RESTRICT"), nullable=False)
    seq_no: Mapped[int] = mapped_column(Integer, nullable=False)
    marks: Mapped[float] = mapped_column(Numeric(8, 2), default=1, nullable=False)
    negative_marks: Mapped[float] = mapped_column(Numeric(8, 2), default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("assessment_id", "seq_no", name="uq_assessment_question_seq"),
        Index("ix_assessment_question_assessment", "assessment_id"),
    )


class AssessmentAttempt(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "assessment_attempts"

    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[str] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[AttemptStatus] = mapped_column(
        Enum(AttemptStatus, name="attempt_status", native_enum=False),
        default=AttemptStatus.STARTED,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    __table_args__ = (
        UniqueConstraint("assessment_id", "student_id", "attempt_no", name="uq_assessment_student_attempt"),
        Index("ix_attempt_student_started", "student_id", "started_at"),
        Index("ix_attempt_status_expires", "status", "expires_at"),
    )


class AttemptAnswer(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "attempt_answers"

    attempt_id: Mapped[str] = mapped_column(ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[str] = mapped_column(ForeignKey("question_bank.id", ondelete="RESTRICT"), nullable=False)
    answer_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    marks_obtained: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question"),
        Index("ix_attempt_answers_attempt", "attempt_id"),
    )
