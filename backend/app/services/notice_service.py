import re

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

    @staticmethod
    def _extract_class_level(class_name: str | None) -> int | None:
        if not class_name:
            return None
        match = re.search(r"(10|11|12)", class_name)
        if not match:
            return None
        return int(match.group(1))

    @staticmethod
    def _serialize_attachment(attachment) -> dict:
        return {
            "id": attachment.id,
            "attachment_type": attachment.attachment_type,
            "file_name": attachment.file_name,
            "file_url": attachment.file_url,
            "content_type": attachment.content_type,
            "file_size_bytes": attachment.file_size_bytes,
            "image_width": attachment.image_width,
            "image_height": attachment.image_height,
            "created_at": attachment.created_at,
        }

    async def list_for_student(
        self,
        *,
        user_id: str,
        student_id: str,
        batch_id: str | None,
        class_name: str | None,
        stream: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        key = student_notices_key(student_id, limit, offset)
        cached = await get_json(self.cache, key)
        if cached:
            return cached["items"], int(cached["total"])

        class_level = self._extract_class_level(class_name)
        rows, total = await self.notice_repo.list_for_student(
            user_id=user_id,
            student_id=student_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=stream,
            limit=limit,
            offset=offset,
        )
        notice_ids = [notice.id for notice, _ in rows]
        attachment_map = await self.notice_repo.list_attachments_for_notice_ids(notice_ids=notice_ids)

        items = [
            {
                "id": notice.id,
                "title": notice.title,
                "body_preview": notice.body[:200],
                "priority": notice.priority,
                "publish_at": notice.publish_at,
                "is_read": bool(is_read),
                "attachment_count": len(attachment_map.get(notice.id, [])),
            }
            for notice, is_read in rows
        ]
        await set_json(self.cache, key, {"items": items, "total": total}, ttl_seconds=120)
        return items, total

    async def detail_for_student(
        self,
        *,
        notice_id: str,
        user_id: str,
        student_id: str,
        batch_id: str | None,
        class_name: str | None,
        stream: str | None,
    ) -> dict:
        class_level = self._extract_class_level(class_name)
        notice, is_read = await self.notice_repo.get_notice_for_student(
            notice_id=notice_id,
            user_id=user_id,
            student_id=student_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=stream,
        )
        if not notice:
            raise NotFoundException("Notice not found")

        attachments = await self.notice_repo.list_attachments_for_notice(notice_id=notice_id)

        return {
            "id": notice.id,
            "title": notice.title,
            "body": notice.body,
            "priority": notice.priority,
            "publish_at": notice.publish_at,
            "is_read": is_read,
            "attachments": [self._serialize_attachment(attachment) for attachment in attachments],
        }

    async def mark_read(self, *, notice_id: str, user_id: str, student_id: str) -> None:
        await self.notice_repo.mark_read(notice_id=notice_id, user_id=user_id)
        await self.session.commit()
        await delete_keys(self.cache, [student_notices_key(student_id, 20, 0)])
