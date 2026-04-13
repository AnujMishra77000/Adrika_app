from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_teacher_profile, get_current_user
from app.cache.redis_client import get_redis
from app.db.session import get_db_session
from app.schemas.doubt import TeacherCompleteLectureDTO
from app.schemas.teacher import TeacherAddDoubtMessageDTO, TeacherUpdateDoubtStatusDTO
from app.services.notification_service import NotificationService
from app.services.lecture_schedule_service import LectureScheduleService
from app.services.teacher_service import TeacherService
from app.utils.pagination import build_meta

router = APIRouter(prefix="/teachers/me", tags=["teachers"])


@router.get("/profile")
async def profile(
    teacher_profile=Depends(get_current_teacher_profile),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
) -> dict:
    return await TeacherService(session, cache).profile(teacher_profile=teacher_profile)


@router.get("/dashboard")
async def dashboard(
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    teacher_profile=Depends(get_current_teacher_profile),
) -> dict:
    return await TeacherService(session, cache).dashboard(
        user_id=current_user.id,
        teacher_id=teacher_profile.id,
    )


@router.get("/assignments")
async def assignments(
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    teacher_profile=Depends(get_current_teacher_profile),
) -> dict:
    items = await TeacherService(session, cache).list_assignments(teacher_id=teacher_profile.id)
    return {"items": items}


@router.get("/lectures/done")
async def list_completed_lectures(
    class_level: int | None = Query(default=None, ge=10, le=12),
    stream: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    teacher_profile=Depends(get_current_teacher_profile),
) -> dict:
    items, total = await TeacherService(session, cache).list_completed_lectures(
        teacher_id=teacher_profile.id,
        class_level=class_level,
        stream=stream,
        subject_id=subject_id,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/lectures/done")
async def create_completed_lecture(
    payload: TeacherCompleteLectureDTO,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    teacher_profile=Depends(get_current_teacher_profile),
) -> dict:
    return await TeacherService(session, cache).create_completed_lecture(
        teacher_id=teacher_profile.id,
        payload=payload,
    )


@router.get("/lectures/scheduled")
async def list_scheduled_lectures(
    status: str | None = Query(default="scheduled"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    teacher_profile=Depends(get_current_teacher_profile),
) -> dict:
    items, total = await LectureScheduleService(session).list_for_teacher(
        teacher_id=teacher_profile.id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/notices")
async def list_notices(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    teacher_profile=Depends(get_current_teacher_profile),
) -> dict:
    items, total = await TeacherService(session, cache).list_notices(
        user_id=current_user.id,
        teacher_id=teacher_profile.id,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/notices/{notice_id}")
async def notice_detail(
    notice_id: str,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    teacher_profile=Depends(get_current_teacher_profile),
) -> dict:
    return await TeacherService(session, cache).notice_detail(
        notice_id=notice_id,
        user_id=current_user.id,
        teacher_id=teacher_profile.id,
    )


@router.post("/notices/{notice_id}/read")
async def mark_notice_read(
    notice_id: str,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    teacher_profile=Depends(get_current_teacher_profile),
) -> dict:
    await TeacherService(session, cache).mark_notice_read(
        notice_id=notice_id,
        user_id=current_user.id,
        teacher_id=teacher_profile.id,
    )
    return {"message": "Marked as read"}


@router.get("/homework")
async def list_homework(
    subject_id: str | None = Query(default=None),
    due_from: date | None = Query(default=None),
    due_to: date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    teacher_profile=Depends(get_current_teacher_profile),
) -> dict:
    items, total = await TeacherService(session, cache).list_homework(
        teacher_id=teacher_profile.id,
        subject_id=subject_id,
        due_from=due_from,
        due_to=due_to,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/tests")
async def list_tests(
    assessment_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    teacher_profile=Depends(get_current_teacher_profile),
) -> dict:
    items, total = await TeacherService(session, cache).list_assessments(
        teacher_id=teacher_profile.id,
        assessment_type=assessment_type,
        status=status,
        subject_id=subject_id,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/doubts")
async def list_doubts(
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    teacher_profile=Depends(get_current_teacher_profile),
) -> dict:
    items, total = await TeacherService(session, cache).list_doubts(
        teacher_id=teacher_profile.id,
        status=status,
        query=q,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/doubts/{doubt_id}")
async def doubt_detail(
    doubt_id: str,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    teacher_profile=Depends(get_current_teacher_profile),
) -> dict:
    return await TeacherService(session, cache).doubt_detail(
        teacher_id=teacher_profile.id,
        doubt_id=doubt_id,
    )


@router.get("/doubts/{doubt_id}/messages")
async def list_doubt_messages(
    doubt_id: str,
    since: datetime | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    teacher_profile=Depends(get_current_teacher_profile),
) -> dict:
    items = await TeacherService(session, cache).list_doubt_messages(
        teacher_id=teacher_profile.id,
        doubt_id=doubt_id,
        since=since,
    )
    return {"items": items}


@router.post("/doubts/{doubt_id}/messages")
async def add_doubt_message(
    doubt_id: str,
    payload: TeacherAddDoubtMessageDTO,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    teacher_profile=Depends(get_current_teacher_profile),
) -> dict:
    return await TeacherService(session, cache).add_doubt_message(
        teacher_id=teacher_profile.id,
        user_id=current_user.id,
        doubt_id=doubt_id,
        message=payload.message,
    )


@router.post("/doubts/{doubt_id}/status")
async def update_doubt_status(
    doubt_id: str,
    payload: TeacherUpdateDoubtStatusDTO,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    teacher_profile=Depends(get_current_teacher_profile),
) -> dict:
    return await TeacherService(session, cache).update_doubt_status(
        teacher_id=teacher_profile.id,
        doubt_id=doubt_id,
        status=payload.status,
    )


@router.get("/notifications")
async def list_notifications(
    is_read: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    _teacher_profile=Depends(get_current_teacher_profile),
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
    _teacher_profile=Depends(get_current_teacher_profile),
) -> dict:
    await NotificationService(session, cache).mark_read(user_id=current_user.id, notification_id=notification_id)
    return {"message": "Marked as read"}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    _teacher_profile=Depends(get_current_teacher_profile),
) -> dict:
    await NotificationService(session, cache).mark_all_read(user_id=current_user.id)
    return {"message": "All notifications marked as read"}
