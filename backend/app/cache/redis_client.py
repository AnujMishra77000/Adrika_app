from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Protocol

import structlog
from redis.asyncio import Redis

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger(__name__)


class CacheClient(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ex: int | None = None): ...

    async def delete(self, *keys: str): ...


class InMemoryCacheClient:
    """Small async cache fallback when Redis is unavailable in local dev."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._expires_at: dict[str, float] = {}
        self._lock = asyncio.Lock()

    def _purge_expired_key(self, key: str) -> None:
        expires_at = self._expires_at.get(key)
        if expires_at is not None and time.time() >= expires_at:
            self._store.pop(key, None)
            self._expires_at.pop(key, None)

    async def get(self, key: str) -> str | None:
        async with self._lock:
            self._purge_expired_key(key)
            return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        async with self._lock:
            self._store[key] = value
            if ex is None:
                self._expires_at.pop(key, None)
            else:
                self._expires_at[key] = time.time() + ex
        return True

    async def delete(self, *keys: str) -> int:
        deleted = 0
        async with self._lock:
            for key in keys:
                existed = key in self._store
                self._store.pop(key, None)
                self._expires_at.pop(key, None)
                if existed:
                    deleted += 1
        return deleted


redis_client = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
memory_cache_client = InMemoryCacheClient()

_cache_client: CacheClient = redis_client
_cache_probe_done = False
_cache_probe_lock = asyncio.Lock()


async def _resolve_cache_client() -> CacheClient:
    global _cache_client, _cache_probe_done
    if _cache_probe_done:
        return _cache_client

    async with _cache_probe_lock:
        if _cache_probe_done:
            return _cache_client

        try:
            await redis_client.ping()
            _cache_client = redis_client
            logger.info("cache_backend_selected", backend="redis")
        except Exception as exc:  # pragma: no cover - runtime fallback branch
            _cache_client = memory_cache_client
            logger.warning("cache_backend_fallback", backend="memory", reason=str(exc))

        _cache_probe_done = True
        return _cache_client


async def get_redis() -> AsyncGenerator[CacheClient, None]:
    yield await _resolve_cache_client()
