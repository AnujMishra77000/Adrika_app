from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_student_profile, get_current_user
from app.cache.redis_client import get_redis
from app.db.session import get_db_session
from app.services.notice_service import NoticeService
from app.utils.pagination import build_meta

router = APIRouter(prefix="/students/me/notices", tags=["notices"])


@router.get("")
async def list_notices(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    items, total = await NoticeService(session, cache).list_for_student(
        user_id=current_user.id,
        student_id=student_profile.id,
        batch_id=student_profile.current_batch_id,
        class_name=student_profile.class_name,
        stream=student_profile.stream,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/{notice_id}")
async def detail(
    notice_id: str,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    return await NoticeService(session, cache).detail_for_student(
        notice_id=notice_id,
        user_id=current_user.id,
        student_id=student_profile.id,
        batch_id=student_profile.current_batch_id,
        class_name=student_profile.class_name,
        stream=student_profile.stream,
    )


@router.post("/{notice_id}/read")
async def mark_read(
    notice_id: str,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    await NoticeService(session, cache).mark_read(
        notice_id=notice_id,
        user_id=current_user.id,
        student_id=student_profile.id,
    )
    return {"message": "Marked as read"}
