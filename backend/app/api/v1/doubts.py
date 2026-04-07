from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_student_profile, get_current_user
from app.db.session import get_db_session
from app.schemas.doubt import AddDoubtMessageDTO, CreateDoubtDTO
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
    student_profile=Depends(get_current_student_profile),
) -> dict:
    items, total = await DoubtService(session).list_for_student(
        student_id=student_profile.id,
        status=status,
        subject_id=subject_id,
        query=q,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("")
async def create_doubt(
    payload: CreateDoubtDTO,
    session: AsyncSession = Depends(get_db_session),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    return await DoubtService(session).create(
        student_id=student_profile.id,
        subject_id=payload.subject_id,
        topic=payload.topic,
        description=payload.description,
    )


@router.get("/{doubt_id}")
async def detail(
    doubt_id: str,
    session: AsyncSession = Depends(get_db_session),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    return await DoubtService(session).get_detail(student_id=student_profile.id, doubt_id=doubt_id)


@router.post("/{doubt_id}/messages")
async def add_message(
    doubt_id: str,
    payload: AddDoubtMessageDTO,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    return await DoubtService(session).add_message(
        student_id=student_profile.id,
        user_id=current_user.id,
        doubt_id=doubt_id,
        message=payload.message,
    )
