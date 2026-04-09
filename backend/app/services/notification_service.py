from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.keys import student_unread_notifications_key
from app.cache.utils import delete_keys, get_json, set_json
from app.repositories.notification_repo import NotificationRepository


class NotificationService:
    def __init__(self, session: AsyncSession, cache: Redis) -> None:
        self.session = session
        self.repo = NotificationRepository(session)
        self.cache = cache

    async def list_for_user(self, *, user_id: str, is_read: bool | None, limit: int, offset: int) -> tuple[list[dict], int]:
        rows, total = await self.repo.list_for_user(user_id=user_id, is_read=is_read, limit=limit, offset=offset)
        return [
            {
                "id": row.id,
                "notification_type": row.notification_type.value if hasattr(row.notification_type, "value") else str(row.notification_type),
                "title": row.title,
                "body": row.body,
                "metadata": row.metadata_json,
                "is_read": row.is_read,
                "created_at": row.created_at,
            }
            for row in rows
        ], total

    async def unread_count(self, *, user_id: str) -> int:
        key = student_unread_notifications_key(user_id)
        cached = await get_json(self.cache, key)
        if isinstance(cached, int):
            return cached

        count = await self.repo.unread_count(user_id=user_id)
        await set_json(self.cache, key, count, ttl_seconds=60)
        return count

    async def mark_read(self, *, user_id: str, notification_id: str) -> None:
        await self.repo.mark_read(user_id=user_id, notification_id=notification_id)
        await self.session.commit()
        await delete_keys(self.cache, [student_unread_notifications_key(user_id)])

    async def mark_all_read(self, *, user_id: str) -> None:
        await self.repo.mark_all_read(user_id=user_id)
        await self.session.commit()
        await delete_keys(self.cache, [student_unread_notifications_key(user_id)])
