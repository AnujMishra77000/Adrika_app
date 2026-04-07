from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.cache.redis_client import get_redis
from app.db.session import get_db_session
from app.services.notification_service import NotificationService
from app.utils.pagination import build_meta

router = APIRouter(prefix="/students/me/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    is_read: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    service = NotificationService(session, cache)
    items, total = await service.list_for_user(
        user_id=current_user.id,
        is_read=is_read,
        limit=limit,
        offset=offset,
    )
    unread_count = await service.unread_count(user_id=current_user.id)
    return {
        "items": items,
        "meta": build_meta(total=total, limit=limit, offset=offset),
        "unread_count": unread_count,
    }


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    await NotificationService(session, cache).mark_read(user_id=current_user.id, notification_id=notification_id)
    return {"message": "Marked as read"}


@router.post("/read-all")
async def mark_all_read(
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    await NotificationService(session, cache).mark_all_read(user_id=current_user.id)
    return {"message": "All notifications marked as read"}
