from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.assessment import Assessment, AssessmentAssignment, AssessmentAttempt, AttemptAnswer
from app.db.models.enums import AssessmentStatus, AttemptStatus


class AssessmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_student(
        self,
        *,
        student_id: str,
        batch_id: str | None,
        assessment_type: str | None,
        status: str | None,
        subject_id: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Assessment], int]:
        target_filters = [
            and_(AssessmentAssignment.target_type == "all", AssessmentAssignment.target_id == "all"),
            and_(AssessmentAssignment.target_type == "student", AssessmentAssignment.target_id == student_id),
        ]
        if batch_id:
            target_filters.append(
                and_(AssessmentAssignment.target_type == "batch", AssessmentAssignment.target_id == batch_id)
            )

        filters = [or_(*target_filters)]
        if assessment_type:
            filters.append(Assessment.assessment_type == assessment_type)
        if status:
            filters.append(Assessment.status == status)
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
                base.order_by(Assessment.starts_at.desc().nulls_last()).limit(limit).offset(offset)
            )
        ).scalars().all()
        return rows, total

    async def get_assessment_for_student(self, *, assessment_id: str, student_id: str, batch_id: str | None) -> Assessment | None:
        target_filters = [
            and_(AssessmentAssignment.target_type == "all", AssessmentAssignment.target_id == "all"),
            and_(AssessmentAssignment.target_type == "student", AssessmentAssignment.target_id == student_id),
        ]
        if batch_id:
            target_filters.append(
                and_(AssessmentAssignment.target_type == "batch", AssessmentAssignment.target_id == batch_id)
            )

        stmt = (
            select(Assessment)
            .join(AssessmentAssignment, AssessmentAssignment.assessment_id == Assessment.id)
            .where(Assessment.id == assessment_id, or_(*target_filters))
            .distinct()
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def current_attempt_count(self, *, assessment_id: str, student_id: str) -> int:
        stmt = select(func.count()).where(
            AssessmentAttempt.assessment_id == assessment_id,
            AssessmentAttempt.student_id == student_id,
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def create_attempt(self, *, assessment: Assessment, student_id: str, attempt_no: int) -> AssessmentAttempt:
        now = datetime.now(UTC)
        attempt = AssessmentAttempt(
            assessment_id=assessment.id,
            student_id=student_id,
            attempt_no=attempt_no,
            started_at=now,
            expires_at=now + timedelta(seconds=assessment.duration_sec),
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

    async def upsert_answer(self, *, attempt_id: str, question_id: str, answer_payload: dict) -> None:
        stmt = select(AttemptAnswer).where(
            AttemptAnswer.attempt_id == attempt_id,
            AttemptAnswer.question_id == question_id,
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.answer_payload = answer_payload
            return
        self.session.add(AttemptAnswer(attempt_id=attempt_id, question_id=question_id, answer_payload=answer_payload))

    async def submit_attempt(self, attempt: AssessmentAttempt) -> AssessmentAttempt:
        attempt.status = AttemptStatus.SUBMITTED
        attempt.submitted_at = datetime.now(UTC)
        if attempt.score is None:
            attempt.score = 0
        await self.session.flush()
        return attempt

    async def upcoming_count_for_student(self, *, student_id: str, batch_id: str | None) -> int:
        now = datetime.now(UTC)
        target_filters = [
            and_(AssessmentAssignment.target_type == "all", AssessmentAssignment.target_id == "all"),
            and_(AssessmentAssignment.target_type == "student", AssessmentAssignment.target_id == student_id),
        ]
        if batch_id:
            target_filters.append(
                and_(AssessmentAssignment.target_type == "batch", AssessmentAssignment.target_id == batch_id)
            )

        stmt = (
            select(func.count())
            .select_from(Assessment)
            .join(AssessmentAssignment, AssessmentAssignment.assessment_id == Assessment.id)
            .where(
                Assessment.status == AssessmentStatus.PUBLISHED,
                Assessment.starts_at.is_not(None),
                Assessment.starts_at >= now,
                or_(*target_filters),
            )
        )
        return (await self.session.execute(stmt)).scalar_one()
