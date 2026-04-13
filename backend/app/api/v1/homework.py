from datetime import date

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_student_profile, get_current_user
from app.cache.redis_client import get_redis
from app.db.session import get_db_session
from app.services.homework_service import HomeworkService
from app.utils.pagination import build_meta

router = APIRouter(prefix="/students/me/homework", tags=["homework"])


@router.get("")
async def list_homework(
    subject_id: str | None = Query(default=None),
    due_from: date | None = Query(default=None),
    due_to: date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    items, total = await HomeworkService(session, cache).list_for_student(
        user_id=current_user.id,
        student_id=student_profile.id,
        batch_id=student_profile.current_batch_id,
        class_name=student_profile.class_name,
        stream=student_profile.stream,
        subject_id=subject_id,
        due_from=due_from,
        due_to=due_to,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/{homework_id}")
async def homework_detail(
    homework_id: str,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    return await HomeworkService(session, cache).detail_for_student(
        homework_id=homework_id,
        user_id=current_user.id,
        student_id=student_profile.id,
        batch_id=student_profile.current_batch_id,
        class_name=student_profile.class_name,
        stream=student_profile.stream,
    )


@router.post("/read-all")
async def mark_homework_seen(
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    payload = await HomeworkService(session, cache).mark_all_seen(
        user_id=current_user.id,
        student_id=student_profile.id,
        batch_id=student_profile.current_batch_id,
        class_name=student_profile.class_name,
        stream=student_profile.stream,
    )
    return {
        "message": "Homework marked as seen",
        **payload,
    }


@router.post("/{homework_id}/submit")
async def submit_homework(
    homework_id: str,
    file: UploadFile = File(...),
    notes: str | None = Form(default=None),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    return await HomeworkService(session, cache).submit_for_student(
        homework_id=homework_id,
        user_id=current_user.id,
        student_id=student_profile.id,
        batch_id=student_profile.current_batch_id,
        class_name=student_profile.class_name,
        stream=student_profile.stream,
        file=file,
        notes=notes,
    )
