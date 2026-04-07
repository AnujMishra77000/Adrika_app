from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.repositories.assessment_repo import AssessmentRepository


class AssessmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AssessmentRepository(session)

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
    ) -> tuple[list[dict], int]:
        rows, total = await self.repo.list_for_student(
            student_id=student_id,
            batch_id=batch_id,
            assessment_type=assessment_type,
            status=status,
            subject_id=subject_id,
            limit=limit,
            offset=offset,
        )

        return [
            {
                "id": row.id,
                "title": row.title,
                "subject_id": row.subject_id,
                "assessment_type": row.assessment_type.value if hasattr(row.assessment_type, "value") else str(row.assessment_type),
                "starts_at": row.starts_at,
                "ends_at": row.ends_at,
                "duration_sec": row.duration_sec,
            }
            for row in rows
        ], total

    async def start_attempt(self, *, assessment_id: str, student_id: str, batch_id: str | None) -> dict:
        assessment = await self.repo.get_assessment_for_student(
            assessment_id=assessment_id,
            student_id=student_id,
            batch_id=batch_id,
        )
        if not assessment:
            raise NotFoundException("Assessment not found")

        current_count = await self.repo.current_attempt_count(assessment_id=assessment.id, student_id=student_id)
        if current_count >= assessment.attempt_limit:
            raise ForbiddenException("Attempt limit reached")

        attempt = await self.repo.create_attempt(
            assessment=assessment,
            student_id=student_id,
            attempt_no=current_count + 1,
        )
        await self.session.commit()

        return {
            "attempt_id": attempt.id,
            "status": attempt.status.value if hasattr(attempt.status, "value") else str(attempt.status),
            "started_at": attempt.started_at,
            "expires_at": attempt.expires_at,
        }

    async def save_answer(self, *, attempt_id: str, student_id: str, question_id: str, answer_payload: dict) -> None:
        attempt = await self.repo.get_attempt(attempt_id=attempt_id, student_id=student_id)
        if not attempt:
            raise NotFoundException("Attempt not found")

        await self.repo.upsert_answer(attempt_id=attempt_id, question_id=question_id, answer_payload=answer_payload)
        await self.session.commit()

    async def submit_attempt(self, *, attempt_id: str, student_id: str) -> dict:
        attempt = await self.repo.get_attempt(attempt_id=attempt_id, student_id=student_id)
        if not attempt:
            raise NotFoundException("Attempt not found")

        updated = await self.repo.submit_attempt(attempt)
        await self.session.commit()

        return {
            "attempt_id": updated.id,
            "status": updated.status.value if hasattr(updated.status, "value") else str(updated.status),
            "started_at": updated.started_at,
            "expires_at": updated.expires_at,
        }
