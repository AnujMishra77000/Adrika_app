from datetime import date

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.keys import student_homework_key
from app.cache.utils import get_json, set_json
from app.repositories.homework_repo import HomeworkRepository


class HomeworkService:
    def __init__(self, session: AsyncSession, cache: Redis) -> None:
        self.repo = HomeworkRepository(session)
        self.cache = cache

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
    ) -> tuple[list[dict], int]:
        key = student_homework_key(student_id, limit, offset)
        cached = await get_json(self.cache, key)
        if cached:
            return cached["items"], int(cached["total"])

        rows, total = await self.repo.list_for_student(
            student_id=student_id,
            batch_id=batch_id,
            subject_id=subject_id,
            due_from=due_from,
            due_to=due_to,
            limit=limit,
            offset=offset,
        )

        payload = [
            {
                "id": hw.id,
                "title": hw.title,
                "description": hw.description,
                "subject_id": hw.subject_id,
                "due_date": hw.due_date,
                "status": hw.status.value if hasattr(hw.status, "value") else str(hw.status),
            }
            for hw in rows
        ]
        await set_json(self.cache, key, {"items": payload, "total": total}, ttl_seconds=120)
        return payload, total
