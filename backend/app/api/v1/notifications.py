from fastapi import APIRouter, Depends, Query, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.cache.redis_client import get_redis
from app.db.session import get_db_session
from app.schemas.notification import (
    DeviceRegisterDTO,
    DeviceRegisterResponseDTO,
    NotificationSendDTO,
)
from app.services.notification_service import NotificationService
from app.utils.pagination import build_meta

router = APIRouter(tags=["notifications"])
student_router = APIRouter(prefix="/students/me/notifications", tags=["notifications"])
notification_router = APIRouter(prefix="/notifications", tags=["notifications"])
device_router = APIRouter(prefix="/devices", tags=["devices"])


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


@student_router.get("")
async def list_student_notifications(
    is_read: bool | None = Query(default=None),
    since_hours: int | None = Query(default=None, ge=1, le=168),
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
        since_hours=since_hours,
        limit=limit,
        offset=offset,
    )
    unread_count = await service.unread_count(user_id=current_user.id)
    return {
        "items": items,
        "meta": build_meta(total=total, limit=limit, offset=offset),
        "unread_count": unread_count,
    }


@student_router.post("/{notification_id}/read")
async def mark_student_notification_read(
    notification_id: str,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    unread_count = await NotificationService(session, cache).mark_read(
        user_id=current_user.id,
        notification_id=notification_id,
    )
    return {"message": "Marked as read", "unread_count": unread_count}


@student_router.post("/read-all")
async def mark_all_student_notifications_read(
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    unread_count = await NotificationService(session, cache).mark_all_read(user_id=current_user.id)
    return {"message": "All notifications marked as read", "unread_count": unread_count}


@notification_router.get("")
async def list_notifications(
    is_read: bool | None = Query(default=None),
    since_hours: int | None = Query(default=None, ge=1, le=168),
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
        since_hours=since_hours,
        limit=limit,
        offset=offset,
    )
    unread_count = await service.unread_count(user_id=current_user.id)
    return {
        "items": items,
        "meta": build_meta(total=total, limit=limit, offset=offset),
        "unread_count": unread_count,
    }


@notification_router.get("/unread-count")
async def unread_count(
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    count = await NotificationService(session, cache).unread_count(user_id=current_user.id)
    return {"unread_count": count}


@notification_router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    unread = await NotificationService(session, cache).mark_read(
        user_id=current_user.id,
        notification_id=notification_id,
    )
    return {"message": "Marked as read", "unread_count": unread}


@notification_router.post("/read-all")
async def mark_all_read(
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    unread = await NotificationService(session, cache).mark_all_read(user_id=current_user.id)
    return {"message": "All notifications marked as read", "unread_count": unread}


@notification_router.post("/send", dependencies=[Depends(require_roles("admin", "teacher"))])
async def send_notification(
    payload: NotificationSendDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    return await NotificationService(session, cache).send_to_targets(
        title=payload.title,
        body=payload.body,
        notification_type=payload.notification_type,
        targets=[item.model_dump() for item in payload.targets],
        metadata=payload.metadata,
        actor_user_id=current_user.id,
        audit_action="notification.send",
        audit_ip_address=_client_ip(request),
    )


@device_router.post("/register", response_model=DeviceRegisterResponseDTO)
async def register_device(
    payload: DeviceRegisterDTO,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> DeviceRegisterResponseDTO:
    row = await NotificationService(session, cache).register_device(
        user_id=current_user.id,
        device_id=payload.device_id,
        platform=payload.platform,
        push_token=payload.push_token,
    )
    return DeviceRegisterResponseDTO.model_validate(row, from_attributes=True)


router.include_router(student_router)
router.include_router(notification_router)
router.include_router(device_router)
