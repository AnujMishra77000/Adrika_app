from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_student_profile
from app.db.session import get_db_session
from app.schemas.suggestion import SuggestionMessageCreateDTO
from app.services.suggestion_service import SuggestionService
from app.utils.pagination import build_meta

router = APIRouter(prefix="/students/me/suggestions", tags=["suggestions"])


@router.get("/messages")
async def student_list_suggestion_messages(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    payload = await SuggestionService(session).student_get_messages(
        student_profile=student_profile,
        limit=limit,
        offset=offset,
    )
    return {
        "thread": payload["thread"],
        "items": payload["items"],
        "meta": build_meta(total=payload["total"], limit=limit, offset=offset),
    }


@router.post("/messages")
async def student_send_suggestion_message(
    payload: SuggestionMessageCreateDTO,
    session: AsyncSession = Depends(get_db_session),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    return await SuggestionService(session).student_send_message(
        student_profile=student_profile,
        message=payload.message,
    )
