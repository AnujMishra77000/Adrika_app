import json
import re
import textwrap
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from redis.asyncio import Redis
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.keys import student_dashboard_key, student_homework_key, student_unread_notifications_key
from app.cache.utils import delete_keys
from app.core.config import get_settings
from app.core.exceptions import NotFoundException
from app.db.models.academic import Batch, Standard, StudentProfile, TeacherProfile
from app.db.models.audit import AuditLog
from app.db.models.enums import HomeworkStatus, NotificationType, UserStatus
from app.db.models.homework import (
    Homework,
    HomeworkAttachment,
    HomeworkSubmission,
    HomeworkSubmissionAttachment,
    HomeworkTarget,
)
from app.db.models.notification import Notification
from app.db.models.user import User
from app.schemas.admin import AdminHomeworkCreateDTO


@dataclass(slots=True)
class _Recipient:
    user_id: str
    student_id: str | None


INDIA_TZ = ZoneInfo("Asia/Kolkata")


class AdminHomeworkService:
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
        if normalized in {"science", "sci"}:
            return "science"
        if normalized in {"commerce", "comm"}:
            return "commerce"
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

    @staticmethod
    def _pdf_escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    @classmethod
    def _build_text_pdf(cls, *, title: str, description: str | None, due_at: datetime) -> bytes:
        local_due = due_at.astimezone(INDIA_TZ)
        lines = [
            "Adrika Smart Institute",
            "Homework Sheet",
            "",
            f"Title: {title}",
            f"Due: {local_due.strftime('%d %b %Y, %I:%M %p')}",
            "",
            "Instructions:",
        ]

        normalized_description = (description or "").strip()
        source_lines = normalized_description.splitlines() if normalized_description else ["(No additional instructions)"]

        for raw_line in source_lines:
            cleaned = raw_line.strip()
            if not cleaned:
                lines.append("")
                continue
            wrapped = textwrap.wrap(cleaned, width=92)
            if not wrapped:
                lines.append("")
                continue
            lines.extend(wrapped)

        if len(lines) > 58:
            lines = lines[:58] + ["... (truncated)"]

        stream_lines = ["BT", "/F1 11 Tf", "48 800 Td", "14 TL"]
        first = True
        for line in lines:
            escaped = cls._pdf_escape(line)
            if first:
                stream_lines.append(f"({escaped}) Tj")
                first = False
            else:
                stream_lines.append("T*")
                stream_lines.append(f"({escaped}) Tj")
        stream_lines.append("ET")

        stream = "\n".join(stream_lines).encode("latin-1", errors="replace")

        objects = [
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n",
            b"4 0 obj\n<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream\nendobj\n",
            b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        ]

        pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for obj in objects:
            offsets.append(len(pdf))
            pdf.extend(obj)

        xref_start = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode())

        pdf.extend(
            (
                f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref_start}\n%%EOF\n"
            ).encode()
        )

        return bytes(pdf)

    @staticmethod
    def _ensure_pdf_bytes(raw: bytes) -> None:
        if not raw.lstrip().startswith(b"%PDF"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded PDF is invalid",
            )

    @staticmethod
    def _resolve_due_at(payload: AdminHomeworkCreateDTO) -> tuple[datetime, date]:
        if payload.due_at is not None:
            due_at_local = payload.due_at
        elif payload.due_date is not None:
            due_at_local = datetime.combine(payload.due_date, time(hour=23, minute=59))
        else:  # pragma: no cover
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Due date is required")

        if due_at_local.tzinfo is None:
            due_at_local = due_at_local.replace(tzinfo=INDIA_TZ)
        else:
            due_at_local = due_at_local.astimezone(INDIA_TZ)

        return due_at_local.astimezone(UTC), due_at_local.date()

    async def _store_attachment_bytes(
        self,
        *,
        homework: Homework,
        payload: bytes,
        content_type: str,
        file_name: str,
        is_generated: bool,
    ) -> HomeworkAttachment:
        media_dir, media_url = self._media_config()
        homework_dir = media_dir / "homework" / homework.id
        homework_dir.mkdir(parents=True, exist_ok=True)

        extension = self._ALLOWED_DOC_TYPES.get(content_type, ".pdf")
        stored_name = f"{uuid4().hex}{extension}"
        stored_path = homework_dir / stored_name
        stored_path.write_bytes(payload)

        relative_path = f"homework/{homework.id}/{stored_name}"
        file_url = f"{media_url}/{relative_path}"

        attachment = HomeworkAttachment(
            homework_id=homework.id,
            attachment_type="pdf",
            file_name=file_name,
            storage_path=relative_path,
            file_url=file_url,
            content_type=content_type,
            file_size_bytes=len(payload),
            is_generated=is_generated,
        )
        self.session.add(attachment)
        await self.session.flush()
        return attachment

    async def list_homework(
        self,
        *,
        status: str | None,
        due_from: date | None,
        due_to: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = select(Homework)
        if status:
            query = query.where(Homework.status == HomeworkStatus(status))

        if due_from:
            due_from_dt = datetime.combine(due_from, time.min, tzinfo=UTC)
            query = query.where(
                or_(
                    and_(Homework.due_at.is_not(None), Homework.due_at >= due_from_dt),
                    and_(Homework.due_at.is_(None), Homework.due_date >= due_from),
                )
            )

        if due_to:
            due_to_dt = datetime.combine(due_to, time.max, tzinfo=UTC)
            query = query.where(
                or_(
                    and_(Homework.due_at.is_not(None), Homework.due_at <= due_to_dt),
                    and_(Homework.due_at.is_(None), Homework.due_date <= due_to),
                )
            )

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        homeworks = (
            await self.session.execute(
                query.order_by(Homework.created_at.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()

        homework_ids = [row.id for row in homeworks]
        targets_by_homework: dict[str, list[HomeworkTarget]] = {homework_id: [] for homework_id in homework_ids}
        attachment_count_by_homework: dict[str, int] = {homework_id: 0 for homework_id in homework_ids}

        if homework_ids:
            target_rows = (
                await self.session.execute(
                    select(HomeworkTarget)
                    .where(HomeworkTarget.homework_id.in_(homework_ids))
                    .order_by(HomeworkTarget.created_at.asc())
                )
            ).scalars().all()
            for row in target_rows:
                targets_by_homework.setdefault(row.homework_id, []).append(row)

            attachment_rows = (
                await self.session.execute(
                    select(HomeworkAttachment.homework_id, func.count(HomeworkAttachment.id))
                    .where(HomeworkAttachment.homework_id.in_(homework_ids))
                    .group_by(HomeworkAttachment.homework_id)
                )
            ).all()
            for homework_id, count in attachment_rows:
                attachment_count_by_homework[homework_id] = int(count)

        return [
            {
                "id": homework.id,
                "title": homework.title,
                "description": homework.description,
                "subject_id": homework.subject_id,
                "status": homework.status.value if hasattr(homework.status, "value") else str(homework.status),
                "due_date": homework.due_date,
                "due_at": homework.due_at,
                "publish_at": homework.publish_at,
                "expires_at": homework.expires_at,
                "created_at": homework.created_at,
                "targets": [
                    {
                        "target_type": target.target_type,
                        "target_id": target.target_id,
                        "label": self._target_label(target.target_type, target.target_id),
                    }
                    for target in targets_by_homework.get(homework.id, [])
                ],
                "attachment_count": attachment_count_by_homework.get(homework.id, 0),
            }
            for homework in homeworks
        ], total

    async def list_homework_completions(
        self,
        *,
        homework_id: str | None,
        class_level: int | None,
        stream: str | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = (
            select(
                HomeworkSubmission,
                Homework,
                StudentProfile,
                User,
                Batch,
                Standard,
            )
            .join(Homework, Homework.id == HomeworkSubmission.homework_id)
            .join(StudentProfile, StudentProfile.id == HomeworkSubmission.student_id)
            .join(User, User.id == StudentProfile.user_id)
            .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
            .outerjoin(Standard, Standard.id == Batch.standard_id)
        )

        if homework_id:
            query = query.where(HomeworkSubmission.homework_id == homework_id)

        if class_level is not None:
            class_pattern = f"%{class_level}%"
            query = query.where(
                or_(
                    func.lower(func.coalesce(StudentProfile.class_name, "")).like(class_pattern),
                    func.lower(func.coalesce(Standard.name, "")).like(class_pattern),
                )
            )

        normalized_stream = self._normalize_stream(stream)
        if normalized_stream:
            query = query.where(func.lower(func.coalesce(StudentProfile.stream, "")) == normalized_stream)

        if search:
            q = f"%{search.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(func.coalesce(User.full_name, "")).like(q),
                    func.lower(func.coalesce(User.phone, "")).like(q),
                    func.lower(func.coalesce(StudentProfile.admission_no, "")).like(q),
                )
            )

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

        rows = (
            await self.session.execute(
                query
                .order_by(HomeworkSubmission.submitted_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()

        submission_ids = [row[0].id for row in rows]
        attachments_map: dict[str, list[HomeworkSubmissionAttachment]] = {submission_id: [] for submission_id in submission_ids}

        if submission_ids:
            attachments = (
                await self.session.execute(
                    select(HomeworkSubmissionAttachment)
                    .where(HomeworkSubmissionAttachment.submission_id.in_(submission_ids))
                    .order_by(HomeworkSubmissionAttachment.created_at.asc())
                )
            ).scalars().all()
            for attachment in attachments:
                attachments_map.setdefault(attachment.submission_id, []).append(attachment)

        payload: list[dict] = []
        for submission, homework, student, user, _batch, standard in rows:
            class_name = student.class_name or (standard.name if standard else None) or "-"
            stream_name = self._normalize_stream(student.stream)
            stream_label = stream_name.title() if stream_name else ("General" if "10" in class_name else "-")
            submission_attachments = attachments_map.get(submission.id, [])

            payload.append(
                {
                    "submission_id": submission.id,
                    "homework_id": homework.id,
                    "homework_title": homework.title,
                    "student_id": student.id,
                    "student_name": user.full_name,
                    "contact": user.phone,
                    "admission_no": student.admission_no,
                    "class_name": class_name,
                    "stream": stream_label,
                    "status": submission.status.value if hasattr(submission.status, "value") else str(submission.status),
                    "submitted_at": submission.submitted_at,
                    "submitted_at_ist": submission.submitted_at.astimezone(INDIA_TZ),
                    "notes": submission.notes,
                    "attachments": [
                        {
                            "id": attachment.id,
                            "file_name": attachment.file_name,
                            "file_url": attachment.file_url,
                            "content_type": attachment.content_type,
                            "file_size_bytes": attachment.file_size_bytes,
                            "created_at": attachment.created_at,
                        }
                        for attachment in submission_attachments
                    ],
                }
            )

        return payload, total

    async def create_homework(
        self,
        *,
        payload: AdminHomeworkCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        due_at, due_date = self._resolve_due_at(payload)
        expires_at = due_at + timedelta(hours=24)

        homework = Homework(
            title=payload.title,
            description=(payload.description or "").strip(),
            subject_id=payload.subject_id,
            due_date=due_date,
            due_at=due_at,
            publish_at=None,
            expires_at=expires_at,
            status=HomeworkStatus.DRAFT,
            created_by=actor_user_id,
        )
        self.session.add(homework)
        await self.session.flush()

        for target in payload.targets:
            self.session.add(
                HomeworkTarget(
                    homework_id=homework.id,
                    target_type=target.target_type,
                    target_id=target.target_id,
                )
            )

        generated_pdf = self._build_text_pdf(
            title=payload.title,
            description=(payload.description or "").strip(),
            due_at=due_at,
        )

        generated_name = self._safe_display_name(
            f"{payload.title}-homework.pdf",
            fallback="homework-sheet.pdf",
        )
        generated_attachment = await self._store_attachment_bytes(
            homework=homework,
            payload=generated_pdf,
            content_type="application/pdf",
            file_name=generated_name,
            is_generated=True,
        )

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.homework.create",
            entity_type="homework",
            entity_id=homework.id,
            before_state=None,
            after_state={
                "title": homework.title,
                "status": homework.status.value,
                "due_at": homework.due_at,
                "expires_at": homework.expires_at,
                "targets": [target.model_dump() for target in payload.targets],
                "generated_attachment_id": generated_attachment.id,
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "id": homework.id,
            "title": homework.title,
            "status": homework.status.value,
            "due_date": homework.due_date,
            "due_at": homework.due_at,
            "expires_at": homework.expires_at,
            "generated_attachment_id": generated_attachment.id,
        }

    async def upload_homework_attachment(
        self,
        *,
        homework_id: str,
        file: UploadFile,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        homework = await self.session.get(Homework, homework_id)
        if not homework:
            raise NotFoundException("Homework not found")

        content_type = (file.content_type or "").lower().strip()
        if content_type not in self._ALLOWED_DOC_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF attachment is supported for homework",
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

        fallback_name = "homework-attachment.pdf"
        safe_name = self._safe_display_name(file.filename, fallback=fallback_name)
        attachment = await self._store_attachment_bytes(
            homework=homework,
            payload=raw,
            content_type="application/pdf",
            file_name=safe_name,
            is_generated=False,
        )

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.homework.attachment.upload",
            entity_type="homework_attachment",
            entity_id=attachment.id,
            before_state=None,
            after_state={
                "homework_id": homework.id,
                "file_name": attachment.file_name,
                "file_size_bytes": attachment.file_size_bytes,
                "content_type": attachment.content_type,
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "id": attachment.id,
            "homework_id": attachment.homework_id,
            "attachment_type": attachment.attachment_type,
            "file_name": attachment.file_name,
            "file_url": attachment.file_url,
            "content_type": attachment.content_type,
            "file_size_bytes": attachment.file_size_bytes,
            "is_generated": bool(attachment.is_generated),
            "created_at": attachment.created_at,
        }

    async def _resolve_recipients(self, *, targets: list[HomeworkTarget]) -> list[_Recipient]:
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
                keys.add(student_homework_key(recipient.student_id, 8, 0))
                keys.add(student_homework_key(recipient.student_id, 12, 0))
                keys.add(student_homework_key(recipient.student_id, 20, 0))
                keys.add(student_homework_key(recipient.student_id, 50, 0))

        await delete_keys(self.cache, list(keys))

    async def publish_homework(
        self,
        *,
        homework_id: str,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        homework = await self.session.get(Homework, homework_id)
        if not homework:
            raise NotFoundException("Homework not found")

        targets = (
            await self.session.execute(
                select(HomeworkTarget).where(HomeworkTarget.homework_id == homework.id)
            )
        ).scalars().all()

        if homework.status == HomeworkStatus.PUBLISHED:
            return {
                "id": homework.id,
                "status": homework.status.value,
                "publish_at": homework.publish_at,
                "recipient_count": 0,
            }

        before = {
            "status": homework.status.value if hasattr(homework.status, "value") else str(homework.status),
            "publish_at": homework.publish_at,
        }

        homework.status = HomeworkStatus.PUBLISHED
        if homework.publish_at is None:
            homework.publish_at = datetime.now(UTC)
        if homework.expires_at is None:
            reference_due_at = homework.due_at or datetime.now(UTC)
            homework.expires_at = reference_due_at + timedelta(hours=24)

        recipients = await self._resolve_recipients(targets=targets)
        for recipient in recipients:
            self.session.add(
                Notification(
                    recipient_user_id=recipient.user_id,
                    notification_type=NotificationType.HOMEWORK,
                    title=homework.title,
                    body=homework.description[:500],
                    metadata_json={
                        "source": "homework",
                        "homework_id": homework.id,
                    },
                    is_read=False,
                )
            )

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.homework.publish",
            entity_type="homework",
            entity_id=homework.id,
            before_state=before,
            after_state={
                "status": homework.status.value,
                "publish_at": homework.publish_at,
                "expires_at": homework.expires_at,
                "recipient_count": len(recipients),
            },
            ip_address=ip_address,
        )

        await self.session.commit()
        await self._invalidate_student_cache(recipients=recipients)

        return {
            "id": homework.id,
            "status": homework.status.value,
            "publish_at": homework.publish_at,
            "expires_at": homework.expires_at,
            "recipient_count": len(recipients),
        }
