from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.keys import student_dashboard_key
from app.cache.utils import get_json, set_json
from app.repositories.assessment_repo import AssessmentRepository
from app.repositories.attendance_repo import AttendanceRepository
from app.repositories.homework_repo import HomeworkRepository
from app.repositories.notification_repo import NotificationRepository


class DashboardService:
    def __init__(self, session: AsyncSession, cache: Redis) -> None:
        self.assessment_repo = AssessmentRepository(session)
        self.attendance_repo = AttendanceRepository(session)
        self.homework_repo = HomeworkRepository(session)
        self.notification_repo = NotificationRepository(session)
        self.cache = cache

    async def get_student_dashboard(self, *, user_id: str, student_id: str, batch_id: str | None) -> dict:
        key = student_dashboard_key(student_id)
        cached = await get_json(self.cache, key)
        if cached:
            return cached

        unread = await self.notification_repo.unread_count(user_id=user_id)
        pending_homework = await self.homework_repo.pending_count_for_student(
            student_id=student_id,
            batch_id=batch_id,
        )
        attendance = await self.attendance_repo.summary_for_student(student_id=student_id, date_from=None, date_to=None)
        upcoming_tests = await self.assessment_repo.upcoming_count_for_student(
            student_id=student_id,
            batch_id=batch_id,
        )

        payload = {
            "unread_notifications": unread,
            "pending_homework_count": pending_homework,
            "attendance_percentage": attendance["attendance_percentage"],
            "upcoming_tests_count": upcoming_tests,
        }

        await set_json(self.cache, key, payload, ttl_seconds=60)
        return payload
