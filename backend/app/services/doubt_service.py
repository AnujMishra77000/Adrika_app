import re
from datetime import datetime

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.keys import student_dashboard_key, student_unread_notifications_key, teacher_dashboard_key
from app.cache.utils import delete_keys
from app.core.exceptions import NotFoundException
from app.db.models.enums import NotificationType
from app.db.models.notification import Notification
from app.db.models.user import User
from app.repositories.doubt_repo import DoubtRepository


class DoubtService:
    def __init__(self, session: AsyncSession, cache: Redis | None = None) -> None:
        self.session = session
        self.repo = DoubtRepository(session)
        self.cache = cache

    @staticmethod
    def _extract_class_level(class_name: str | None) -> int | None:
        text = (class_name or "").strip()
        matched = re.search(r"\b(10|11|12)\b", text)
        if matched:
            return int(matched.group(1))

        if "10" in text:
            return 10
        if "11" in text:
            return 11
        if "12" in text:
            return 12
        return None

    @staticmethod
    def _normalize_stream(stream: str | None, class_level: int | None) -> str:
        value = (stream or "").strip().lower()
        if class_level == 10:
            return "common"
        if value in {"science", "sci"}:
            return "science"
        if value in {"commerce", "comm"}:
            return "commerce"
        # defaults to common only for unknown data paths
        return "common" if class_level == 10 else "science"

    async def _sender_name_map(self, *, messages) -> dict[str, str]:
        sender_ids = [message.sender_user_id for message in messages if message.sender_user_id]
        if not sender_ids:
            return {}

        rows = (
            await self.session.execute(
                select(User.id, User.full_name).where(User.id.in_(sender_ids))
            )
        ).all()
        return {user_id: full_name for user_id, full_name in rows}

    async def _invalidate_user_counters(
        self,
        *,
        recipient_user_id: str | None,
        student_id: str | None = None,
        teacher_id: str | None = None,
    ) -> None:
        if not self.cache:
            return

        keys: list[str] = []
        if recipient_user_id:
            keys.append(student_unread_notifications_key(recipient_user_id))
        if student_id:
            keys.append(student_dashboard_key(student_id))
        if teacher_id:
            keys.append(teacher_dashboard_key(teacher_id))

        if keys:
            await delete_keys(self.cache, keys)

    async def _notify_doubt_event(
        self,
        *,
        recipient_user_id: str | None,
        doubt_id: str,
        lecture_id: str | None,
        title: str,
        body: str,
        student_id: str | None = None,
        teacher_id: str | None = None,
    ) -> None:
        if not recipient_user_id:
            return

        self.session.add(
            Notification(
                recipient_user_id=recipient_user_id,
                notification_type=NotificationType.DOUBT,
                title=title,
                body=body,
                metadata_json={
                    "source": "doubt",
                    "doubt_id": doubt_id,
                    "lecture_id": lecture_id,
                },
                is_read=False,
            )
        )
        await self._invalidate_user_counters(
            recipient_user_id=recipient_user_id,
            student_id=student_id,
            teacher_id=teacher_id,
        )

    async def list_done_lectures_for_student(
        self,
        *,
        student_id: str,
        batch_id: str | None,
        class_name: str | None,
        stream: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        class_level = self._extract_class_level(class_name)
        if class_level is None and batch_id is None:
            return [], 0
        normalized_stream = self._normalize_stream(stream, class_level)

        rows, total = await self.repo.list_done_lectures_for_student(
            student_id=student_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=normalized_stream,
            limit=limit,
            offset=offset,
        )

        items = [
            {
                "lecture_id": lecture.id,
                "topic": lecture.topic,
                "summary": lecture.summary,
                "completed_at": lecture.completed_at,
                "subject_id": subject.id,
                "subject_name": subject.name,
                "teacher_id": teacher.id,
                "teacher_name": teacher_user.full_name,
                "class_level": lecture.class_level,
                "stream": lecture.stream,
            }
            for lecture, subject, teacher, teacher_user in rows
        ]

        return items, total

    async def lecture_detail_for_student(
        self,
        *,
        student_id: str,
        lecture_id: str,
        batch_id: str | None,
        class_name: str | None,
        stream: str | None,
    ) -> dict:
        class_level = self._extract_class_level(class_name)
        if class_level is None and batch_id is None:
            raise NotFoundException("Lecture not found")
        normalized_stream = self._normalize_stream(stream, class_level)

        row = await self.repo.get_done_lecture_for_student(
            student_id=student_id,
            lecture_id=lecture_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=normalized_stream,
        )
        if not row:
            raise NotFoundException("Lecture not found")

        lecture, subject, teacher, teacher_user = row
        return {
            "lecture_id": lecture.id,
            "topic": lecture.topic,
            "summary": lecture.summary,
            "completed_at": lecture.completed_at,
            "subject_id": subject.id,
            "subject_name": subject.name,
            "teacher_id": teacher.id,
            "teacher_name": teacher_user.full_name,
            "class_level": lecture.class_level,
            "stream": lecture.stream,
        }

    async def list_for_student(
        self,
        *,
        student_id: str,
        status: str | None,
        subject_id: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        rows, total = await self.repo.list_for_student(
            student_id=student_id,
            status=status,
            subject_id=subject_id,
            query=query,
            limit=limit,
            offset=offset,
        )
        return [
            {
                "id": row.id,
                "lecture_id": row.lecture_id,
                "teacher_id": row.teacher_id,
                "subject_id": row.subject_id,
                "topic": row.topic,
                "status": row.status.value if hasattr(row.status, "value") else str(row.status),
                "priority": row.priority,
                "created_at": row.created_at,
            }
            for row in rows
        ], total

    async def create(
        self,
        *,
        student_id: str,
        subject_id: str | None,
        lecture_id: str | None,
        teacher_id: str | None,
        topic: str,
        description: str,
    ) -> dict:
        resolved_subject_id = subject_id
        resolved_teacher_id = teacher_id

        if lecture_id:
            lecture = await self.repo.get_lecture_by_id(lecture_id=lecture_id)
            if not lecture:
                raise NotFoundException("Lecture not found")
            resolved_subject_id = lecture.subject_id
            resolved_teacher_id = lecture.teacher_id

        if not resolved_subject_id:
            raise ValueError("subject_id is required")

        doubt = await self.repo.create_doubt(
            student_id=student_id,
            subject_id=resolved_subject_id,
            topic=topic,
            description=description,
            lecture_id=lecture_id,
            teacher_id=resolved_teacher_id,
        )

        teacher_user_id = None
        if resolved_teacher_id:
            teacher_user_id = await self.repo.get_teacher_user_id(teacher_id=resolved_teacher_id)
            await self._notify_doubt_event(
                recipient_user_id=teacher_user_id,
                doubt_id=doubt.id,
                lecture_id=doubt.lecture_id,
                title="New doubt raised",
                body=f"A student raised a doubt on '{doubt.topic}'.",
                teacher_id=resolved_teacher_id,
            )

        await self.session.commit()

        return {
            "id": doubt.id,
            "lecture_id": doubt.lecture_id,
            "teacher_id": doubt.teacher_id,
            "subject_id": doubt.subject_id,
            "topic": doubt.topic,
            "status": doubt.status.value if hasattr(doubt.status, "value") else str(doubt.status),
            "priority": doubt.priority,
            "created_at": doubt.created_at,
            "teacher_notified": bool(teacher_user_id),
        }

    async def create_from_lecture(
        self,
        *,
        student_id: str,
        batch_id: str | None,
        class_name: str | None,
        stream: str | None,
        lecture_id: str,
        topic: str,
        description: str,
    ) -> dict:
        class_level = self._extract_class_level(class_name)
        if class_level is None and batch_id is None:
            raise NotFoundException("Lecture not found")
        normalized_stream = self._normalize_stream(stream, class_level)

        row = await self.repo.get_done_lecture_for_student(
            student_id=student_id,
            lecture_id=lecture_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=normalized_stream,
        )
        if not row:
            raise NotFoundException("Lecture not found")

        lecture, _subject, _teacher, teacher_user = row
        doubt = await self.repo.create_doubt(
            student_id=student_id,
            subject_id=lecture.subject_id,
            topic=topic,
            description=description,
            lecture_id=lecture.id,
            teacher_id=lecture.teacher_id,
        )

        await self._notify_doubt_event(
            recipient_user_id=teacher_user.id,
            doubt_id=doubt.id,
            lecture_id=lecture.id,
            title="New lecture doubt",
            body=f"A student raised a doubt for lecture '{lecture.topic}'.",
            teacher_id=lecture.teacher_id,
        )

        await self.session.commit()

        return {
            "id": doubt.id,
            "lecture_id": lecture.id,
            "teacher_id": lecture.teacher_id,
            "subject_id": lecture.subject_id,
            "topic": doubt.topic,
            "description": doubt.description,
            "status": doubt.status.value if hasattr(doubt.status, "value") else str(doubt.status),
            "priority": doubt.priority,
            "created_at": doubt.created_at,
        }

    async def get_detail(self, *, student_id: str, doubt_id: str) -> dict:
        doubt = await self.repo.get_doubt_for_student(doubt_id=doubt_id, student_id=student_id)
        if not doubt:
            raise NotFoundException("Doubt not found")

        messages = await self.repo.list_messages(doubt_id=doubt.id)
        sender_name_map = await self._sender_name_map(messages=messages)
        return {
            "doubt": {
                "id": doubt.id,
                "lecture_id": doubt.lecture_id,
                "teacher_id": doubt.teacher_id,
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
                    "sender_name": sender_name_map.get(message.sender_user_id or "", "Unknown"),
                    "message": message.message,
                    "created_at": message.created_at,
                }
                for message in messages
            ],
        }

    async def list_messages(self, *, student_id: str, doubt_id: str, since: datetime | None) -> list[dict]:
        doubt = await self.repo.get_doubt_for_student(doubt_id=doubt_id, student_id=student_id)
        if not doubt:
            raise NotFoundException("Doubt not found")

        messages = await self.repo.list_messages(doubt_id=doubt.id, since=since)
        sender_name_map = await self._sender_name_map(messages=messages)
        return [
            {
                "id": message.id,
                "sender_user_id": message.sender_user_id,
                "sender_name": sender_name_map.get(message.sender_user_id or "", "Unknown"),
                "message": message.message,
                "created_at": message.created_at,
            }
            for message in messages
        ]

    async def add_message(self, *, student_id: str, user_id: str, doubt_id: str, message: str) -> dict:
        doubt = await self.repo.get_doubt_for_student(doubt_id=doubt_id, student_id=student_id)
        if not doubt:
            raise NotFoundException("Doubt not found")

        saved = await self.repo.add_message(doubt_id=doubt_id, sender_user_id=user_id, message=message)

        teacher_user_id = None
        if doubt.teacher_id:
            teacher_user_id = await self.repo.get_teacher_user_id(teacher_id=doubt.teacher_id)

        await self._notify_doubt_event(
            recipient_user_id=teacher_user_id,
            doubt_id=doubt.id,
            lecture_id=doubt.lecture_id,
            title="New doubt message",
            body=f"Student replied on doubt '{doubt.topic}'.",
            teacher_id=doubt.teacher_id,
        )

        sender_name = "You"
        sender_row = (await self.session.execute(select(User.full_name).where(User.id == user_id))).first()
        if sender_row and sender_row[0]:
            sender_name = sender_row[0]

        await self.session.commit()
        return {
            "id": saved.id,
            "sender_user_id": saved.sender_user_id,
            "sender_name": sender_name,
            "message": saved.message,
            "created_at": saved.created_at,
        }
