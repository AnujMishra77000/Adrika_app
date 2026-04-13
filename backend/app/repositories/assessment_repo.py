from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.academic import Batch, Standard, StudentProfile
from app.db.models.assessment import (
    Assessment,
    AssessmentAssignment,
    AssessmentAttempt,
    AssessmentQuestion,
    AttemptAnswer,
    QuestionBank,
)
from app.db.models.enums import AssessmentStatus, AttemptStatus, UserStatus
from app.db.models.results import Result
from app.db.models.user import User


class AssessmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _normalize_stream(stream: str | None) -> str:
        value = (stream or "").strip().lower()
        if value in {"science", "sci"}:
            return "science"
        if value in {"commerce", "comm"}:
            return "commerce"
        return "common"

    @staticmethod
    def _extract_grade(class_name: str | None, standard_name: str | None) -> int | None:
        source = f"{class_name or ''} {standard_name or ''}".lower()
        if "10" in source:
            return 10
        if "11" in source:
            return 11
        if "12" in source:
            return 12
        return None

    @staticmethod
    def _to_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _target_filters(
        self,
        *,
        student_id: str,
        batch_id: str | None,
        class_level: int | None,
        stream: str | None,
    ) -> list:
        filters = [
            and_(AssessmentAssignment.target_type == "all", AssessmentAssignment.target_id == "all"),
            and_(AssessmentAssignment.target_type == "all_students", AssessmentAssignment.target_id == "all"),
            and_(AssessmentAssignment.target_type == "student", AssessmentAssignment.target_id == student_id),
        ]

        if batch_id:
            filters.append(and_(AssessmentAssignment.target_type == "batch", AssessmentAssignment.target_id == batch_id))

        if class_level is not None:
            filters.append(
                and_(AssessmentAssignment.target_type == "grade", AssessmentAssignment.target_id == str(class_level))
            )
            normalized = self._normalize_stream(stream)
            filters.append(
                and_(
                    AssessmentAssignment.target_type == "grade",
                    AssessmentAssignment.target_id == f"{class_level}:{normalized}",
                )
            )

        return filters

    async def list_for_student(
        self,
        *,
        student_id: str,
        batch_id: str | None,
        class_level: int | None,
        stream: str | None,
        assessment_type: str | None,
        status: str | None,
        subject_id: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Assessment], int]:
        target_filters = self._target_filters(
            student_id=student_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=stream,
        )

        filters = [or_(*target_filters)]
        if status:
            filters.append(Assessment.status == status)
        else:
            filters.append(Assessment.status.in_([AssessmentStatus.PUBLISHED, AssessmentStatus.COMPLETED]))

        if assessment_type:
            filters.append(Assessment.assessment_type == assessment_type)
        if subject_id:
            filters.append(Assessment.subject_id == subject_id)

        base = (
            select(Assessment)
            .join(AssessmentAssignment, AssessmentAssignment.assessment_id == Assessment.id)
            .where(*filters)
            .distinct()
        )

        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                base.order_by(Assessment.starts_at.asc(), Assessment.created_at.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()
        return rows, total

    async def get_assessment_for_student(
        self,
        *,
        assessment_id: str,
        student_id: str,
        batch_id: str | None,
        class_level: int | None,
        stream: str | None,
    ) -> Assessment | None:
        target_filters = self._target_filters(
            student_id=student_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=stream,
        )

        stmt = (
            select(Assessment)
            .join(AssessmentAssignment, AssessmentAssignment.assessment_id == Assessment.id)
            .where(
                Assessment.id == assessment_id,
                Assessment.status.in_([AssessmentStatus.PUBLISHED, AssessmentStatus.COMPLETED]),
                or_(*target_filters),
            )
            .distinct()
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def current_attempt_count(self, *, assessment_id: str, student_id: str) -> int:
        stmt = select(func.count()).where(
            AssessmentAttempt.assessment_id == assessment_id,
            AssessmentAttempt.student_id == student_id,
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def latest_attempt_for_student(self, *, assessment_id: str, student_id: str) -> AssessmentAttempt | None:
        stmt = (
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.assessment_id == assessment_id,
                AssessmentAttempt.student_id == student_id,
            )
            .order_by(AssessmentAttempt.attempt_no.desc(), AssessmentAttempt.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_attempt(self, *, assessment: Assessment, student_id: str, attempt_no: int) -> AssessmentAttempt:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=int(assessment.duration_sec))
        assessment_ends_at = self._to_utc(assessment.ends_at)
        if assessment_ends_at and expires_at > assessment_ends_at:
            expires_at = assessment_ends_at

        attempt = AssessmentAttempt(
            assessment_id=assessment.id,
            student_id=student_id,
            attempt_no=attempt_no,
            started_at=now,
            expires_at=expires_at,
            status=AttemptStatus.STARTED,
        )
        self.session.add(attempt)
        await self.session.flush()
        return attempt

    async def get_attempt(self, *, attempt_id: str, student_id: str) -> AssessmentAttempt | None:
        stmt = select(AssessmentAttempt).where(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.student_id == student_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_assessment_questions(self, *, assessment_id: str) -> list[tuple[AssessmentQuestion, QuestionBank]]:
        stmt = (
            select(AssessmentQuestion, QuestionBank)
            .join(QuestionBank, QuestionBank.id == AssessmentQuestion.question_id)
            .where(AssessmentQuestion.assessment_id == assessment_id)
            .order_by(AssessmentQuestion.seq_no.asc())
        )
        return (await self.session.execute(stmt)).all()

    async def question_exists_in_assessment(self, *, assessment_id: str, question_id: str) -> bool:
        stmt = select(func.count()).where(
            AssessmentQuestion.assessment_id == assessment_id,
            AssessmentQuestion.question_id == question_id,
        )
        return ((await self.session.execute(stmt)).scalar_one() or 0) > 0

    async def upsert_answer(self, *, attempt_id: str, question_id: str, answer_payload: dict) -> AttemptAnswer:
        stmt = select(AttemptAnswer).where(
            AttemptAnswer.attempt_id == attempt_id,
            AttemptAnswer.question_id == question_id,
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.answer_payload = answer_payload
            existing.is_correct = None
            existing.marks_obtained = None
            await self.session.flush()
            return existing

        row = AttemptAnswer(attempt_id=attempt_id, question_id=question_id, answer_payload=answer_payload)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_answer_rows_for_attempt(self, *, attempt_id: str) -> list[AttemptAnswer]:
        stmt = select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt_id)
        return (await self.session.execute(stmt)).scalars().all()

    async def upsert_result(
        self,
        *,
        assessment_id: str,
        student_id: str,
        score: float,
        total_marks: float,
        published_at: datetime,
    ) -> Result:
        stmt = select(Result).where(
            Result.assessment_id == assessment_id,
            Result.student_id == student_id,
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.score = score
            existing.total_marks = total_marks
            existing.published_at = published_at
            await self.session.flush()
            return existing

        row = Result(
            assessment_id=assessment_id,
            student_id=student_id,
            score=score,
            total_marks=total_marks,
            rank=None,
            published_at=published_at,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def result_for_student(self, *, assessment_id: str, student_id: str) -> Result | None:
        stmt = select(Result).where(
            Result.assessment_id == assessment_id,
            Result.student_id == student_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def upcoming_count_for_student(
        self,
        *,
        student_id: str,
        batch_id: str | None,
        class_level: int | None = None,
        stream: str | None = None,
    ) -> int:
        now = datetime.now(UTC)
        target_filters = self._target_filters(
            student_id=student_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=stream,
        )

        stmt = (
            select(func.count(func.distinct(Assessment.id)))
            .select_from(Assessment)
            .join(AssessmentAssignment, AssessmentAssignment.assessment_id == Assessment.id)
            .outerjoin(
                Result,
                and_(
                    Result.assessment_id == Assessment.id,
                    Result.student_id == student_id,
                ),
            )
            .where(
                Assessment.status == AssessmentStatus.PUBLISHED,
                or_(Assessment.ends_at.is_(None), Assessment.ends_at >= now),
                or_(*target_filters),
                Result.id.is_(None),
            )
        )
        return (await self.session.execute(stmt)).scalar_one() or 0

    async def list_expired_started_attempts(self, *, limit: int) -> list[AssessmentAttempt]:
        now = datetime.now(UTC)
        stmt = (
            select(AssessmentAttempt)
            .where(
                AssessmentAttempt.status == AttemptStatus.STARTED,
                AssessmentAttempt.expires_at <= now,
            )
            .order_by(AssessmentAttempt.expires_at.asc())
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def list_ended_assessments_for_absent(self, *, limit: int) -> list[Assessment]:
        now = datetime.now(UTC)
        stmt = (
            select(Assessment)
            .where(
                Assessment.status.in_([AssessmentStatus.PUBLISHED, AssessmentStatus.COMPLETED]),
                Assessment.ends_at.is_not(None),
                Assessment.ends_at <= now,
            )
            .order_by(Assessment.ends_at.asc())
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def list_assigned_students_for_assessment(self, *, assessment_id: str) -> set[str]:
        assignments = (
            await self.session.execute(
                select(AssessmentAssignment.target_type, AssessmentAssignment.target_id).where(
                    AssessmentAssignment.assessment_id == assessment_id
                )
            )
        ).all()

        if not assignments:
            return set()

        rows = (
            await self.session.execute(
                select(StudentProfile, User, Batch, Standard)
                .join(User, User.id == StudentProfile.user_id)
                .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
                .outerjoin(Standard, Standard.id == Batch.standard_id)
                .where(User.status == UserStatus.ACTIVE)
            )
        ).all()

        selected: set[str] = set()
        for target_type, target_id in assignments:
            if target_type in {"all", "all_students"} and target_id == "all":
                for profile, _user, _batch, _standard in rows:
                    selected.add(profile.id)
                continue

            if target_type == "student":
                for profile, _user, _batch, _standard in rows:
                    if profile.id == target_id:
                        selected.add(profile.id)
                continue

            if target_type == "batch":
                for profile, _user, _batch, _standard in rows:
                    if profile.current_batch_id == target_id:
                        selected.add(profile.id)
                continue

            if target_type == "grade":
                grade_raw, _, stream_raw = target_id.partition(":")
                try:
                    grade = int(grade_raw)
                except ValueError:
                    continue
                stream_filter = self._normalize_stream(stream_raw) if stream_raw else None

                for profile, _user, _batch, standard in rows:
                    student_grade = self._extract_grade(
                        profile.class_name,
                        standard.name if standard else None,
                    )
                    if student_grade != grade:
                        continue

                    if stream_filter and grade in {11, 12}:
                        student_stream = self._normalize_stream(profile.stream)
                        if student_stream != stream_filter:
                            continue

                    selected.add(profile.id)

        return selected

    async def mark_assessment_completed(self, *, assessment_id: str) -> None:
        assessment = await self.session.get(Assessment, assessment_id)
        if assessment and assessment.status != AssessmentStatus.COMPLETED:
            assessment.status = AssessmentStatus.COMPLETED
            await self.session.flush()
