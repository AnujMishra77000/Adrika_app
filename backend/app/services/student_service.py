from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.repositories.student_repo import StudentRepository


class StudentService:
    def __init__(self, session: AsyncSession) -> None:
        self.student_repo = StudentRepository(session)

    async def get_profile_or_404(self, *, user_id: str):
        profile = await self.student_repo.get_profile_by_user_id(user_id)
        if not profile:
            raise NotFoundException("Student profile not found")
        return profile
