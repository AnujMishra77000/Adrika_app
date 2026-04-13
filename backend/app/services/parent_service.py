from datetime import date

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.keys import parent_dashboard_key, parent_notices_key
from app.cache.utils import delete_keys, get_json, set_json
from app.core.exceptions import ForbiddenException, NotFoundException
from app.repositories.assessment_repo import AssessmentRepository
from app.repositories.attendance_repo import AttendanceRepository
from app.repositories.homework_repo import HomeworkRepository
from app.repositories.notice_repo import NoticeRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.parent_repo import ParentRepository
from app.repositories.result_repo import ResultRepository
from app.repositories.student_repo import StudentRepository


class ParentService:
    def __init__(self, session: AsyncSession, cache: Redis) -> None:
        self.session = session
        self.cache = cache
        self.parent_repo = ParentRepository(session)
        self.student_repo = StudentRepository(session)
        self.notice_repo = NoticeRepository(session)
        self.homework_repo = HomeworkRepository(session)
        self.attendance_repo = AttendanceRepository(session)
        self.assessment_repo = AssessmentRepository(session)
        self.result_repo = ResultRepository(session)
        self.notification_repo = NotificationRepository(session)

    @staticmethod
    def _extract_class_level(class_name: str | None) -> int | None:
        if not class_name:
            return None
        if "10" in class_name:
            return 10
        if "11" in class_name:
            return 11
        if "12" in class_name:
            return 12
        return None

    async def _resolve_student(self, *, parent_id: str, student_id: str | None):
        linked_ids = await self.parent_repo.linked_student_ids(parent_id=parent_id)
        if not linked_ids:
            raise ForbiddenException("No linked students found")

        resolved_id = student_id or linked_ids[0]
        if resolved_id not in linked_ids:
            raise ForbiddenException("Student is not linked to parent")

        profile = await self.student_repo.get_profile_by_id(resolved_id)
        if not profile:
            raise NotFoundException("Student profile not found")
        return profile

    async def profile(self, *, parent_profile) -> dict:
        preferences = await self.parent_repo.get_preferences(parent_id=parent_profile.id)
        linked = await self.parent_repo.linked_student_ids(parent_id=parent_profile.id)

        return {
            "parent_id": parent_profile.id,
            "user_id": parent_profile.user_id,
            "full_name": parent_profile.user.full_name,
            "email": parent_profile.user.email,
            "phone": parent_profile.user.phone,
            "linked_students_count": len(linked),
            "preferences": {
                "in_app_enabled": preferences.in_app_enabled if preferences else True,
                "push_enabled": preferences.push_enabled if preferences else True,
                "whatsapp_enabled": preferences.whatsapp_enabled if preferences else False,
                "fee_reminders_enabled": preferences.fee_reminders_enabled if preferences else True,
                "preferred_language": preferences.preferred_language if preferences else "en",
            },
        }

    async def linked_students(self, *, parent_id: str) -> list[dict]:
        links = await self.parent_repo.list_student_links(parent_id=parent_id)
        students = await self.student_repo.list_profiles_by_ids([link.student_id for link in links])
        by_id = {student.id: student for student in students}

        payload: list[dict] = []
        for link in links:
            student = by_id.get(link.student_id)
            if not student:
                continue
            payload.append(
                {
                    "student_id": student.id,
                    "full_name": student.user.full_name,
                    "admission_no": student.admission_no,
                    "roll_no": student.roll_no,
                    "current_batch_id": student.current_batch_id,
                    "relation_type": link.relation_type,
                    "is_primary": link.is_primary,
                }
            )
        return payload

    async def dashboard(self, *, user_id: str, parent_id: str, student_id: str | None) -> dict:
        student = await self._resolve_student(parent_id=parent_id, student_id=student_id)
        key = parent_dashboard_key(parent_id, student.id)
        cached = await get_json(self.cache, key)
        if cached:
            return cached

        unread = await self.notification_repo.unread_count(user_id=user_id)
        pending_homework = await self.homework_repo.pending_count_for_student(
            student_id=student.id,
            batch_id=student.current_batch_id,
            class_level=self._extract_class_level(student.class_name),
            stream=student.stream,
        )
        attendance = await self.attendance_repo.summary_for_student(student_id=student.id, date_from=None, date_to=None)
        upcoming_tests = await self.assessment_repo.upcoming_count_for_student(
            student_id=student.id,
            batch_id=student.current_batch_id,
        )
        pending_fees = await self.parent_repo.pending_fee_count(student_id=student.id)

        payload = {
            "student_id": student.id,
            "unread_notifications": unread,
            "pending_homework_count": pending_homework,
            "attendance_percentage": attendance["attendance_percentage"],
            "upcoming_tests_count": upcoming_tests,
            "pending_fee_invoices": pending_fees,
        }
        await set_json(self.cache, key, payload, ttl_seconds=60)
        return payload

    async def list_notices(
        self,
        *,
        user_id: str,
        parent_id: str,
        student_id: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        student = await self._resolve_student(parent_id=parent_id, student_id=student_id)
        key = parent_notices_key(parent_id, student.id, limit, offset)
        cached = await get_json(self.cache, key)
        if cached:
            return cached["items"], int(cached["total"])

        rows, total = await self.notice_repo.list_for_student(
            user_id=user_id,
            student_id=student.id,
            batch_id=student.current_batch_id,
            class_level=self._extract_class_level(student.class_name),
            stream=student.stream,
            limit=limit,
            offset=offset,
        )
        items = [
            {
                "id": notice.id,
                "title": notice.title,
                "body_preview": notice.body[:200],
                "priority": notice.priority,
                "publish_at": notice.publish_at,
                "is_read": bool(is_read),
            }
            for notice, is_read in rows
        ]
        await set_json(self.cache, key, {"items": items, "total": total}, ttl_seconds=120)
        return items, total

    async def notice_detail(self, *, notice_id: str, user_id: str, parent_id: str, student_id: str) -> dict:
        student = await self._resolve_student(parent_id=parent_id, student_id=student_id)
        notice, is_read = await self.notice_repo.get_notice_for_student(
            notice_id=notice_id,
            user_id=user_id,
            student_id=student.id,
            batch_id=student.current_batch_id,
            class_level=self._extract_class_level(student.class_name),
            stream=student.stream,
        )
        if not notice:
            raise NotFoundException("Notice not found")

        return {
            "id": notice.id,
            "title": notice.title,
            "body": notice.body,
            "priority": notice.priority,
            "publish_at": notice.publish_at,
            "is_read": is_read,
        }

    async def mark_notice_read(self, *, notice_id: str, user_id: str, parent_id: str, student_id: str) -> None:
        student = await self._resolve_student(parent_id=parent_id, student_id=student_id)
        await self.notice_repo.mark_read(notice_id=notice_id, user_id=user_id)
        await self.session.commit()
        await delete_keys(self.cache, [parent_notices_key(parent_id, student.id, 20, 0)])

    async def list_homework(
        self,
        *,
        parent_id: str,
        student_id: str,
        subject_id: str | None,
        due_from: date | None,
        due_to: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        student = await self._resolve_student(parent_id=parent_id, student_id=student_id)
        rows, total = await self.homework_repo.list_for_student(
            student_id=student.id,
            batch_id=student.current_batch_id,
            class_level=self._extract_class_level(student.class_name),
            stream=student.stream,
            subject_id=subject_id,
            due_from=due_from,
            due_to=due_to,
            limit=limit,
            offset=offset,
        )
        payload = [
            {
                "id": hw.id,
                "title": hw.title,
                "description": hw.description,
                "subject_id": hw.subject_id,
                "due_date": hw.due_date,
                "status": hw.status.value if hasattr(hw.status, "value") else str(hw.status),
            }
            for hw in rows
        ]
        return payload, total

    async def attendance(
        self,
        *,
        parent_id: str,
        student_id: str,
        date_from: date | None,
        date_to: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int, dict]:
        student = await self._resolve_student(parent_id=parent_id, student_id=student_id)
        rows, total = await self.attendance_repo.list_for_student(
            student_id=student.id,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
        summary = await self.attendance_repo.summary_for_student(
            student_id=student.id,
            date_from=date_from,
            date_to=date_to,
        )
        items = [
            {
                "id": row.id,
                "attendance_date": row.attendance_date,
                "session_code": row.session_code,
                "status": row.status.value if hasattr(row.status, "value") else str(row.status),
                "source": row.source,
            }
            for row in rows
        ]
        return items, total, summary

    async def results(
        self,
        *,
        parent_id: str,
        student_id: str,
        subject_id: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        student = await self._resolve_student(parent_id=parent_id, student_id=student_id)
        rows, total = await self.result_repo.list_results(
            student_id=student.id,
            subject_id=subject_id,
            limit=limit,
            offset=offset,
        )
        payload = [
            {
                "id": row.id,
                "assessment_id": row.assessment_id,
                "score": float(row.score),
                "total_marks": float(row.total_marks),
                "rank": row.rank,
                "published_at": row.published_at,
            }
            for row in rows
        ]
        return payload, total

    async def progress(self, *, parent_id: str, student_id: str, period_type: str | None, limit: int) -> list[dict]:
        student = await self._resolve_student(parent_id=parent_id, student_id=student_id)
        rows = await self.result_repo.list_progress(student_id=student.id, period_type=period_type, limit=limit)
        return [
            {
                "period_type": row.period_type,
                "period_start": row.period_start,
                "metrics": row.metrics,
            }
            for row in rows
        ]

    async def list_fee_invoices(
        self,
        *,
        parent_id: str,
        student_id: str,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        student = await self._resolve_student(parent_id=parent_id, student_id=student_id)
        rows, total = await self.parent_repo.list_fee_invoices(
            student_id=student.id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return [
            {
                "id": row.id,
                "invoice_no": row.invoice_no,
                "period_label": row.period_label,
                "due_date": row.due_date,
                "amount": float(row.amount),
                "status": row.status,
                "paid_at": row.paid_at,
            }
            for row in rows
        ], total

    async def list_payments(
        self,
        *,
        parent_id: str,
        student_id: str,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        student = await self._resolve_student(parent_id=parent_id, student_id=student_id)
        rows, total = await self.parent_repo.list_payment_transactions(
            student_id=student.id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return [
            {
                "id": row.id,
                "invoice_id": row.invoice_id,
                "provider": row.provider,
                "external_ref": row.external_ref,
                "amount": float(row.amount),
                "status": row.status,
                "paid_at": row.paid_at,
            }
            for row in rows
        ], total

    async def get_preferences(self, *, parent_id: str) -> dict:
        pref = await self.parent_repo.get_preferences(parent_id=parent_id)
        if not pref:
            return {
                "in_app_enabled": True,
                "push_enabled": True,
                "whatsapp_enabled": False,
                "fee_reminders_enabled": True,
                "preferred_language": "en",
            }

        return {
            "in_app_enabled": pref.in_app_enabled,
            "push_enabled": pref.push_enabled,
            "whatsapp_enabled": pref.whatsapp_enabled,
            "fee_reminders_enabled": pref.fee_reminders_enabled,
            "preferred_language": pref.preferred_language,
        }

    async def update_preferences(
        self,
        *,
        parent_id: str,
        in_app_enabled: bool,
        push_enabled: bool,
        whatsapp_enabled: bool,
        fee_reminders_enabled: bool,
        preferred_language: str,
    ) -> dict:
        pref = await self.parent_repo.upsert_preferences(
            parent_id=parent_id,
            in_app_enabled=in_app_enabled,
            push_enabled=push_enabled,
            whatsapp_enabled=whatsapp_enabled,
            fee_reminders_enabled=fee_reminders_enabled,
            preferred_language=preferred_language,
        )
        await self.session.commit()
        await self.session.refresh(pref)

        return {
            "in_app_enabled": pref.in_app_enabled,
            "push_enabled": pref.push_enabled,
            "whatsapp_enabled": pref.whatsapp_enabled,
            "fee_reminders_enabled": pref.fee_reminders_enabled,
            "preferred_language": pref.preferred_language,
            "updated_at": pref.updated_at,
        }
