from datetime import date

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_student_profile
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
    student_profile=Depends(get_current_student_profile),
) -> dict:
    items, total = await HomeworkService(session, cache).list_for_student(
        student_id=student_profile.id,
        batch_id=student_profile.current_batch_id,
        subject_id=subject_id,
        due_from=due_from,
        due_to=due_to,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}
