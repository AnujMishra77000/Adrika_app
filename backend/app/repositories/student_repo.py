from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.academic import StudentProfile


class StudentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_profile_by_user_id(self, user_id: str) -> StudentProfile | None:
        result = await self.session.execute(select(StudentProfile).where(StudentProfile.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_profile_by_id(self, student_id: str) -> StudentProfile | None:
        result = await self.session.execute(select(StudentProfile).where(StudentProfile.id == student_id))
        return result.scalar_one_or_none()

    async def list_profiles_by_ids(self, student_ids: list[str]) -> list[StudentProfile]:
        if not student_ids:
            return []
        rows = (
            await self.session.execute(
                select(StudentProfile).where(StudentProfile.id.in_(student_ids)).order_by(StudentProfile.created_at.asc())
            )
        ).scalars().all()
        return rows
