import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
try:
    from PIL import Image, ImageOps, UnidentifiedImageError
except ImportError:  # pragma: no cover
    Image = None
    ImageOps = None

    class UnidentifiedImageError(Exception):
        pass
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.keys import student_dashboard_key, student_notices_key, student_unread_notifications_key
from app.cache.utils import delete_keys
from app.core.config import get_settings
from app.core.exceptions import NotFoundException
from app.db.models.academic import Batch, Standard, StudentProfile, TeacherProfile
from app.db.models.audit import AuditLog
from app.db.models.content import Notice, NoticeAttachment, NoticeTarget
from app.db.models.enums import NoticeStatus, NotificationType, UserStatus
from app.db.models.notification import Notification
from app.db.models.user import User
from app.schemas.admin import AdminNoticeCreateDTO


@dataclass(slots=True)
class _Recipient:
    user_id: str
    student_id: str | None


class AdminNoticeService:
    _ALLOWED_IMAGE_TYPES: dict[str, str] = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    _ALLOWED_DOC_TYPES: dict[str, str] = {
        "application/pdf": ".pdf",
    }

    def __init__(self, session: AsyncSession, cache: Redis | None = None) -> None:
        self.session = session
        self.cache = cache

    async def _audit(
        self,
        *,
        actor_user_id: str | None,
        action: str,
        entity_type: str,
        entity_id: str,
        before_state: dict | None,
        after_state: dict | None,
        ip_address: str | None,
    ) -> None:
        self.session.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_state=json.dumps(before_state, default=str) if before_state is not None else None,
                after_state=json.dumps(after_state, default=str) if after_state is not None else None,
                ip_address=ip_address,
                created_at=datetime.now(UTC),
            )
        )

    @staticmethod
    def _extract_grade(class_name: str | None, standard_name: str | None) -> int | None:
        source = f"{class_name or ''} {standard_name or ''}".lower()
        match = re.search(r"(10|11|12)", source)
        if not match:
            return None
        return int(match.group(1))

    @staticmethod
    def _normalize_stream(stream: str | None) -> str | None:
        if stream is None:
            return None
        normalized = stream.strip().lower()
        if normalized in {"science", "commerce"}:
            return normalized
        return None

    @classmethod
    def _parse_grade_target_id(cls, target_id: str) -> tuple[int | None, str | None]:
        raw = (target_id or "").strip().lower()
        if not raw:
            return None, None

        if ":" in raw:
            grade_raw, stream_raw = raw.split(":", 1)
            try:
                grade = int(grade_raw)
            except ValueError:
                return None, None
            if grade not in {10, 11, 12}:
                return None, None
            return grade, cls._normalize_stream(stream_raw)

        try:
            grade = int(raw)
        except ValueError:
            return None, None
        if grade not in {10, 11, 12}:
            return None, None
        return grade, None

    @classmethod
    def _target_label(cls, target_type: str, target_id: str) -> str:
        if target_type == "all_students":
            return "All Students"
        if target_type == "all":
            return "All Users"
        if target_type == "grade":
            grade, stream = cls._parse_grade_target_id(target_id)
            if grade is None:
                return f"Grade ({target_id})"
            if stream:
                return f"Class {grade} {stream.title()}"
            return f"Class {grade}"
        if target_type == "batch":
            return f"Batch ({target_id})"
        if target_type == "student":
            return "Specific Student"
        if target_type == "teacher":
            return "Specific Teacher"
        return f"{target_type}:{target_id}"

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

    @classmethod
    def _compress_image(cls, payload: bytes) -> tuple[bytes, int, int]:
        if Image is None or ImageOps is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Image processing dependency is not installed on server",
            )

        try:
            with Image.open(BytesIO(payload)) as image:
                image = ImageOps.exif_transpose(image)
                max_edge = 1600
                image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
                if image.mode not in {"RGB", "L"}:
                    image = image.convert("RGB")
                elif image.mode == "L":
                    image = image.convert("RGB")

                width, height = image.size
                output = BytesIO()
                image.save(output, format="JPEG", quality=82, optimize=True, progressive=True)
                return output.getvalue(), width, height
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded image is invalid or unsupported",
            ) from exc

    async def list_notices(self, *, status: str | None, limit: int, offset: int) -> tuple[list[dict], int]:
        query = select(Notice)
        if status:
            query = query.where(Notice.status == NoticeStatus(status))

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        notices = (
            await self.session.execute(
                query.order_by(Notice.created_at.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()

        notice_ids = [item.id for item in notices]
        targets_by_notice: dict[str, list[NoticeTarget]] = {notice_id: [] for notice_id in notice_ids}
        attachment_count_by_notice: dict[str, int] = {notice_id: 0 for notice_id in notice_ids}

        if notice_ids:
            target_rows = (
                await self.session.execute(
                    select(NoticeTarget)
                    .where(NoticeTarget.notice_id.in_(notice_ids))
                    .order_by(NoticeTarget.created_at.asc())
                )
            ).scalars().all()
            for row in target_rows:
                targets_by_notice.setdefault(row.notice_id, []).append(row)

            attachment_rows = (
                await self.session.execute(
                    select(NoticeAttachment.notice_id, func.count(NoticeAttachment.id))
                    .where(NoticeAttachment.notice_id.in_(notice_ids))
                    .group_by(NoticeAttachment.notice_id)
                )
            ).all()
            for notice_id, count in attachment_rows:
                attachment_count_by_notice[notice_id] = int(count)

        return [
            {
                "id": notice.id,
                "title": notice.title,
                "status": notice.status.value if hasattr(notice.status, "value") else str(notice.status),
                "priority": notice.priority,
                "publish_at": notice.publish_at,
                "created_at": notice.created_at,
                "targets": [
                    {
                        "target_type": target.target_type,
                        "target_id": target.target_id,
                        "label": self._target_label(target.target_type, target.target_id),
                    }
                    for target in targets_by_notice.get(notice.id, [])
                ],
                "attachment_count": attachment_count_by_notice.get(notice.id, 0),
            }
            for notice in notices
        ], total

    async def create_notice(
        self,
        *,
        payload: AdminNoticeCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        notice = Notice(
            title=payload.title,
            body=payload.body,
            status=NoticeStatus.DRAFT,
            priority=payload.priority,
            publish_at=payload.publish_at,
            created_by=actor_user_id,
        )
        self.session.add(notice)
        await self.session.flush()

        for target in payload.targets:
            self.session.add(
                NoticeTarget(
                    notice_id=notice.id,
                    target_type=target.target_type,
                    target_id=target.target_id,
                )
            )

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.notice.create",
            entity_type="notice",
            entity_id=notice.id,
            before_state=None,
            after_state={
                "title": notice.title,
                "status": notice.status.value,
                "targets": [target.model_dump() for target in payload.targets],
            },
            ip_address=ip_address,
        )
        await self.session.commit()

        return {
            "id": notice.id,
            "title": notice.title,
            "status": notice.status.value,
            "priority": notice.priority,
            "publish_at": notice.publish_at,
        }

    async def upload_notice_attachment(
        self,
        *,
        notice_id: str,
        file: UploadFile,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        notice = await self.session.get(Notice, notice_id)
        if not notice:
            raise NotFoundException("Notice not found")

        content_type = (file.content_type or "").lower().strip()
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

        max_upload_bytes = 15 * 1024 * 1024
        if len(raw) > max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is too large. Max supported size is 15MB",
            )

        attachment_type: str
        stored_bytes: bytes
        stored_content_type: str
        extension: str
        image_width: int | None = None
        image_height: int | None = None

        if content_type in self._ALLOWED_IMAGE_TYPES:
            attachment_type = "image"
            stored_bytes, image_width, image_height = self._compress_image(raw)
            stored_content_type = "image/jpeg"
            extension = ".jpg"
        elif content_type in self._ALLOWED_DOC_TYPES:
            attachment_type = "pdf"
            stored_bytes = raw
            stored_content_type = "application/pdf"
            extension = ".pdf"
            if not raw.lstrip().startswith(b"%PDF"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded PDF is invalid",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only image (JPG/PNG/WEBP) and PDF files are allowed",
            )

        media_dir, media_url = self._media_config()
        notice_dir = media_dir / "notices" / notice.id
        notice_dir.mkdir(parents=True, exist_ok=True)

        stored_name = f"{uuid4().hex}{extension}"
        stored_path = notice_dir / stored_name
        stored_path.write_bytes(stored_bytes)

        relative_path = f"notices/{notice.id}/{stored_name}"
        file_url = f"{media_url}/{relative_path}"

        fallback_name = f"notice-{attachment_type}{extension}"
        original_name = self._safe_display_name(file.filename, fallback=fallback_name)

        attachment = NoticeAttachment(
            notice_id=notice.id,
            attachment_type=attachment_type,
            file_name=original_name,
            storage_path=relative_path,
            file_url=file_url,
            content_type=stored_content_type,
            file_size_bytes=len(stored_bytes),
            image_width=image_width,
            image_height=image_height,
        )
        self.session.add(attachment)
        await self.session.flush()

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.notice.attachment.upload",
            entity_type="notice_attachment",
            entity_id=attachment.id,
            before_state=None,
            after_state={
                "notice_id": notice.id,
                "attachment_type": attachment_type,
                "file_name": original_name,
                "file_size_bytes": len(stored_bytes),
                "content_type": stored_content_type,
            },
            ip_address=ip_address,
        )
        await self.session.commit()

        return {
            "id": attachment.id,
            "notice_id": attachment.notice_id,
            "attachment_type": attachment.attachment_type,
            "file_name": attachment.file_name,
            "file_url": attachment.file_url,
            "content_type": attachment.content_type,
            "file_size_bytes": attachment.file_size_bytes,
            "image_width": attachment.image_width,
            "image_height": attachment.image_height,
            "created_at": attachment.created_at,
        }

    async def _resolve_recipients(self, *, targets: list[NoticeTarget]) -> list[_Recipient]:
        recipient_map: dict[str, _Recipient] = {}

        async def add_student_rows(rows: list[tuple[str, str]]) -> None:
            for user_id, student_id in rows:
                recipient_map[user_id] = _Recipient(user_id=user_id, student_id=student_id)

        for target in targets:
            target_type = target.target_type
            target_id = target.target_id

            if target_type == "all":
                rows = (
                    await self.session.execute(
                        select(User.id)
                        .where(User.status == UserStatus.ACTIVE)
                    )
                ).all()
                for row in rows:
                    recipient_map[row[0]] = _Recipient(user_id=row[0], student_id=None)
                continue

            if target_type == "all_students":
                rows = (
                    await self.session.execute(
                        select(StudentProfile.user_id, StudentProfile.id)
                        .join(User, User.id == StudentProfile.user_id)
                        .where(User.status == UserStatus.ACTIVE)
                    )
                ).all()
                await add_student_rows(rows)
                continue

            if target_type == "student":
                row = (
                    await self.session.execute(
                        select(StudentProfile.user_id, StudentProfile.id)
                        .join(User, User.id == StudentProfile.user_id)
                        .where(StudentProfile.id == target_id, User.status == UserStatus.ACTIVE)
                    )
                ).first()
                if row:
                    recipient_map[row[0]] = _Recipient(user_id=row[0], student_id=row[1])
                continue

            if target_type == "teacher":
                row = (
                    await self.session.execute(
                        select(TeacherProfile.user_id)
                        .join(User, User.id == TeacherProfile.user_id)
                        .where(TeacherProfile.id == target_id, User.status == UserStatus.ACTIVE)
                    )
                ).first()
                if row:
                    recipient_map[row[0]] = _Recipient(user_id=row[0], student_id=None)
                continue

            if target_type == "batch":
                rows = (
                    await self.session.execute(
                        select(StudentProfile.user_id, StudentProfile.id)
                        .join(User, User.id == StudentProfile.user_id)
                        .where(
                            StudentProfile.current_batch_id == target_id,
                            User.status == UserStatus.ACTIVE,
                        )
                    )
                ).all()
                await add_student_rows(rows)
                continue

            if target_type == "grade":
                grade, stream = self._parse_grade_target_id(target_id)
                if grade is None:
                    continue

                rows = (
                    await self.session.execute(
                        select(
                            StudentProfile.user_id,
                            StudentProfile.id,
                            StudentProfile.class_name,
                            StudentProfile.stream,
                            Standard.name,
                        )
                        .join(User, User.id == StudentProfile.user_id)
                        .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
                        .outerjoin(Standard, Standard.id == Batch.standard_id)
                        .where(User.status == UserStatus.ACTIVE)
                    )
                ).all()

                for user_id, student_id, class_name, student_stream, standard_name in rows:
                    student_grade = self._extract_grade(class_name, standard_name)
                    if student_grade != grade:
                        continue

                    if stream and grade in {11, 12}:
                        normalized_student_stream = self._normalize_stream(student_stream)
                        if normalized_student_stream != stream:
                            continue

                    recipient_map[user_id] = _Recipient(user_id=user_id, student_id=student_id)

        return list(recipient_map.values())

    async def _invalidate_student_cache(self, *, recipients: list[_Recipient]) -> None:
        if not self.cache:
            return

        keys: set[str] = set()
        for recipient in recipients:
            keys.add(student_unread_notifications_key(recipient.user_id))
            if recipient.student_id:
                keys.add(student_dashboard_key(recipient.student_id))
                keys.add(student_notices_key(recipient.student_id, 8, 0))
                keys.add(student_notices_key(recipient.student_id, 12, 0))
                keys.add(student_notices_key(recipient.student_id, 20, 0))

        await delete_keys(self.cache, list(keys))

    async def publish_notice(
        self,
        *,
        notice_id: str,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        notice = await self.session.get(Notice, notice_id)
        if not notice:
            raise NotFoundException("Notice not found")

        targets = (
            await self.session.execute(
                select(NoticeTarget).where(NoticeTarget.notice_id == notice.id)
            )
        ).scalars().all()

        if notice.status == NoticeStatus.PUBLISHED:
            return {
                "id": notice.id,
                "status": notice.status.value,
                "publish_at": notice.publish_at,
                "recipient_count": 0,
            }

        before = {
            "status": notice.status.value if hasattr(notice.status, "value") else str(notice.status),
            "publish_at": notice.publish_at,
        }

        notice.status = NoticeStatus.PUBLISHED
        if notice.publish_at is None:
            notice.publish_at = datetime.now(UTC)

        recipients = await self._resolve_recipients(targets=targets)
        for recipient in recipients:
            self.session.add(
                Notification(
                    recipient_user_id=recipient.user_id,
                    notification_type=NotificationType.NOTICE,
                    title=notice.title,
                    body=notice.body[:500],
                    metadata_json={
                        "source": "notice",
                        "notice_id": notice.id,
                    },
                    is_read=False,
                )
            )

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.notice.publish",
            entity_type="notice",
            entity_id=notice.id,
            before_state=before,
            after_state={
                "status": notice.status.value,
                "publish_at": notice.publish_at,
                "recipient_count": len(recipients),
            },
            ip_address=ip_address,
        )

        await self.session.commit()
        await self._invalidate_student_cache(recipients=recipients)

        return {
            "id": notice.id,
            "status": notice.status.value,
            "publish_at": notice.publish_at,
            "recipient_count": len(recipients),
        }
