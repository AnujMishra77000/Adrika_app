from datetime import datetime

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_student_profile, get_current_user
from app.cache.redis_client import get_redis
from app.db.session import get_db_session
from app.schemas.doubt import AddDoubtMessageDTO, CreateDoubtDTO, CreateLectureDoubtDTO
from app.services.doubt_service import DoubtService
from app.utils.pagination import build_meta

router = APIRouter(prefix="/students/me/doubts", tags=["doubts"])


@router.get("")
async def list_doubts(
    status: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    items, total = await DoubtService(session, cache).list_for_student(
        student_id=student_profile.id,
        status=status,
        subject_id=subject_id,
        query=q,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/lectures/done")
async def list_done_lectures(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    items, total = await DoubtService(session, cache).list_done_lectures_for_student(
        student_id=student_profile.id,
        batch_id=student_profile.current_batch_id,
        class_name=student_profile.class_name,
        stream=student_profile.stream,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/lectures/done/{lecture_id}")
async def done_lecture_detail(
    lecture_id: str,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    return await DoubtService(session, cache).lecture_detail_for_student(
        student_id=student_profile.id,
        lecture_id=lecture_id,
        batch_id=student_profile.current_batch_id,
        class_name=student_profile.class_name,
        stream=student_profile.stream,
    )


@router.post("/lectures/done/{lecture_id}/raise")
async def raise_from_lecture(
    lecture_id: str,
    payload: CreateLectureDoubtDTO,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    return await DoubtService(session, cache).create_from_lecture(
        student_id=student_profile.id,
        batch_id=student_profile.current_batch_id,
        class_name=student_profile.class_name,
        stream=student_profile.stream,
        lecture_id=lecture_id,
        topic=payload.topic,
        description=payload.description,
    )


@router.post("")
async def create_doubt(
    payload: CreateDoubtDTO,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    return await DoubtService(session, cache).create(
        student_id=student_profile.id,
        subject_id=payload.subject_id,
        lecture_id=payload.lecture_id,
        teacher_id=payload.teacher_id,
        topic=payload.topic,
        description=payload.description,
    )


@router.get("/{doubt_id}")
async def detail(
    doubt_id: str,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    return await DoubtService(session, cache).get_detail(student_id=student_profile.id, doubt_id=doubt_id)


@router.get("/{doubt_id}/messages")
async def list_messages(
    doubt_id: str,
    since: datetime | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    items = await DoubtService(session, cache).list_messages(
        student_id=student_profile.id,
        doubt_id=doubt_id,
        since=since,
    )
    return {"items": items}


@router.post("/{doubt_id}/messages")
async def add_message(
    doubt_id: str,
    payload: AddDoubtMessageDTO,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    return await DoubtService(session, cache).add_message(
        student_id=student_profile.id,
        user_id=current_user.id,
        doubt_id=doubt_id,
        message=payload.message,
    )
