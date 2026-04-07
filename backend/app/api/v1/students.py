from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_student_profile, get_current_user
from app.cache.redis_client import get_redis
from app.db.session import get_db_session
from app.services.content_service import ContentService
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/students/me", tags=["students"])


@router.get("/profile")
async def profile(student_profile=Depends(get_current_student_profile)) -> dict:
    return {
        "student_id": student_profile.id,
        "user_id": student_profile.user_id,
        "full_name": student_profile.user.full_name,
        "admission_no": student_profile.admission_no,
        "roll_no": student_profile.roll_no,
        "current_batch_id": student_profile.current_batch_id,
    }


@router.get("/dashboard")
async def dashboard(
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    return await DashboardService(session, cache).get_student_dashboard(
        user_id=current_user.id,
        student_id=student_profile.id,
        batch_id=student_profile.current_batch_id,
    )


@router.get("/content")
async def content(
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    student_profile=Depends(get_current_student_profile),
) -> dict:
    _ = student_profile
    return await ContentService(session, cache).get_student_content()
