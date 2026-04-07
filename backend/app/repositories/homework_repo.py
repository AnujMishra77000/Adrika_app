from datetime import date

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import HomeworkStatus
from app.db.models.homework import Homework, HomeworkTarget


class HomeworkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_student(
        self,
        *,
        student_id: str,
        batch_id: str | None,
        subject_id: str | None,
        due_from: date | None,
        due_to: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Homework], int]:
        target_filters = [
            and_(HomeworkTarget.target_type == "all", HomeworkTarget.target_id == "all"),
            and_(HomeworkTarget.target_type == "student", HomeworkTarget.target_id == student_id),
        ]
        if batch_id:
            target_filters.append(and_(HomeworkTarget.target_type == "batch", HomeworkTarget.target_id == batch_id))

        filters = [Homework.status == HomeworkStatus.PUBLISHED, or_(*target_filters)]
        if subject_id:
            filters.append(Homework.subject_id == subject_id)
        if due_from:
            filters.append(Homework.due_date >= due_from)
        if due_to:
            filters.append(Homework.due_date <= due_to)

        base = (
            select(Homework)
            .join(HomeworkTarget, HomeworkTarget.homework_id == Homework.id)
            .where(*filters)
            .distinct()
        )

        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

        rows = (
            await self.session.execute(
                base.order_by(Homework.due_date.asc(), Homework.created_at.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()
        return rows, total

    async def pending_count_for_student(self, *, student_id: str, batch_id: str | None) -> int:
        target_filters = [
            and_(HomeworkTarget.target_type == "all", HomeworkTarget.target_id == "all"),
            and_(HomeworkTarget.target_type == "student", HomeworkTarget.target_id == student_id),
        ]
        if batch_id:
            target_filters.append(and_(HomeworkTarget.target_type == "batch", HomeworkTarget.target_id == batch_id))

        stmt = (
            select(func.count())
            .select_from(Homework)
            .join(HomeworkTarget, HomeworkTarget.homework_id == Homework.id)
            .where(Homework.status == HomeworkStatus.PUBLISHED, or_(*target_filters))
        )
        return (await self.session.execute(stmt)).scalar_one()
