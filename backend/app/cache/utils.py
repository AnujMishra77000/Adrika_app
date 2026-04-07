import json
from typing import Any

from redis.asyncio import Redis


async def get_json(cache: Redis, key: str) -> Any | None:
    raw = await cache.get(key)
    if not raw:
        return None
    return json.loads(raw)


async def set_json(cache: Redis, key: str, payload: Any, ttl_seconds: int) -> None:
    await cache.set(key, json.dumps(payload, default=str), ex=ttl_seconds)


async def delete_keys(cache: Redis, keys: list[str]) -> None:
    if keys:
        await cache.delete(*keys)
