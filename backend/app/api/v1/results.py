from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_student_profile
from app.db.session import get_db_session
from app.services.result_service import ResultService
from app.utils.pagination import build_meta

router = APIRouter(prefix="/students/me", tags=["results"])


@router.get("/results")
async def list_results(
    subject_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    items, total = await ResultService(session).list_results(
        student_id=student_profile.id,
        subject_id=subject_id,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/progress")
async def list_progress(
    period_type: str | None = Query(default=None),
    limit: int = Query(default=6, ge=1, le=24),
    session: AsyncSession = Depends(get_db_session),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    items = await ResultService(session).list_progress(
        student_id=student_profile.id,
        period_type=period_type,
        limit=limit,
    )
    return {"items": items}
