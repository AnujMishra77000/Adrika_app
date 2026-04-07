from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.keys import student_content_key
from app.cache.utils import get_json, set_json
from app.repositories.content_repo import ContentRepository


class ContentService:
    def __init__(self, session: AsyncSession, cache: Redis) -> None:
        self.repo = ContentRepository(session)
        self.cache = cache

    async def get_student_content(self) -> dict:
        key = student_content_key()
        cached = await get_json(self.cache, key)
        if cached:
            return cached

        now = datetime.now(UTC)
        daily_thought = await self.repo.get_daily_thought(for_date=now.date())
        banners = await self.repo.list_active_banners(at_time=now, limit=5)

        payload = {
            "daily_thought": {
                "id": daily_thought.id,
                "thought_date": daily_thought.thought_date,
                "text": daily_thought.text,
            }
            if daily_thought
            else None,
            "banners": [
                {
                    "id": banner.id,
                    "title": banner.title,
                    "media_url": banner.media_url,
                    "action_url": banner.action_url,
                    "active_from": banner.active_from,
                    "active_to": banner.active_to,
                    "priority": banner.priority,
                    "is_popup": banner.is_popup,
                }
                for banner in banners
            ],
        }

        await set_json(self.cache, key, payload, ttl_seconds=120)
        return payload
