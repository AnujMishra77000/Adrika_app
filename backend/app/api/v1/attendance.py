from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_student_profile
from app.db.session import get_db_session
from app.services.attendance_service import AttendanceService
from app.utils.pagination import build_meta

router = APIRouter(prefix="/students/me/attendance", tags=["attendance"])


@router.get("")
async def list_attendance(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    items, total = await AttendanceService(session).list_for_student(
        student_id=student_profile.id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/summary")
async def attendance_summary(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    return await AttendanceService(session).summary_for_student(
        student_id=student_profile.id,
        date_from=date_from,
        date_to=date_to,
    )
