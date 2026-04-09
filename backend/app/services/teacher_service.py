from datetime import date

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.keys import teacher_dashboard_key, teacher_notices_key
from app.cache.utils import delete_keys, get_json, set_json
from app.core.exceptions import NotFoundException
from app.repositories.notification_repo import NotificationRepository
from app.repositories.teacher_repo import TeacherRepository


class TeacherService:
    def __init__(self, session: AsyncSession, cache: Redis) -> None:
        self.session = session
        self.repo = TeacherRepository(session)
        self.notification_repo = NotificationRepository(session)
        self.cache = cache

    async def profile(self, *, teacher_profile) -> dict:
        return {
            "teacher_id": teacher_profile.id,
            "user_id": teacher_profile.user_id,
            "full_name": teacher_profile.user.full_name,
            "employee_code": teacher_profile.employee_code,
            "designation": teacher_profile.designation,
            "age": teacher_profile.age,
            "gender": teacher_profile.gender,
            "qualification": teacher_profile.qualification,
            "specialization": teacher_profile.specialization,
            "school_college": teacher_profile.school_college,
            "address": teacher_profile.address,
            "photo_url": teacher_profile.photo_url,
        }

    async def list_assignments(self, *, teacher_id: str) -> list[dict]:
        rows = await self.repo.list_assignments(teacher_id=teacher_id)
        return [
            {
                "assignment_id": assignment.id,
                "batch_id": batch.id,
                "batch_name": batch.name,
                "standard_id": standard.id,
                "standard_name": standard.name,
                "subject_id": subject.id,
                "subject_name": subject.name,
            }
            for assignment, batch, standard, subject in rows
        ]

    async def dashboard(self, *, user_id: str, teacher_id: str) -> dict:
        key = teacher_dashboard_key(teacher_id)
        cached = await get_json(self.cache, key)
        if cached:
            return cached

        batch_ids = await self.repo.assigned_batch_ids(teacher_id=teacher_id)
        subject_ids = await self.repo.assigned_subject_ids(teacher_id=teacher_id)

        unread = await self.notification_repo.unread_count(user_id=user_id)
        open_doubts = await self.repo.open_doubts_count_for_teacher(subject_ids=subject_ids)
        pending_homework = await self.repo.pending_homework_count_for_teacher(
            batch_ids=batch_ids,
            subject_ids=subject_ids,
        )
        upcoming_tests = await self.repo.upcoming_assessments_count_for_teacher(
            batch_ids=batch_ids,
            subject_ids=subject_ids,
        )

        payload = {
            "assigned_batches_count": len(batch_ids),
            "assigned_subjects_count": len(subject_ids),
            "unread_notifications": unread,
            "open_doubts_count": open_doubts,
            "pending_homework_count": pending_homework,
            "upcoming_tests_count": upcoming_tests,
        }
        await set_json(self.cache, key, payload, ttl_seconds=60)
        return payload

    async def list_notices(
        self,
        *,
        user_id: str,
        teacher_id: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        key = teacher_notices_key(teacher_id, limit, offset)
        cached = await get_json(self.cache, key)
        if cached:
            return cached["items"], int(cached["total"])

        batch_ids = await self.repo.assigned_batch_ids(teacher_id=teacher_id)
        rows, total = await self.repo.list_notices_for_teacher(
            user_id=user_id,
            teacher_id=teacher_id,
            batch_ids=batch_ids,
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

    async def notice_detail(self, *, notice_id: str, user_id: str, teacher_id: str) -> dict:
        batch_ids = await self.repo.assigned_batch_ids(teacher_id=teacher_id)
        notice, is_read = await self.repo.get_notice_for_teacher(
            notice_id=notice_id,
            user_id=user_id,
            teacher_id=teacher_id,
            batch_ids=batch_ids,
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

    async def mark_notice_read(self, *, notice_id: str, user_id: str, teacher_id: str) -> None:
        await self.repo.mark_notice_read(notice_id=notice_id, user_id=user_id)
        await self.session.commit()
        await delete_keys(self.cache, [teacher_notices_key(teacher_id, 20, 0)])

    async def list_homework(
        self,
        *,
        teacher_id: str,
        subject_id: str | None,
        due_from: date | None,
        due_to: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        batch_ids = await self.repo.assigned_batch_ids(teacher_id=teacher_id)
        subject_ids = await self.repo.assigned_subject_ids(teacher_id=teacher_id)
        rows, total = await self.repo.list_homework_for_teacher(
            batch_ids=batch_ids,
            subject_ids=subject_ids,
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

    async def list_assessments(
        self,
        *,
        teacher_id: str,
        assessment_type: str | None,
        status: str | None,
        subject_id: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        batch_ids = await self.repo.assigned_batch_ids(teacher_id=teacher_id)
        subject_ids = await self.repo.assigned_subject_ids(teacher_id=teacher_id)
        rows, total = await self.repo.list_assessments_for_teacher(
            batch_ids=batch_ids,
            subject_ids=subject_ids,
            assessment_type=assessment_type,
            status=status,
            subject_id=subject_id,
            limit=limit,
            offset=offset,
        )
        payload = [
            {
                "id": row.id,
                "title": row.title,
                "subject_id": row.subject_id,
                "assessment_type": row.assessment_type.value if hasattr(row.assessment_type, "value") else str(row.assessment_type),
                "status": row.status.value if hasattr(row.status, "value") else str(row.status),
                "starts_at": row.starts_at,
                "ends_at": row.ends_at,
                "duration_sec": row.duration_sec,
            }
            for row in rows
        ]
        return payload, total

    async def list_doubts(
        self,
        *,
        teacher_id: str,
        status: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        subject_ids = await self.repo.assigned_subject_ids(teacher_id=teacher_id)
        rows, total = await self.repo.list_doubts_for_teacher(
            subject_ids=subject_ids,
            status=status,
            query=query,
            limit=limit,
            offset=offset,
        )
        return [
            {
                "id": row.id,
                "student_id": row.student_id,
                "subject_id": row.subject_id,
                "topic": row.topic,
                "status": row.status.value if hasattr(row.status, "value") else str(row.status),
                "priority": row.priority,
                "created_at": row.created_at,
            }
            for row in rows
        ], total

    async def doubt_detail(self, *, teacher_id: str, doubt_id: str) -> dict:
        subject_ids = await self.repo.assigned_subject_ids(teacher_id=teacher_id)
        doubt = await self.repo.get_doubt_for_teacher(doubt_id=doubt_id, subject_ids=subject_ids)
        if not doubt:
            raise NotFoundException("Doubt not found")

        messages = await self.repo.list_doubt_messages(doubt_id=doubt.id)
        return {
            "doubt": {
                "id": doubt.id,
                "student_id": doubt.student_id,
                "subject_id": doubt.subject_id,
                "topic": doubt.topic,
                "description": doubt.description,
                "status": doubt.status.value if hasattr(doubt.status, "value") else str(doubt.status),
                "priority": doubt.priority,
                "created_at": doubt.created_at,
            },
            "messages": [
                {
                    "id": message.id,
                    "sender_user_id": message.sender_user_id,
                    "message": message.message,
                    "created_at": message.created_at,
                }
                for message in messages
            ],
        }

    async def add_doubt_message(
        self,
        *,
        teacher_id: str,
        user_id: str,
        doubt_id: str,
        message: str,
    ) -> dict:
        subject_ids = await self.repo.assigned_subject_ids(teacher_id=teacher_id)
        doubt = await self.repo.get_doubt_for_teacher(doubt_id=doubt_id, subject_ids=subject_ids)
        if not doubt:
            raise NotFoundException("Doubt not found")

        saved = await self.repo.add_doubt_message(
            doubt_id=doubt_id,
            sender_user_id=user_id,
            message=message,
        )
        await self.session.commit()
        await self.session.refresh(saved)
        await delete_keys(self.cache, [teacher_dashboard_key(teacher_id)])
        return {
            "id": saved.id,
            "sender_user_id": saved.sender_user_id,
            "message": saved.message,
            "created_at": saved.created_at,
        }

    async def update_doubt_status(self, *, teacher_id: str, doubt_id: str, status: str) -> dict:
        subject_ids = await self.repo.assigned_subject_ids(teacher_id=teacher_id)
        doubt = await self.repo.get_doubt_for_teacher(doubt_id=doubt_id, subject_ids=subject_ids)
        if not doubt:
            raise NotFoundException("Doubt not found")

        updated = await self.repo.update_doubt_status(doubt=doubt, status=status)
        await self.session.commit()
        await self.session.refresh(updated)
        await delete_keys(self.cache, [teacher_dashboard_key(teacher_id)])

        return {
            "id": updated.id,
            "status": updated.status.value if hasattr(updated.status, "value") else str(updated.status),
            "updated_at": updated.updated_at,
        }
