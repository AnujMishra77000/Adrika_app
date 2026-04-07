from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.keys import student_notices_key
from app.cache.utils import delete_keys, get_json, set_json
from app.core.exceptions import NotFoundException
from app.repositories.notice_repo import NoticeRepository


class NoticeService:
    def __init__(self, session: AsyncSession, cache: Redis) -> None:
        self.session = session
        self.notice_repo = NoticeRepository(session)
        self.cache = cache

    async def list_for_student(self, *, user_id: str, student_id: str, batch_id: str | None, limit: int, offset: int) -> tuple[list[dict], int]:
        key = student_notices_key(student_id, limit, offset)
        cached = await get_json(self.cache, key)
        if cached:
            return cached["items"], int(cached["total"])

        rows, total = await self.notice_repo.list_for_student(
            user_id=user_id,
            student_id=student_id,
            batch_id=batch_id,
            limit=limit,
            offset=offset,
        )
        items = [
            {
                "id": notice.id,
                "title": notice.title,
                "body_preview": notice.body[:200],
                "priority": notice.priority,
                "publish_at": notice.publish_at,
                "is_read": bool(is_read),
            }
            for notice, is_read in rows
        ]
        await set_json(self.cache, key, {"items": items, "total": total}, ttl_seconds=120)
        return items, total

    async def detail_for_student(self, *, notice_id: str, user_id: str, student_id: str, batch_id: str | None) -> dict:
        notice, is_read = await self.notice_repo.get_notice_for_student(
            notice_id=notice_id,
            user_id=user_id,
            student_id=student_id,
            batch_id=batch_id,
        )
        if not notice:
            raise NotFoundException("Notice not found")

        return {
            "id": notice.id,
            "title": notice.title,
            "body": notice.body,
            "priority": notice.priority,
            "publish_at": notice.publish_at,
            "is_read": is_read,
        }

    async def mark_read(self, *, notice_id: str, user_id: str, student_id: str) -> None:
        await self.notice_repo.mark_read(notice_id=notice_id, user_id=user_id)
        await self.session.commit()
        await delete_keys(self.cache, [student_notices_key(student_id, 20, 0)])
