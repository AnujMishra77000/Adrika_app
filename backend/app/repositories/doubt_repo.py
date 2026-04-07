from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.doubt import Doubt, DoubtMessage


class DoubtRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_student(
        self,
        *,
        student_id: str,
        status: str | None,
        subject_id: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Doubt], int]:
        filters = [Doubt.student_id == student_id]
        if status:
            filters.append(Doubt.status == status)
        if subject_id:
            filters.append(Doubt.subject_id == subject_id)
        if query:
            filters.append(Doubt.topic.ilike(f"%{query}%"))

        base = select(Doubt).where(*filters)
        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (
            await self.session.execute(base.order_by(Doubt.created_at.desc()).limit(limit).offset(offset))
        ).scalars().all()
        return rows, total

    async def create_doubt(self, *, student_id: str, subject_id: str, topic: str, description: str) -> Doubt:
        doubt = Doubt(student_id=student_id, subject_id=subject_id, topic=topic, description=description)
        self.session.add(doubt)
        await self.session.flush()
        return doubt

    async def get_doubt_for_student(self, *, doubt_id: str, student_id: str) -> Doubt | None:
        result = await self.session.execute(
            select(Doubt).where(Doubt.id == doubt_id, Doubt.student_id == student_id)
        )
        return result.scalar_one_or_none()

    async def add_message(self, *, doubt_id: str, sender_user_id: str, message: str) -> DoubtMessage:
        doubt_message = DoubtMessage(doubt_id=doubt_id, sender_user_id=sender_user_id, message=message)
        self.session.add(doubt_message)
        await self.session.flush()
        return doubt_message

    async def list_messages(self, *, doubt_id: str) -> list[DoubtMessage]:
        rows = (
            await self.session.execute(
                select(DoubtMessage).where(DoubtMessage.doubt_id == doubt_id).order_by(DoubtMessage.created_at.asc())
            )
        ).scalars().all()
        return rows
