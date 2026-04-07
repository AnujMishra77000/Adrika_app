from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.content import Banner, DailyThought


class ContentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active_banners(self, *, at_time: datetime, limit: int) -> list[Banner]:
        stmt = (
            select(Banner)
            .where(Banner.active_from <= at_time, Banner.active_to >= at_time)
            .order_by(Banner.priority.desc(), Banner.active_from.desc())
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def get_daily_thought(self, *, for_date: date) -> DailyThought | None:
        exact_stmt = select(DailyThought).where(
            DailyThought.thought_date == for_date,
            DailyThought.is_active.is_(True),
        )
        exact = (await self.session.execute(exact_stmt)).scalar_one_or_none()
        if exact:
            return exact

        fallback_stmt = (
            select(DailyThought)
            .where(DailyThought.thought_date <= for_date, DailyThought.is_active.is_(True))
            .order_by(DailyThought.thought_date.desc())
            .limit(1)
        )
        return (await self.session.execute(fallback_stmt)).scalar_one_or_none()
