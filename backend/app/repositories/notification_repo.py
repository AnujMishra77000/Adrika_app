from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import NotificationType
from app.db.models.notification import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, *, user_id: str, is_read: bool | None, limit: int, offset: int) -> tuple[list[Notification], int]:
        filters = [Notification.recipient_user_id == user_id]
        if is_read is not None:
            filters.append(Notification.is_read == is_read)

        base = select(Notification).where(*filters)
        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (
            await self.session.execute(base.order_by(Notification.created_at.desc()).limit(limit).offset(offset))
        ).scalars().all()
        return rows, total

    async def unread_count(self, *, user_id: str) -> int:
        stmt = select(func.count()).where(Notification.recipient_user_id == user_id, Notification.is_read.is_(False))
        return (await self.session.execute(stmt)).scalar_one()

    async def unread_count_by_type(self, *, user_id: str, notification_type: NotificationType) -> int:
        stmt = select(func.count()).where(
            Notification.recipient_user_id == user_id,
            Notification.notification_type == notification_type,
            Notification.is_read.is_(False),
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def mark_read(self, *, notification_id: str, user_id: str) -> None:
        await self.session.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.recipient_user_id == user_id)
            .values(is_read=True)
        )

    async def mark_all_read(self, *, user_id: str) -> None:
        await self.session.execute(
            update(Notification).where(Notification.recipient_user_id == user_id).values(is_read=True)
        )

    async def mark_all_read_by_type(self, *, user_id: str, notification_type: NotificationType) -> None:
        await self.session.execute(
            update(Notification)
            .where(
                Notification.recipient_user_id == user_id,
                Notification.notification_type == notification_type,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
