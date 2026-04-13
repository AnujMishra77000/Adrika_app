from datetime import UTC, date, datetime, time
from pathlib import Path
import re
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.keys import student_dashboard_key, student_homework_key, student_unread_notifications_key
from app.cache.utils import delete_keys, get_json, set_json
from app.core.config import get_settings
from app.core.exceptions import NotFoundException
from app.db.models.enums import HomeworkSubmissionStatus, NotificationType
from app.repositories.homework_repo import HomeworkRepository
from app.repositories.notification_repo import NotificationRepository


class HomeworkService:
    _ALLOWED_DOC_TYPES: dict[str, str] = {
        "application/pdf": ".pdf",
    }

    def __init__(self, session: AsyncSession, cache: Redis) -> None:
        self.repo = HomeworkRepository(session)
        self.notification_repo = NotificationRepository(session)
        self.session = session
        self.cache = cache

    @staticmethod
    def _extract_class_level(class_name: str | None) -> str | None:
        text = (class_name or "").strip()
        if "10" in text:
            return "10"
        if "11" in text:
            return "11"
        if "12" in text:
            return "12"
        return None

    @staticmethod
    def _normalize_stream(stream: str | None) -> str | None:
        value = (stream or "").strip().lower()
        if value in {"science", "sci"}:
            return "science"
        if value in {"commerce", "comm"}:
            return "commerce"
        return None

    @staticmethod
    def _serialize_attachment(attachment) -> dict:
        return {
            "id": attachment.id,
            "attachment_type": attachment.attachment_type,
            "file_name": attachment.file_name,
            "file_url": attachment.file_url,
            "content_type": attachment.content_type,
            "file_size_bytes": attachment.file_size_bytes,
            "is_generated": bool(attachment.is_generated),
            "created_at": attachment.created_at,
        }

    @staticmethod
    def _serialize_submission_attachment(attachment) -> dict:
        return {
            "id": attachment.id,
            "file_name": attachment.file_name,
            "file_url": attachment.file_url,
            "content_type": attachment.content_type,
            "file_size_bytes": attachment.file_size_bytes,
            "created_at": attachment.created_at,
        }

    @staticmethod
    def _media_config() -> tuple[Path, str]:
        settings = get_settings()
        media_dir = Path(settings.media_base_dir).expanduser().resolve()
        media_dir.mkdir(parents=True, exist_ok=True)
        media_url = settings.media_base_url.strip() or "/media"
        if not media_url.startswith("/"):
            media_url = f"/{media_url}"
        return media_dir, media_url.rstrip("/")

    @staticmethod
    def _safe_display_name(raw_name: str | None, fallback: str) -> str:
        if not raw_name:
            return fallback
        cleaned = re.sub(r"[^\w\-.() ]+", "_", raw_name).strip()
        return cleaned[:120] or fallback

    @staticmethod
    def _ensure_pdf_bytes(raw: bytes) -> None:
        if not raw.lstrip().startswith(b"%PDF"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded PDF is invalid",
            )

    @staticmethod
    def _cache_key(
        *,
        student_id: str,
        subject_id: str | None,
        due_from: date | None,
        due_to: date | None,
        limit: int,
        offset: int,
    ) -> str:
        return (
            f"{student_homework_key(student_id, limit, offset)}"
            f":subject:{subject_id or 'all'}"
            f":from:{due_from.isoformat() if due_from else 'na'}"
            f":to:{due_to.isoformat() if due_to else 'na'}"
        )

    @classmethod
    def _serialize_submission(cls, submission, submission_attachments: list) -> dict:
        return {
            "id": submission.id,
            "status": submission.status.value if hasattr(submission.status, "value") else str(submission.status),
            "submitted_at": submission.submitted_at,
            "notes": submission.notes,
            "attachments": [
                cls._serialize_submission_attachment(attachment)
                for attachment in submission_attachments
            ],
        }

    async def list_for_student(
        self,
        *,
        user_id: str,
        student_id: str,
        batch_id: str | None,
        class_name: str | None,
        stream: str | None,
        subject_id: str | None,
        due_from: date | None,
        due_to: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        key = self._cache_key(
            student_id=student_id,
            subject_id=subject_id,
            due_from=due_from,
            due_to=due_to,
            limit=limit,
            offset=offset,
        )
        cached = await get_json(self.cache, key)
        if cached:
            return cached["items"], int(cached["total"])

        class_level = self._extract_class_level(class_name)
        normalized_stream = self._normalize_stream(stream)

        rows, total = await self.repo.list_for_student_with_read(
            user_id=user_id,
            student_id=student_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=normalized_stream,
            subject_id=subject_id,
            due_from=due_from,
            due_to=due_to,
            limit=limit,
            offset=offset,
        )

        homework_ids = [homework.id for homework, _ in rows]
        attachment_map = await self.repo.list_attachments_for_homework_ids(homework_ids=homework_ids)

        submission_map = await self.repo.list_submissions_for_student_homework_ids(
            student_id=student_id,
            homework_ids=homework_ids,
        )
        submission_ids = [submission.id for submission in submission_map.values()]
        submission_attachment_map = await self.repo.list_submission_attachments_for_submission_ids(
            submission_ids=submission_ids,
        )

        payload = []
        for homework, is_read in rows:
            attachments = attachment_map.get(homework.id, [])
            submission = submission_map.get(homework.id)
            submission_payload = None
            if submission:
                submission_payload = self._serialize_submission(
                    submission,
                    submission_attachment_map.get(submission.id, []),
                )

            payload.append(
                {
                    "id": homework.id,
                    "title": homework.title,
                    "description": homework.description,
                    "subject_id": homework.subject_id,
                    "due_date": homework.due_date,
                    "due_at": homework.due_at,
                    "expires_at": homework.expires_at,
                    "status": homework.status.value if hasattr(homework.status, "value") else str(homework.status),
                    "is_read": bool(is_read),
                    "attachment_count": len(attachments),
                    "attachments": [
                        self._serialize_attachment(attachment)
                        for attachment in attachments
                    ],
                    "is_submitted": submission is not None,
                    "submission": submission_payload,
                }
            )

        await set_json(self.cache, key, {"items": payload, "total": total}, ttl_seconds=120)
        return payload, total

    async def detail_for_student(
        self,
        *,
        homework_id: str,
        user_id: str,
        student_id: str,
        batch_id: str | None,
        class_name: str | None,
        stream: str | None,
    ) -> dict:
        class_level = self._extract_class_level(class_name)
        normalized_stream = self._normalize_stream(stream)

        homework, is_read = await self.repo.get_for_student_with_read(
            homework_id=homework_id,
            user_id=user_id,
            student_id=student_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=normalized_stream,
        )
        if not homework:
            raise NotFoundException("Homework not found")

        attachments = await self.repo.list_attachments_for_homework(homework_id=homework_id)
        submission = await self.repo.get_submission_for_student(
            homework_id=homework_id,
            student_id=student_id,
        )
        submission_payload = None
        if submission:
            submission_attachments = await self.repo.list_submission_attachments(
                submission_id=submission.id,
            )
            submission_payload = self._serialize_submission(submission, submission_attachments)

        return {
            "id": homework.id,
            "title": homework.title,
            "description": homework.description,
            "subject_id": homework.subject_id,
            "due_date": homework.due_date,
            "due_at": homework.due_at,
            "expires_at": homework.expires_at,
            "status": homework.status.value if hasattr(homework.status, "value") else str(homework.status),
            "is_read": bool(is_read),
            "attachment_count": len(attachments),
            "attachments": [self._serialize_attachment(attachment) for attachment in attachments],
            "is_submitted": submission is not None,
            "submission": submission_payload,
        }

    async def submit_for_student(
        self,
        *,
        homework_id: str,
        user_id: str,
        student_id: str,
        batch_id: str | None,
        class_name: str | None,
        stream: str | None,
        file: UploadFile,
        notes: str | None,
    ) -> dict:
        class_level = self._extract_class_level(class_name)
        normalized_stream = self._normalize_stream(stream)

        homework, _ = await self.repo.get_for_student_with_read(
            homework_id=homework_id,
            user_id=user_id,
            student_id=student_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=normalized_stream,
        )
        if not homework:
            raise NotFoundException("Homework not found")

        content_type = (file.content_type or "").lower().strip()
        if content_type not in self._ALLOWED_DOC_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF attachment is supported for homework submission",
            )

        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
        if len(raw) > (20 * 1024 * 1024):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is too large. Max supported size is 20MB",
            )

        self._ensure_pdf_bytes(raw)

        now = datetime.now(UTC)
        due_cutoff_raw = homework.due_at or datetime.combine(
            homework.due_date,
            time(hour=23, minute=59, tzinfo=UTC),
        )
        # SQLite can return timezone-naive datetime values even when stored as UTC.
        due_cutoff = (
            due_cutoff_raw.astimezone(UTC)
            if due_cutoff_raw.tzinfo is not None
            else due_cutoff_raw.replace(tzinfo=UTC)
        )
        submission_status = (
            HomeworkSubmissionStatus.LATE
            if now > due_cutoff
            else HomeworkSubmissionStatus.SUBMITTED
        )

        submission = await self.repo.upsert_submission(
            homework_id=homework.id,
            student_id=student_id,
            submitted_by_user_id=user_id,
            submitted_at=now,
            status=submission_status,
            notes=(notes or "").strip() or None,
        )

        await self.repo.clear_submission_attachments(submission_id=submission.id)

        media_dir, media_url = self._media_config()
        submission_dir = media_dir / "homework_submissions" / homework.id / student_id
        submission_dir.mkdir(parents=True, exist_ok=True)

        extension = self._ALLOWED_DOC_TYPES.get(content_type, ".pdf")
        stored_name = f"{uuid4().hex}{extension}"
        stored_path = submission_dir / stored_name
        stored_path.write_bytes(raw)

        relative_path = f"homework_submissions/{homework.id}/{student_id}/{stored_name}"
        file_url = f"{media_url}/{relative_path}"

        fallback_name = "homework-submission.pdf"
        safe_name = self._safe_display_name(file.filename, fallback=fallback_name)
        attachment = await self.repo.add_submission_attachment(
            submission_id=submission.id,
            file_name=safe_name,
            storage_path=relative_path,
            file_url=file_url,
            content_type="application/pdf",
            file_size_bytes=len(raw),
        )

        await self.session.commit()

        await delete_keys(
            self.cache,
            [
                student_dashboard_key(student_id),
                student_homework_key(student_id, 8, 0),
                student_homework_key(student_id, 12, 0),
                student_homework_key(student_id, 20, 0),
                student_homework_key(student_id, 50, 0),
            ],
        )

        submission_payload = self._serialize_submission(submission, [attachment])
        return {
            "message": "Homework submitted successfully",
            "homework_id": homework.id,
            "is_submitted": True,
            "submission": submission_payload,
        }

    async def mark_all_seen(
        self,
        *,
        user_id: str,
        student_id: str,
        batch_id: str | None,
        class_name: str | None,
        stream: str | None,
    ) -> dict:
        class_level = self._extract_class_level(class_name)
        normalized_stream = self._normalize_stream(stream)

        marked_count = await self.repo.mark_visible_read_for_student(
            user_id=user_id,
            student_id=student_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=normalized_stream,
        )
        await self.notification_repo.mark_all_read_by_type(
            user_id=user_id,
            notification_type=NotificationType.HOMEWORK,
        )
        await self.session.commit()

        unseen_count = await self.repo.unseen_count_for_student(
            user_id=user_id,
            student_id=student_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=normalized_stream,
        )

        await delete_keys(
            self.cache,
            [
                student_dashboard_key(student_id),
                student_homework_key(student_id, 8, 0),
                student_homework_key(student_id, 12, 0),
                student_homework_key(student_id, 20, 0),
                student_homework_key(student_id, 50, 0),
                student_unread_notifications_key(user_id),
            ],
        )

        return {
            "marked_count": marked_count,
            "unseen_homework_count": unseen_count,
        }
