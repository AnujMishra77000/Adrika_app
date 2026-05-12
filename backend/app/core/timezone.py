from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def app_timezone() -> ZoneInfo:
    settings = get_settings()
    return ZoneInfo(settings.app_timezone)


def ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def to_app_timezone(value: datetime | None) -> datetime | None:
    normalized = ensure_utc(value)
    if normalized is None:
        return None
    return normalized.astimezone(app_timezone())
