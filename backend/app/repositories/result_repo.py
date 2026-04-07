from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.assessment import Assessment
from app.db.models.results import Result, StudentProgressSnapshot


class ResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_results(
        self,
        *,
        student_id: str,
        subject_id: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Result], int]:
        base = select(Result).where(Result.student_id == student_id)

        if subject_id:
            base = base.join(Assessment, Assessment.id == Result.assessment_id).where(
                Assessment.subject_id == subject_id
            )

        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (
            await self.session.execute(base.order_by(Result.published_at.desc()).limit(limit).offset(offset))
        ).scalars().all()
        return rows, total

    async def list_progress(
        self,
        *,
        student_id: str,
        period_type: str | None,
        limit: int,
    ) -> list[StudentProgressSnapshot]:
        filters = [StudentProgressSnapshot.student_id == student_id]
        if period_type:
            filters.append(StudentProgressSnapshot.period_type == period_type)

        rows = (
            await self.session.execute(
                select(StudentProgressSnapshot)
                .where(and_(*filters))
                .order_by(StudentProgressSnapshot.period_start.desc())
                .limit(limit)
            )
        ).scalars().all()
        return rows
