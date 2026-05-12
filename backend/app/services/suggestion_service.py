from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.timezone import ensure_utc, to_app_timezone
from app.db.models.academic import StudentProfile
from app.db.models.user import User
from app.repositories.suggestion_repo import SuggestionRepository


class SuggestionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SuggestionRepository(session)

    @staticmethod
    def _serialize_message(row, sender_name: str) -> dict:
        return {
            "id": row.id,
            "thread_id": row.thread_id,
            "sender_user_id": row.sender_user_id,
            "sender_name": sender_name,
            "message": row.message,
            "created_at": to_app_timezone(row.created_at),
        }

    @staticmethod
    def _serialize_thread(*, thread, student_profile, student_user, unread_for_admin: bool) -> dict:
        return {
            "id": thread.id,
            "student_id": thread.student_id,
            "student_user_id": thread.student_user_id,
            "student_name": student_user.full_name,
            "student_phone": student_user.phone,
            "admission_no": student_profile.admission_no,
            "class_name": student_profile.class_name,
            "stream": student_profile.stream,
            "status": thread.status,
            "last_message_at": to_app_timezone(thread.last_message_at),
            "updated_at": to_app_timezone(thread.updated_at),
            "unread_for_admin": unread_for_admin,
        }

    async def _ensure_student_thread(self, *, student_profile: StudentProfile) -> tuple:
        thread = await self.repo.get_thread_for_student(student_id=student_profile.id)
        if thread is None:
            thread = await self.repo.create_thread(
                student_id=student_profile.id,
                student_user_id=student_profile.user_id,
            )
            await self.session.commit()
            await self.session.refresh(thread)

        student_user = (
            await self.session.execute(select(User).where(User.id == student_profile.user_id))
        ).scalar_one_or_none()
        if student_user is None:
            raise NotFoundException("Student user not found")

        return thread, student_user

    async def student_get_messages(
        self,
        *,
        student_profile: StudentProfile,
        limit: int,
        offset: int,
    ) -> dict:
        thread, student_user = await self._ensure_student_thread(student_profile=student_profile)

        rows, total = await self.repo.list_messages(
            thread_id=thread.id,
            limit=limit,
            offset=offset,
        )

        sender_ids = sorted({row.sender_user_id for row in rows})
        sender_map: dict[str, str] = {}
        if sender_ids:
            sender_rows = (
                await self.session.execute(select(User.id, User.full_name).where(User.id.in_(sender_ids)))
            ).all()
            sender_map = {user_id: full_name for user_id, full_name in sender_rows}

        now = datetime.now(UTC)
        thread.student_last_read_at = now
        await self.session.commit()

        messages = [
            self._serialize_message(
                row,
                sender_name=sender_map.get(row.sender_user_id, "Unknown"),
            )
            for row in rows
        ]

        return {
            "thread": {
                "id": thread.id,
                "student_id": thread.student_id,
                "student_name": student_user.full_name,
                "status": thread.status,
                "last_message_at": to_app_timezone(thread.last_message_at),
            },
            "items": messages,
            "total": total,
        }

    async def student_send_message(
        self,
        *,
        student_profile: StudentProfile,
        message: str,
    ) -> dict:
        cleaned = message.strip()
        if not cleaned:
            raise ValueError("Message is required")

        thread, _student_user = await self._ensure_student_thread(student_profile=student_profile)

        row = await self.repo.add_message(
            thread_id=thread.id,
            sender_user_id=student_profile.user_id,
            message=cleaned,
        )

        now = datetime.now(UTC)
        thread.last_message_at = now
        thread.last_sender_user_id = student_profile.user_id
        thread.status = "open"

        await self.session.commit()
        await self.session.refresh(row)

        return self._serialize_message(row, sender_name="You")

    async def admin_unread_count(self) -> dict:
        unread = await self.repo.admin_unread_threads_count()
        return {"unread_count": unread}

    async def admin_list_threads(
        self,
        *,
        search: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        rows, total = await self.repo.list_admin_threads(
            search=search,
            limit=limit,
            offset=offset,
        )

        items = [
            self._serialize_thread(
                thread=thread,
                student_profile=student_profile,
                student_user=student_user,
                unread_for_admin=bool(unread_for_admin),
            )
            for thread, student_profile, student_user, unread_for_admin in rows
        ]
        return items, total

    async def admin_get_thread_messages(
        self,
        *,
        thread_id: str,
        limit: int,
        offset: int,
    ) -> dict:
        thread = await self.repo.get_thread_by_id(thread_id=thread_id)
        if thread is None:
            raise NotFoundException("Suggestion thread not found")

        student_profile = (
            await self.session.execute(
                select(StudentProfile).where(StudentProfile.id == thread.student_id)
            )
        ).scalar_one_or_none()
        if student_profile is None:
            raise NotFoundException("Student profile not found")

        student_user = (
            await self.session.execute(select(User).where(User.id == thread.student_user_id))
        ).scalar_one_or_none()
        if student_user is None:
            raise NotFoundException("Student user not found")

        rows, total = await self.repo.list_messages(
            thread_id=thread.id,
            limit=limit,
            offset=offset,
        )

        sender_ids = sorted({row.sender_user_id for row in rows})
        sender_map: dict[str, str] = {}
        if sender_ids:
            sender_rows = (
                await self.session.execute(select(User.id, User.full_name).where(User.id.in_(sender_ids)))
            ).all()
            sender_map = {user_id: full_name for user_id, full_name in sender_rows}

        now = datetime.now(UTC)
        thread.admin_last_read_at = now
        await self.session.commit()

        messages = [
            self._serialize_message(
                row,
                sender_name=sender_map.get(row.sender_user_id, "Unknown"),
            )
            for row in rows
        ]

        last_message_at = ensure_utc(thread.last_message_at)
        admin_last_read_at = ensure_utc(thread.admin_last_read_at)

        unread_for_admin = (
            thread.last_sender_user_id == thread.student_user_id
            and (admin_last_read_at is None or (last_message_at is not None and admin_last_read_at < last_message_at))
            if last_message_at is not None
            else False
        )

        return {
            "thread": self._serialize_thread(
                thread=thread,
                student_profile=student_profile,
                student_user=student_user,
                unread_for_admin=bool(unread_for_admin),
            ),
            "items": messages,
            "total": total,
        }

    async def admin_send_message(
        self,
        *,
        thread_id: str,
        admin_user_id: str,
        message: str,
    ) -> dict:
        cleaned = message.strip()
        if not cleaned:
            raise ValueError("Message is required")

        thread = await self.repo.get_thread_by_id(thread_id=thread_id)
        if thread is None:
            raise NotFoundException("Suggestion thread not found")

        row = await self.repo.add_message(
            thread_id=thread.id,
            sender_user_id=admin_user_id,
            message=cleaned,
        )

        now = datetime.now(UTC)
        thread.last_message_at = now
        thread.last_sender_user_id = admin_user_id
        thread.admin_last_read_at = now

        await self.session.commit()
        await self.session.refresh(row)

        admin_user = (
            await self.session.execute(select(User).where(User.id == admin_user_id))
        ).scalar_one_or_none()
        admin_name = admin_user.full_name if admin_user else "Admin"

        return self._serialize_message(row, sender_name=admin_name)

    async def validate_admin_owns_thread(self, *, thread_id: str) -> None:
        thread = await self.repo.get_thread_by_id(thread_id=thread_id)
        if thread is None:
            raise NotFoundException("Suggestion thread not found")

    async def ensure_student_thread_access(self, *, thread_id: str, student_profile: StudentProfile) -> None:
        thread = await self.repo.get_thread_by_id(thread_id=thread_id)
        if thread is None:
            raise NotFoundException("Suggestion thread not found")
        if thread.student_id != student_profile.id:
            raise ForbiddenException("You are not allowed to access this suggestion thread")
