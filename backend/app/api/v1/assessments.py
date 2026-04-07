from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_student_profile
from app.db.session import get_db_session
from app.services.assessment_service import AssessmentService
from app.utils.pagination import build_meta

router = APIRouter(prefix="/students/me/tests", tags=["assessments"])


@router.get("")
async def list_tests(
    assessment_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    items, total = await AssessmentService(session).list_for_student(
        student_id=student_profile.id,
        batch_id=student_profile.current_batch_id,
        assessment_type=assessment_type,
        status=status,
        subject_id=subject_id,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/{assessment_id}/attempts")
async def start_attempt(
    assessment_id: str,
    session: AsyncSession = Depends(get_db_session),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    return await AssessmentService(session).start_attempt(
        assessment_id=assessment_id,
        student_id=student_profile.id,
        batch_id=student_profile.current_batch_id,
    )


@router.put("/attempts/{attempt_id}/answers/{question_id}")
async def save_answer(
    attempt_id: str,
    question_id: str,
    payload: dict,
    session: AsyncSession = Depends(get_db_session),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    await AssessmentService(session).save_answer(
        attempt_id=attempt_id,
        student_id=student_profile.id,
        question_id=question_id,
        answer_payload=payload,
    )
    return {"message": "Answer saved"}


@router.post("/attempts/{attempt_id}/submit")
async def submit_attempt(
    attempt_id: str,
    session: AsyncSession = Depends(get_db_session),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    return await AssessmentService(session).submit_attempt(
        attempt_id=attempt_id,
        student_id=student_profile.id,
    )
