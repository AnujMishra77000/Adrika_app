from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.result_repo import ResultRepository


class ResultService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = ResultRepository(session)

    async def list_results(
        self,
        *,
        student_id: str,
        subject_id: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        rows, total = await self.repo.list_results(
            student_id=student_id,
            subject_id=subject_id,
            limit=limit,
            offset=offset,
        )
        return [
            {
                "id": row.id,
                "assessment_id": row.assessment_id,
                "score": float(row.score),
                "total_marks": float(row.total_marks),
                "rank": row.rank,
                "published_at": row.published_at,
            }
            for row in rows
        ], total

    async def list_progress(self, *, student_id: str, period_type: str | None, limit: int) -> list[dict]:
        rows = await self.repo.list_progress(student_id=student_id, period_type=period_type, limit=limit)
        return [
            {
                "period_type": row.period_type,
                "period_start": row.period_start,
                "metrics": row.metrics,
            }
            for row in rows
        ]
