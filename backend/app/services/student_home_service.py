from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.keys import student_home_summary_key
from app.cache.utils import get_json, set_json
from app.core.timezone import to_app_timezone
from app.repositories.attendance_repo import AttendanceRepository
from app.services.assessment_service import AssessmentService
from app.services.content_service import ContentService
from app.services.homework_service import HomeworkService
from app.services.lecture_schedule_service import LectureScheduleService
from app.services.notice_service import NoticeService
from app.services.notification_service import NotificationService


class StudentHomeService:
    def __init__(self, session: AsyncSession, cache: Redis) -> None:
        self.session = session
        self.cache = cache
        self.attendance_repo = AttendanceRepository(session)

    @staticmethod
    def _extract_class_level(class_name: str | None) -> int | None:
        text = (class_name or "").strip()
        match = re.search(r"(6|7|8|9|10|11|12)", text)
        if not match:
            return None
        return int(match.group(1))

    @staticmethod
    def _normalize_stream(stream: str | None, class_level: int | None) -> str:
        value = (stream or "").strip().lower()
        if class_level is not None and class_level <= 10:
            return "common"
        if value in {"science", "sci"}:
            return "science"
        if value in {"commerce", "comm"}:
            return "commerce"
        return "science"

    @staticmethod
    def _local_now() -> datetime:
        local = to_app_timezone(datetime.now(UTC))
        return local or datetime.now(UTC)

    @staticmethod
    def _to_local(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return to_app_timezone(value)

    @staticmethod
    def _is_practice_type(raw: str) -> bool:
        value = (raw or "").strip().lower()
        return value in {"daily_practice", "subject_practice", "practice_test"}

    @staticmethod
    def _is_online_type(raw: str) -> bool:
        value = (raw or "").strip().lower()
        return value in {"scheduled", "online_test", "online"}

    @staticmethod
    def _is_pending_assessment(item: dict) -> bool:
        availability = str(item.get("availability") or "").strip().lower()
        return availability in {"scheduled", "live"}

    @staticmethod
    def _same_day(a: datetime, b: datetime) -> bool:
        return a.year == b.year and a.month == b.month and a.day == b.day

    async def get_summary(
        self,
        *,
        user_id: str,
        student_profile,
    ) -> dict:
        cache_key = student_home_summary_key(student_profile.id)
        cached = await get_json(self.cache, cache_key)
        if cached:
            return cached

        now_local = self._local_now()
        class_level = self._extract_class_level(student_profile.class_name)
        stream = self._normalize_stream(student_profile.stream, class_level)

        notices, _ = await NoticeService(self.session, self.cache).list_for_student(
            user_id=user_id,
            student_id=student_profile.id,
            batch_id=student_profile.current_batch_id,
            class_name=student_profile.class_name,
            stream=student_profile.stream,
            limit=20,
            offset=0,
        )

        homework, _ = await HomeworkService(self.session, self.cache).list_for_student(
            user_id=user_id,
            student_id=student_profile.id,
            batch_id=student_profile.current_batch_id,
            class_name=student_profile.class_name,
            stream=student_profile.stream,
            subject_id=None,
            due_from=None,
            due_to=None,
            limit=30,
            offset=0,
        )

        scheduled_lectures, _ = await LectureScheduleService(self.session).list_for_student(
            student_profile=student_profile,
            status="scheduled",
            limit=200,
            offset=0,
        )

        assessments, _ = await AssessmentService(self.session).list_for_student(
            student_id=student_profile.id,
            batch_id=student_profile.current_batch_id,
            class_name=student_profile.class_name,
            stream=student_profile.stream,
            assessment_type=None,
            status=None,
            subject_id=None,
            limit=200,
            offset=0,
        )

        notifications, _ = await NotificationService(self.session, self.cache).list_for_user(
            user_id=user_id,
            is_read=None,
            since_hours=24,
            limit=100,
            offset=0,
        )
        unread_count = await NotificationService(self.session, self.cache).unread_count(
            user_id=user_id,
        )

        attendance = await self.attendance_repo.summary_for_student(
            student_id=student_profile.id,
            date_from=None,
            date_to=None,
        )

        content = await ContentService(self.session, self.cache).get_student_content()

        normalized_lectures: list[dict] = []
        for item in scheduled_lectures:
            when = self._to_local(item.get("scheduled_at"))
            done_at = self._to_local(item.get("completed_at"))
            normalized_lectures.append(
                {
                    **item,
                    "scheduled_at": when,
                    "completed_at": done_at,
                }
            )

        normalized_assessments: list[dict] = []
        for item in assessments:
            starts_at = self._to_local(item.get("starts_at"))
            ends_at = self._to_local(item.get("ends_at"))
            normalized_assessments.append(
                {
                    **item,
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                }
            )

        today_lectures = [
            item
            for item in normalized_lectures
            if isinstance(item.get("scheduled_at"), datetime)
            and self._same_day(item["scheduled_at"], now_local)
        ]
        today_lectures.sort(key=lambda row: row.get("scheduled_at") or now_local)

        week_end = now_local + timedelta(days=7)
        weekly_events: list[dict] = []
        for lecture in normalized_lectures:
            when = lecture.get("scheduled_at")
            if isinstance(when, datetime) and now_local <= when <= week_end:
                weekly_events.append(
                    {
                        "kind": "lecture",
                        "id": lecture.get("id"),
                        "title": lecture.get("topic"),
                        "subtitle": f"{lecture.get('subject_name') or 'Lecture'} • {lecture.get('teacher_name') or ''}".strip(" •"),
                        "scheduled_at": when,
                        "route": "/student/lectures/upcoming",
                    }
                )

        for test in normalized_assessments:
            starts_at = test.get("starts_at")
            if isinstance(starts_at, datetime) and now_local <= starts_at <= week_end:
                weekly_events.append(
                    {
                        "kind": "test",
                        "id": test.get("id"),
                        "title": test.get("title"),
                        "subtitle": test.get("subject_name") or "Assessment",
                        "scheduled_at": starts_at,
                        "route": "/student/online-tests"
                        if self._is_online_type(str(test.get("assessment_type") or ""))
                        else "/student/practice-tests",
                    }
                )

        weekly_events.sort(key=lambda row: row.get("scheduled_at") or now_local)

        pending_online_tests = [
            item
            for item in normalized_assessments
            if self._is_online_type(str(item.get("assessment_type") or ""))
            and self._is_pending_assessment(item)
        ]

        pending_practice_tests = [
            item
            for item in normalized_assessments
            if self._is_practice_type(str(item.get("assessment_type") or ""))
            and self._is_pending_assessment(item)
        ]

        completed_tests = [
            item
            for item in normalized_assessments
            if bool(item.get("has_submitted")) and (item.get("total_marks") or 0) > 0
        ]

        test_percentages: list[float] = []
        for test in completed_tests:
            score = float(test.get("score") or 0)
            total_marks = float(test.get("total_marks") or 0)
            if total_marks > 0:
                test_percentages.append((score / total_marks) * 100)

        average_test_percent = (
            (sum(test_percentages) / len(test_percentages)) if test_percentages else 0.0
        )

        attendance_percent = float(attendance.get("attendance_percentage") or 0)
        blended_progress = (attendance_percent * 0.45) + (average_test_percent * 0.55)

        notice_unread_count = sum(1 for item in notices if not bool(item.get("is_read")))
        homework_pending_count = sum(
            1 for item in homework if not bool(item.get("is_submitted"))
        )

        payload = {
            "server": {
                "timezone": "Asia/Kolkata",
                "generated_at": now_local,
                "server_minute_of_day": (now_local.hour * 60) + now_local.minute,
            },
            "student": {
                "student_id": student_profile.id,
                "user_id": student_profile.user_id,
                "full_name": student_profile.user.full_name,
                "class_name": student_profile.class_name,
                "class_level": class_level,
                "stream": stream,
                "batch_id": student_profile.current_batch_id,
            },
            "counts": {
                "unread_notifications": unread_count,
                "unread_notices": notice_unread_count,
                "pending_homework": homework_pending_count,
                "pending_online_tests": len(pending_online_tests),
                "pending_practice_tests": len(pending_practice_tests),
                "today_lectures": len(today_lectures),
            },
            "progress": {
                "attendance_percent": round(attendance_percent, 2),
                "average_test_percent": round(average_test_percent, 2),
                "blended_progress_percent": round(blended_progress, 2),
                "completed_tests_count": len(completed_tests),
            },
            "today_lectures": today_lectures,
            "weekly_schedule": weekly_events,
            "notices": notices,
            "homework": homework,
            "assessments": normalized_assessments,
            "notifications": notifications,
            "content": content,
        }

        await set_json(self.cache, cache_key, payload, ttl_seconds=45)
        return payload
