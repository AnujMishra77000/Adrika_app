from datetime import date

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_parent_profile, get_current_user
from app.cache.redis_client import get_redis
from app.db.session import get_db_session
from app.schemas.parent import ParentUpdatePreferenceDTO
from app.services.notification_service import NotificationService
from app.services.parent_service import ParentService
from app.utils.pagination import build_meta

router = APIRouter(prefix="/parents/me", tags=["parents"])


@router.get("/profile")
async def profile(
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    parent_profile=Depends(get_current_parent_profile),
) -> dict:
    return await ParentService(session, cache).profile(parent_profile=parent_profile)


@router.get("/students")
async def list_students(
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    parent_profile=Depends(get_current_parent_profile),
) -> dict:
    items = await ParentService(session, cache).linked_students(parent_id=parent_profile.id)
    return {"items": items}


@router.get("/dashboard")
async def dashboard(
    student_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    parent_profile=Depends(get_current_parent_profile),
) -> dict:
    return await ParentService(session, cache).dashboard(
        user_id=current_user.id,
        parent_id=parent_profile.id,
        student_id=student_id,
    )


@router.get("/students/{student_id}/notices")
async def list_notices(
    student_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    parent_profile=Depends(get_current_parent_profile),
) -> dict:
    items, total = await ParentService(session, cache).list_notices(
        user_id=current_user.id,
        parent_id=parent_profile.id,
        student_id=student_id,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/students/{student_id}/notices/{notice_id}")
async def notice_detail(
    student_id: str,
    notice_id: str,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    parent_profile=Depends(get_current_parent_profile),
) -> dict:
    return await ParentService(session, cache).notice_detail(
        notice_id=notice_id,
        user_id=current_user.id,
        parent_id=parent_profile.id,
        student_id=student_id,
    )


@router.post("/students/{student_id}/notices/{notice_id}/read")
async def mark_notice_read(
    student_id: str,
    notice_id: str,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    parent_profile=Depends(get_current_parent_profile),
) -> dict:
    await ParentService(session, cache).mark_notice_read(
        notice_id=notice_id,
        user_id=current_user.id,
        parent_id=parent_profile.id,
        student_id=student_id,
    )
    return {"message": "Marked as read"}


@router.get("/students/{student_id}/homework")
async def list_homework(
    student_id: str,
    subject_id: str | None = Query(default=None),
    due_from: date | None = Query(default=None),
    due_to: date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    parent_profile=Depends(get_current_parent_profile),
) -> dict:
    items, total = await ParentService(session, cache).list_homework(
        parent_id=parent_profile.id,
        student_id=student_id,
        subject_id=subject_id,
        due_from=due_from,
        due_to=due_to,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/students/{student_id}/attendance")
async def list_attendance(
    student_id: str,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    parent_profile=Depends(get_current_parent_profile),
) -> dict:
    items, total, summary = await ParentService(session, cache).attendance(
        parent_id=parent_profile.id,
        student_id=student_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "meta": build_meta(total=total, limit=limit, offset=offset),
        "summary": summary,
    }


@router.get("/students/{student_id}/results")
async def list_results(
    student_id: str,
    subject_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    parent_profile=Depends(get_current_parent_profile),
) -> dict:
    items, total = await ParentService(session, cache).results(
        parent_id=parent_profile.id,
        student_id=student_id,
        subject_id=subject_id,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/students/{student_id}/progress")
async def list_progress(
    student_id: str,
    period_type: str | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=50),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    parent_profile=Depends(get_current_parent_profile),
) -> dict:
    items = await ParentService(session, cache).progress(
        parent_id=parent_profile.id,
        student_id=student_id,
        period_type=period_type,
        limit=limit,
    )
    return {"items": items}


@router.get("/students/{student_id}/fees")
async def list_fees(
    student_id: str,
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    parent_profile=Depends(get_current_parent_profile),
) -> dict:
    items, total = await ParentService(session, cache).list_fee_invoices(
        parent_id=parent_profile.id,
        student_id=student_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/students/{student_id}/payments")
async def list_payments(
    student_id: str,
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    parent_profile=Depends(get_current_parent_profile),
) -> dict:
    items, total = await ParentService(session, cache).list_payments(
        parent_id=parent_profile.id,
        student_id=student_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/preferences")
async def get_preferences(
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    parent_profile=Depends(get_current_parent_profile),
) -> dict:
    return await ParentService(session, cache).get_preferences(parent_id=parent_profile.id)


@router.put("/preferences")
async def update_preferences(
    payload: ParentUpdatePreferenceDTO,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    parent_profile=Depends(get_current_parent_profile),
) -> dict:
    return await ParentService(session, cache).update_preferences(
        parent_id=parent_profile.id,
        in_app_enabled=payload.in_app_enabled,
        push_enabled=payload.push_enabled,
        whatsapp_enabled=payload.whatsapp_enabled,
        fee_reminders_enabled=payload.fee_reminders_enabled,
        preferred_language=payload.preferred_language,
    )


@router.get("/notifications")
async def list_notifications(
    is_read: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    _parent_profile=Depends(get_current_parent_profile),
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


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    _parent_profile=Depends(get_current_parent_profile),
) -> dict:
    await NotificationService(session, cache).mark_read(user_id=current_user.id, notification_id=notification_id)
    return {"message": "Marked as read"}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    _parent_profile=Depends(get_current_parent_profile),
) -> dict:
    await NotificationService(session, cache).mark_all_read(user_id=current_user.id)
    return {"message": "All notifications marked as read"}
