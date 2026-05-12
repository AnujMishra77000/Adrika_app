from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import structlog
from fastapi import HTTPException, UploadFile, status as http_status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.keys import user_unread_notifications_key
from app.core.config import get_settings
from app.cache.utils import delete_keys, get_json, set_json
from app.db.models.academic import Batch, Standard, StudentProfile, TeacherProfile
from app.db.models.audit import AuditLog
from app.db.models.enums import DeliveryChannel, NotificationType, UserStatus
from app.db.models.notification import Notification, NotificationDelivery
from app.db.models.user import DeviceRegistration, User
from app.realtime.notification_hub import notification_hub
from app.repositories.notification_repo import NotificationRepository
from app.workers.tasks_notifications import dispatch_push_notification

logger = structlog.get_logger(__name__)


class NotificationService:
    def __init__(self, session: AsyncSession, cache: Redis) -> None:
        self.session = session
        self.repo = NotificationRepository(session)
        self.cache = cache

    _ALLOWED_ATTACHMENT_TYPES: dict[str, str] = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "text/plain": ".txt",
    }


    @staticmethod
    def _enum_value(value) -> str:
        return value.value if hasattr(value, "value") else str(value)

    @staticmethod
    def _serialize_notification(row: Notification) -> dict:
        metadata = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        source = metadata.get("source")
        if not source:
            source = row.notification_type.value if hasattr(row.notification_type, "value") else str(row.notification_type)
        return {
            "id": row.id,
            "notification_type": row.notification_type.value if hasattr(row.notification_type, "value") else str(row.notification_type),
            "title": row.title,
            "body": row.body,
            "metadata": metadata,
            "source": source,
            "notice_id": metadata.get("notice_id"),
            "is_read": row.is_read,
            "created_at": row.created_at,
        }

    async def list_for_user(
        self,
        *,
        user_id: str,
        is_read: bool | None,
        since_hours: int | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        since_at = None
        if since_hours and since_hours > 0:
            since_at = datetime.now(UTC) - timedelta(hours=since_hours)

        rows, total = await self.repo.list_for_user(
            user_id=user_id,
            is_read=is_read,
            since_at=since_at,
            limit=limit,
            offset=offset,
        )
        return [self._serialize_notification(row) for row in rows], total

    async def unread_count(self, *, user_id: str) -> int:
        key = user_unread_notifications_key(user_id)
        cached = await get_json(self.cache, key)
        if isinstance(cached, int):
            return cached

        count = await self.repo.unread_count(user_id=user_id)
        await set_json(self.cache, key, count, ttl_seconds=60)
        return count

    async def mark_read(self, *, user_id: str, notification_id: str) -> int:
        await self.repo.mark_read(user_id=user_id, notification_id=notification_id)
        await self.session.commit()
        await delete_keys(self.cache, [user_unread_notifications_key(user_id)])
        unread = await self.unread_count(user_id=user_id)
        await notification_hub.send_to_user(
            user_id=user_id,
            payload={"event": "notification.unread_count", "unread_count": unread},
        )
        return unread

    async def mark_all_read(self, *, user_id: str) -> int:
        await self.repo.mark_all_read(user_id=user_id)
        await self.session.commit()
        await delete_keys(self.cache, [user_unread_notifications_key(user_id)])
        unread = await self.unread_count(user_id=user_id)
        await notification_hub.send_to_user(
            user_id=user_id,
            payload={"event": "notification.unread_count", "unread_count": unread},
        )
        return unread

    @staticmethod
    def _safe_display_name(raw_name: str | None, fallback: str) -> str:
        if not raw_name:
            return fallback
        cleaned = re.sub(r"[^\w\-.() ]+", "_", raw_name).strip()
        return cleaned[:120] or fallback

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
    def _normalize_stream(value: str | None) -> str | None:
        text = (value or "").strip().lower()
        if text in {"science", "sci"}:
            return "science"
        if text in {"commerce", "comm"}:
            return "commerce"
        if text in {"common", "general"}:
            return "common"
        return None

    @staticmethod
    def _extract_grade(class_name: str | None, standard_name: str | None) -> int | None:
        source = f"{class_name or ''} {standard_name or ''}".lower()

        if "jr" in source and "kg" in source:
            return 0

        for level in range(12, 0, -1):
            if f"{level}th" in source:
                return level

        match = re.search(r"(^|\D)(1[0-2]|[1-9])(\D|$)", source)
        if match:
            try:
                return int(match.group(2))
            except Exception:
                return None
        return None

    @classmethod
    def _parse_grade_target(cls, raw_target_id: str) -> tuple[int, str | None]:
        target = raw_target_id.strip().lower()
        match = re.match(r"^(1[0-2]|[1-9])(?:\s*[:\-_ ]\s*(science|commerce|common))?$", target)
        if not match:
            raise ValueError("Invalid grade target format. Use jrkg-5 or 6 or 10 or 11:science or 12:commerce")
        grade = int(match.group(1))
        stream = cls._normalize_stream(match.group(2))
        if grade <= 10:
            return grade, None
        return grade, stream

    @staticmethod
    def _is_jrkg_to_5_target(raw_target_id: str) -> bool:
        token = raw_target_id.strip().lower().replace(" ", "").replace(".", "")
        return token in {
            "jrkg-5",
            "jrkgto5",
            "jrkg_5",
            "jrkgto5th",
            "junior_to_5",
            "junior5",
            "kg5",
            "kgto5",
            "jrtokg5",
            "jrkg-5th",
        }

    async def _resolve_target_user_ids(self, targets: list[dict]) -> list[str]:
        user_ids: set[str] = set()
        normalized_targets: list[tuple[str, str]] = []
        for target in targets:
            target_type = str(target.get("target_type", "")).strip().lower()
            target_id = str(target.get("target_id", "")).strip()
            if not target_type:
                continue
            normalized_targets.append((target_type, target_id))

        for target_type, target_id in normalized_targets:
            if target_type in {"all", "all_students"}:
                rows = (
                    await self.session.execute(
                        select(StudentProfile.user_id)
                        .join(User, User.id == StudentProfile.user_id)
                        .where(User.status == UserStatus.ACTIVE)
                    )
                ).all()
                user_ids.update([row[0] for row in rows])
                continue

            if target_type == "batch":
                rows = (
                    await self.session.execute(
                        select(StudentProfile.user_id)
                        .join(User, User.id == StudentProfile.user_id)
                        .where(StudentProfile.current_batch_id == target_id, User.status == UserStatus.ACTIVE)
                    )
                ).all()
                user_ids.update([row[0] for row in rows])
                continue

            if target_type == "grade":
                rows = (
                    await self.session.execute(
                        select(StudentProfile, User, Batch, Standard)
                        .join(User, User.id == StudentProfile.user_id)
                        .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
                        .outerjoin(Standard, Standard.id == Batch.standard_id)
                        .where(User.status == UserStatus.ACTIVE)
                    )
                ).all()

                if self._is_jrkg_to_5_target(target_id):
                    for profile, user, _batch, standard in rows:
                        student_grade = self._extract_grade(profile.class_name, standard.name if standard else None)
                        if student_grade is None:
                            continue
                        if 0 <= student_grade <= 5:
                            user_ids.add(user.id)
                    continue

                grade, expected_stream = self._parse_grade_target(target_id)
                for profile, user, _batch, standard in rows:
                    student_grade = self._extract_grade(profile.class_name, standard.name if standard else None)
                    if student_grade != grade:
                        continue
                    if grade in {11, 12} and expected_stream:
                        actual_stream = self._normalize_stream(profile.stream)
                        if actual_stream != expected_stream:
                            continue
                    user_ids.add(user.id)
                continue

            if target_type == "student":
                row = (
                    await self.session.execute(
                        select(StudentProfile.user_id)
                        .join(User, User.id == StudentProfile.user_id)
                        .where(
                            User.status == UserStatus.ACTIVE,
                            (StudentProfile.id == target_id) | (StudentProfile.user_id == target_id),
                        )
                    )
                ).first()
                if row:
                    user_ids.add(row[0])
                continue

            if target_type == "teacher":
                row = (
                    await self.session.execute(
                        select(TeacherProfile.user_id)
                        .join(User, User.id == TeacherProfile.user_id)
                        .where(
                            User.status == UserStatus.ACTIVE,
                            (TeacherProfile.id == target_id) | (TeacherProfile.user_id == target_id),
                        )
                    )
                ).first()
                if row:
                    user_ids.add(row[0])
                continue

        return sorted(user_ids)

    async def upload_attachment(self, *, file: UploadFile) -> dict:
        content_type = (file.content_type or "").strip().lower()
        ext = self._ALLOWED_ATTACHMENT_TYPES.get(content_type)
        if not ext:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Unsupported attachment type. Allowed: image, pdf, doc/docx, txt",
            )

        payload = await file.read()
        if not payload:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
        if len(payload) > 20_000_000:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Attachment exceeds 20MB limit")

        media_dir, media_url = self._media_config()
        attachment_dir = media_dir / "notifications"
        attachment_dir.mkdir(parents=True, exist_ok=True)

        base_name = self._safe_display_name(file.filename, "attachment")
        fallback_name = f"notification-{uuid4().hex[:10]}"
        if base_name.lower().endswith(ext):
            base_name = base_name[: -len(ext)]
        stored_name = f"{base_name or fallback_name}-{uuid4().hex[:8]}{ext}"
        file_path = attachment_dir / stored_name
        file_path.write_bytes(payload)

        return {
            "file_name": file.filename or stored_name,
            "stored_name": stored_name,
            "file_url": f"{media_url}/notifications/{stored_name}",
            "content_type": content_type,
            "file_size": len(payload),
        }

    async def register_device(
        self,
        *,
        user_id: str,
        device_id: str,
        platform: str,
        push_token: str,
    ) -> DeviceRegistration:
        normalized_platform = platform.strip().lower()
        by_token = await self.repo.get_device_by_token(push_token=push_token)
        if by_token:
            by_token.user_id = user_id
            by_token.device_id = device_id
            by_token.platform = normalized_platform
            by_token.is_active = True
            await self.session.commit()
            return by_token

        row = await self.repo.get_device_by_identity(
            user_id=user_id,
            device_id=device_id,
            platform=normalized_platform,
        )
        if row:
            row.push_token = push_token
            row.is_active = True
            await self.session.commit()
            return row

        row = DeviceRegistration(
            user_id=user_id,
            device_id=device_id,
            platform=normalized_platform,
            push_token=push_token,
            is_active=True,
        )
        self.session.add(row)
        await self.session.commit()
        return row

    async def _invalidate_unread_cache(self, user_ids: Iterable[str]) -> None:
        keys = [user_unread_notifications_key(user_id) for user_id in user_ids]
        await delete_keys(self.cache, keys)

    async def _broadcast_and_queue_push(self, notifications: list[Notification]) -> None:
        if not notifications:
            return

        recipients = sorted({row.recipient_user_id for row in notifications})
        unread_map = await self.repo.unread_count_for_users(user_ids=recipients)

        for row in notifications:
            unread_count = int(unread_map.get(row.recipient_user_id, 0))
            payload = {
                "event": "notification.new",
                "notification": self._serialize_notification(row),
                "unread_count": unread_count,
            }
            await notification_hub.send_to_user(user_id=row.recipient_user_id, payload=payload)

            try:
                dispatch_push_notification.delay(row.id)
            except Exception as exc:  # pragma: no cover - runtime branch
                logger.warning(
                    "push_dispatch_enqueue_failed",
                    notification_id=row.id,
                    user_id=row.recipient_user_id,
                    reason=str(exc),
                )

    async def send_to_targets(
        self,
        *,
        title: str,
        body: str,
        notification_type: str,
        targets: list[dict],
        metadata: dict | None = None,
        actor_user_id: str | None = None,
        audit_action: str | None = None,
        audit_ip_address: str | None = None,
    ) -> dict:
        user_ids = await self._resolve_target_user_ids(targets)
        if not user_ids:
            return {"notification_type": notification_type, "recipient_count": 0}

        typed_notification = NotificationType(notification_type)
        prepared_metadata = dict(metadata) if isinstance(metadata, dict) else {}
        prepared_metadata.setdefault("source", notification_type)
        broadcast_id = await self._next_broadcast_id()
        prepared_metadata.setdefault("broadcast_id", broadcast_id)
        now = datetime.now(UTC)

        rows: list[Notification] = []
        for user_id in user_ids:
            row = Notification(
                recipient_user_id=user_id,
                notification_type=typed_notification,
                title=title,
                body=body,
                metadata_json=prepared_metadata,
                is_read=False,
            )
            self.session.add(row)
            rows.append(row)

        await self.session.flush()

        for row in rows:
            self.session.add(
                NotificationDelivery(
                    notification_id=row.id,
                    channel=DeliveryChannel.IN_APP,
                    status="delivered",
                    attempt_no=1,
                    provider_response=json.dumps({"delivered_at": now.isoformat()}),
                )
            )

        if audit_action and actor_user_id:
            self.session.add(
                AuditLog(
                    actor_user_id=actor_user_id,
                    action=audit_action,
                    entity_type="notification_broadcast",
                    entity_id=f"bulk:{now.isoformat()}",
                    before_state=None,
                    after_state=json.dumps(
                        {
                            "title": title,
                            "body": body,
                            "notification_type": notification_type,
                            "targets": targets,
                            "recipient_count": len(user_ids),
                            "broadcast_id": broadcast_id,
                        },
                        default=str,
                    ),
                    ip_address=audit_ip_address,
                    created_at=now,
                )
            )

        await self.session.commit()
        await self._invalidate_unread_cache(user_ids)
        await self._broadcast_and_queue_push(rows)

        return {
            "notification_type": self._enum_value(typed_notification),
            "recipient_count": len(user_ids),
            "broadcast_id": broadcast_id,
        }


    async def _next_broadcast_id(self) -> str:
        rows = (
            await self.session.execute(
                select(AuditLog.after_state)
                .where(
                    AuditLog.action == "admin.notification.create",
                    AuditLog.entity_type == "notification_broadcast",
                )
            )
        ).all()

        max_index = 0
        for (after_state_raw,) in rows:
            if not after_state_raw:
                continue
            try:
                parsed = json.loads(after_state_raw)
            except Exception:
                continue

            broadcast_id = parsed.get("broadcast_id")
            if not isinstance(broadcast_id, str):
                continue

            normalized = broadcast_id.strip().lower()
            if not normalized.startswith("adr"):
                continue

            suffix = normalized[3:]
            if suffix.isdigit():
                max_index = max(max_index, int(suffix))

        next_index = max_index + 1
        return f"adr{next_index:02d}"

    async def list_broadcast_history(
        self,
        *,
        limit: int,
        offset: int,
        title_query: str | None = None,
        on_date: date | None = None,
    ) -> tuple[list[dict], int]:
        rows = (
            await self.session.execute(
                select(AuditLog, User)
                .outerjoin(User, User.id == AuditLog.actor_user_id)
                .where(
                    AuditLog.action == "admin.notification.create",
                    AuditLog.entity_type == "notification_broadcast",
                )
                .order_by(AuditLog.created_at.desc())
            )
        ).all()

        mapped: list[dict] = []
        title_filter = (title_query or "").strip().lower()

        for audit, actor in rows:
            after_state = {}
            if audit.after_state:
                try:
                    after_state = json.loads(audit.after_state)
                except Exception:
                    after_state = {}

            title_value = str(after_state.get("title") or "")
            if title_filter and title_filter not in title_value.lower():
                continue
            if on_date and (audit.created_at is None or audit.created_at.date() != on_date):
                continue

            mapped.append(
                {
                    "id": audit.id,
                    "created_at": audit.created_at,
                    "actor_name": actor.full_name if actor else None,
                    "title": title_value,
                    "notification_type": after_state.get("notification_type"),
                    "recipient_count": int(after_state.get("recipient_count") or 0),
                    "targets": after_state.get("targets") or [],
                    "broadcast_id": after_state.get("broadcast_id"),
                }
            )

        total = len(mapped)
        return mapped[offset : offset + limit], total
