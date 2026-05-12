import json
import re
import secrets
import string
from calendar import monthrange
from datetime import UTC, date, datetime, time, timedelta
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import HTTPException, UploadFile, status as http_status
from sqlalchemy import and_, case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
try:
    from PIL import Image, ImageOps, UnidentifiedImageError
except ImportError:  # pragma: no cover
    Image = None
    ImageOps = None

    class UnidentifiedImageError(Exception):
        pass

from app.core.assessment_type import require_assessment_type
from app.core.config import get_settings
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.timezone import app_timezone, ensure_utc, to_app_timezone
from app.core.security import get_password_hash
from app.db.models.academic import (
    Batch,
    BatchSubject,
    Branch,
    CompletedLecture,
    LectureSchedule,
    Standard,
    StudentBatchEnrollment,
    StudentProfile,
    Subject,
    SubjectAcademicScope,
    TeacherProfile,
)
from app.db.models.parent import ParentProfile, ParentStudentLink
from app.db.models.assessment import Assessment, AssessmentAssignment, AssessmentQuestion
from app.db.models.attendance import AttendanceCorrection, AttendanceRecord
from app.db.models.billing import FeeInvoice, FeeStructure, PaymentTransaction, StudentFeeStructureAssignment
from app.db.models.audit import AuditLog
from app.db.models.content import Banner, DailyThought, Notice, NoticeTarget
from app.db.models.doubt import Doubt, DoubtMessage
from app.db.models.enquiry import StudentEnquiry, StudentEnquiryStatusHistory
from app.db.models.enums import (
    AssessmentStatus,
    AssessmentType,
    AttendanceStatus,
    DoubtStatus,
    HomeworkStatus,
    LectureScheduleStatus,
    NoticeStatus,
    DeliveryChannel,
    NotificationType,
    RegistrationRequestStatus,
    RoleCode,
    UserStatus,
)
from app.db.models.registration import RegistrationRequest
from app.db.models.homework import Homework, HomeworkTarget
from app.db.models.notification import Notification, NotificationDelivery
from app.db.models.results import Result
from app.db.models.user import RefreshSession, Role, StudentCredential, User, UserRole
from app.schemas.admin import (
    AdminAssessmentCreateDTO,
    AdminAttendanceCorrectionApproveDTO,
    AdminAttendanceCorrectionCreateDTO,
    AdminBannerCreateDTO,
    AdminBannerUpdateDTO,
    AdminBatchCreateDTO,
    AdminStandardCreateDTO,
    AdminDailyThoughtUpsertDTO,
    AdminDoubtUpdateDTO,
    AdminFeeStructureCreateDTO,
    AdminFeeStructureUpdateDTO,
    AdminStudentEnquiryCreateDTO,
    AdminStudentEnquiryUpdateDTO,
    AdminStudentFeePaymentCreateDTO,
    AdminFeeOverdueReminderDTO,
    AdminStudentFeeStructureAssignDTO,
    AdminHomeworkCreateDTO,
    AdminNoticeCreateDTO,
    AdminNotificationCreateDTO,
    AdminResultPublishDTO,
    AdminResultWhatsappDTO,
    AdminSubjectCreateDTO,
    AdminStudentCreateDTO,
    AdminStudentUpdateDTO,
    AdminParentLinkCreateDTO,
    AdminSubjectEstimateUpsertDTO,
)


class AdminService:
    _ALLOWED_BANNER_IMAGE_TYPES: dict[str, str] = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    _LOGIN_PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,8}$")
    _LOGIN_PASSWORD_CHARSET = string.ascii_letters + string.digits

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @classmethod
    def _is_valid_login_password(cls, value: str) -> bool:
        return bool(cls._LOGIN_PASSWORD_PATTERN.fullmatch((value or "").strip()))

    @classmethod
    def _generate_login_password(cls, length: int = 8) -> str:
        safe_length = min(8, max(6, int(length)))
        while True:
            candidate = "".join(secrets.choice(cls._LOGIN_PASSWORD_CHARSET) for _ in range(safe_length))
            if any(ch.isalpha() for ch in candidate) and any(ch.isdigit() for ch in candidate):
                return candidate

    @staticmethod
    def _safe_display_name(raw_name: str | None, fallback: str) -> str:
        if not raw_name:
            return fallback
        cleaned = re.sub(r"[^\w\-.() ]+", "_", raw_name).strip()
        return cleaned[:120] or fallback

    async def _upsert_student_credential_snapshot(
        self,
        *,
        user_id: str,
        login_id: str,
        password_plain: str,
        actor_user_id: str | None,
    ) -> None:
        existing = (
            await self.session.execute(
                select(StudentCredential).where(StudentCredential.user_id == user_id)
            )
        ).scalar_one_or_none()

        now = datetime.now(UTC)
        if existing:
            existing.login_id = login_id
            existing.password_plain = password_plain
            existing.password_updated_at = now
            existing.updated_by_user_id = actor_user_id
            return

        self.session.add(
            StudentCredential(
                user_id=user_id,
                login_id=login_id,
                password_plain=password_plain,
                password_updated_at=now,
                updated_by_user_id=actor_user_id,
            )
        )

    @classmethod
    def _normalize_and_crop_banner(cls, payload: bytes) -> tuple[bytes, int, int]:
        if Image is None or ImageOps is None:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Image processing dependency is not installed on server",
            )

        try:
            with Image.open(BytesIO(payload)) as image:
                image = ImageOps.exif_transpose(image)
                if image.mode not in {"RGB", "L"}:
                    image = image.convert("RGB")
                elif image.mode == "L":
                    image = image.convert("RGB")

                source_w, source_h = image.size
                target_ratio = 16 / 9
                source_ratio = source_w / source_h if source_h else target_ratio

                if source_ratio > target_ratio:
                    crop_h = source_h
                    crop_w = int(crop_h * target_ratio)
                    left = (source_w - crop_w) // 2
                    top = 0
                else:
                    crop_w = source_w
                    crop_h = int(crop_w / target_ratio)
                    left = 0
                    top = (source_h - crop_h) // 2

                cropped = image.crop((left, top, left + crop_w, top + crop_h))
                normalized = cropped.resize((1600, 900), Image.Resampling.LANCZOS)

                out = BytesIO()
                normalized.save(
                    out,
                    format="JPEG",
                    quality=85,
                    optimize=True,
                    progressive=True,
                )
                return out.getvalue(), 1600, 900
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Uploaded image is invalid or unsupported",
            ) from exc

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

    async def list_students(
        self,
        *,
        search: str | None,
        status: str | None,
        class_level: int | None,
        stream: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = (
            select(StudentProfile, User, Batch, Standard)
            .join(User, User.id == StudentProfile.user_id)
            .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
            .outerjoin(Standard, Standard.id == Batch.standard_id)
        )

        filters = []
        if search:
            filters.append(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                    User.phone.ilike(f"%{search}%"),
                    StudentProfile.admission_no.ilike(f"%{search}%"),
                )
            )
        if status:
            filters.append(User.status == UserStatus(status))

        if class_level is not None:
            if class_level == 0:
                filters.append(
                    or_(
                        StudentProfile.class_name.ilike("%jr%"),
                        StudentProfile.class_name.ilike("%kg%"),
                        Standard.name.ilike("%jr%"),
                        Standard.name.ilike("%kg%"),
                    )
                )
            else:
                filters.append(
                    or_(
                        StudentProfile.class_name.ilike(f"%{class_level}%"),
                        Standard.name.ilike(f"%{class_level}%"),
                    )
                )

        if stream:
            normalized_stream = self._normalize_stream(stream)
            if class_level in {11, 12}:
                filters.append(StudentProfile.stream.is_not(None))
                filters.append(StudentProfile.stream.ilike(f"%{normalized_stream}%"))
            elif class_level == 10:
                filters.append(or_(StudentProfile.stream.is_(None), StudentProfile.stream == ""))
            else:
                filters.append(StudentProfile.stream.ilike(f"%{normalized_stream}%"))

        if filters:
            query = query.where(and_(*filters))

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

        rows = (
            await self.session.execute(
                query.order_by(User.created_at.desc()).limit(limit).offset(offset)
            )
        ).all()

        items = [
            {
                "student_id": profile.id,
                "user_id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "status": user.status.value if hasattr(user.status, "value") else str(user.status),
                "admission_no": profile.admission_no,
                "roll_no": profile.roll_no,
                "class_name": profile.class_name or (standard.name if standard else None),
                "stream": profile.stream,
                "parent_contact_number": profile.parent_contact_number,
                "address": profile.address,
                "school_details": profile.school_details,
                "batch": {
                    "id": batch.id,
                    "name": batch.name,
                    "academic_year": batch.academic_year,
                    "standard_name": standard.name if standard else None,
                }
                if batch
                else None,
                "admission_date": user.created_at.date().isoformat() if user.created_at else None,
                "created_at": user.created_at,
            }
            for profile, user, batch, standard in rows
        ]
        return items, total

    @staticmethod
    def _extract_grade(class_name: str | None, standard_name: str | None) -> str | None:
        source = f"{class_name or ''} {standard_name or ''}".lower()
        for level in range(12, 0, -1):
            if f"{level}th" in source or f" {level} " in f" {source} ":
                return str(level)
        return None

    @staticmethod
    def _normalize_stream(stream: str | None) -> str:
        value = (stream or "").strip().lower()
        if value in {"science", "sci"}:
            return "science"
        if value in {"commerce", "comm"}:
            return "commerce"
        return "common"

    @staticmethod
    def _normalize_optional_stream(stream: str | None) -> str | None:
        value = (stream or "").strip().lower()
        if not value:
            return None
        if value in {"science", "sci"}:
            return "science"
        if value in {"commerce", "comm"}:
            return "commerce"
        return None

    @staticmethod
    def _derive_class_stream_from_standard_name(standard_name: str | None) -> tuple[str | None, str | None]:
        source = (standard_name or "").lower()
        class_name: str | None = None
        stream: str | None = None

        for level in range(12, 0, -1):
            if f"{level}th" in source or f" {level} " in f" {source} ":
                class_name = f"{level}th"
                break

        if "science" in source:
            stream = "science"
        elif "commerce" in source:
            stream = "commerce"

        if class_name is not None and int(class_name.replace('th', '')) <= 10:
            stream = None

        return class_name, stream

    @staticmethod
    def _to_utc(value: datetime | None) -> datetime | None:
        return ensure_utc(value)

    @staticmethod
    def _to_utc_from_app_input(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=app_timezone()).astimezone(UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _subject_scope_stream(class_level: int, stream: str | None) -> str:
        if class_level == 10:
            return "common"

        normalized = AdminService._normalize_stream(stream)
        if normalized not in {"science", "commerce"}:
            raise ValueError("stream is required for class 11 and 12")
        return normalized

    async def _next_subject_code(self, *, preferred: str) -> str:
        base = preferred.strip().upper() or "SUBJECT"
        # Keep only A-Z, 0-9 and underscore.
        base = re.sub(r"[^A-Z0-9_]+", "_", base).strip("_") or "SUBJECT"

        candidate = base
        index = 2
        while True:
            existing = (
                await self.session.execute(
                    select(Subject.id).where(func.upper(Subject.code) == candidate)
                )
            ).scalar_one_or_none()
            if existing is None:
                return candidate
            candidate = f"{base}_{index}"
            index += 1

    async def student_summary(self) -> dict:
        rows = (
            await self.session.execute(
                select(User.status, StudentProfile.class_name, StudentProfile.stream, Standard.name)
                .join(User, User.id == StudentProfile.user_id)
                .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
                .outerjoin(Standard, Standard.id == Batch.standard_id)
            )
        ).all()

        summary = {
            "total_students": 0,
            "active_students": 0,
            "inactive_students": 0,
            "suspended_students": 0,
            "grade_counts": {
                "10": {"total": 0, "common": 0, "science": 0, "commerce": 0},
                "11": {"total": 0, "common": 0, "science": 0, "commerce": 0},
                "12": {"total": 0, "common": 0, "science": 0, "commerce": 0},
            },
        }

        for status, class_name, stream, standard_name in rows:
            summary["total_students"] += 1
            status_value = status.value if hasattr(status, "value") else str(status)
            if status_value == "active":
                summary["active_students"] += 1
            elif status_value == "inactive":
                summary["inactive_students"] += 1
            elif status_value == "suspended":
                summary["suspended_students"] += 1

            grade = self._extract_grade(class_name, standard_name)
            if grade in summary["grade_counts"]:
                stream_key = self._normalize_stream(stream)
                summary["grade_counts"][grade]["total"] += 1
                summary["grade_counts"][grade][stream_key] += 1

        return summary

    async def list_student_enquiries(
        self,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = (
            select(RegistrationRequest, User, StudentProfile)
            .join(User, User.id == RegistrationRequest.user_id)
            .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
            .where(
                RegistrationRequest.requested_role == RoleCode.STUDENT,
                RegistrationRequest.status == RegistrationRequestStatus.PENDING,
            )
            .order_by(RegistrationRequest.created_at.desc())
        )

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (await self.session.execute(query.limit(limit).offset(offset))).all()

        items = []
        for request, user, profile in rows:
            items.append(
                {
                    "request_id": request.id,
                    "submitted_at": request.created_at,
                    "full_name": user.full_name,
                    "phone": user.phone,
                    "email": user.email,
                    "class_name": profile.class_name if profile else None,
                    "stream": profile.stream if profile else None,
                    "parent_contact_number": profile.parent_contact_number if profile else None,
                    "school_details": profile.school_details if profile else None,
                    "status": request.status.value if hasattr(request.status, "value") else str(request.status),
                }
            )

        return items, total

    async def list_admin_enquiries(
        self,
        *,
        search: str | None,
        status: str | None,
        class_level: int | None,
        fee_class_level: int | None,
        fee_stream: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = select(StudentEnquiry, FeeStructure).outerjoin(
            FeeStructure,
            FeeStructure.id == StudentEnquiry.fee_structure_id,
        )

        normalized_stream = self._normalize_fee_stream(fee_stream)
        filters = []

        if search:
            pattern = f"%{search.strip()}%"
            filters.append(
                or_(
                    StudentEnquiry.student_name.ilike(pattern),
                    StudentEnquiry.contact_number.ilike(pattern),
                    StudentEnquiry.parent_contact_number.ilike(pattern),
                    StudentEnquiry.school_name.ilike(pattern),
                )
            )

        if status:
            filters.append(StudentEnquiry.status == status.strip().lower())

        if class_level is not None:
            filters.append(StudentEnquiry.class_level == class_level)

        if fee_class_level is not None:
            filters.append(StudentEnquiry.fee_class_level == fee_class_level)

        if normalized_stream is not None:
            filters.append(StudentEnquiry.fee_stream == normalized_stream)

        if filters:
            query = query.where(and_(*filters))

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(StudentEnquiry.created_at.desc()).limit(limit).offset(offset)
            )
        ).all()

        items: list[dict] = []
        for enquiry, fee_structure in rows:
            items.append(
                {
                    "enquiry_id": enquiry.id,
                    "student_name": enquiry.student_name,
                    "class_level": enquiry.class_level,
                    "previous_class": enquiry.previous_class,
                    "previous_percentage": float(enquiry.previous_percentage)
                    if enquiry.previous_percentage is not None
                    else None,
                    "school_name": enquiry.school_name,
                    "language": enquiry.language,
                    "contact_number": enquiry.contact_number,
                    "parent_contact_number": enquiry.parent_contact_number,
                    "follow_up_at": enquiry.follow_up_at,
                    "fee_class_level": enquiry.fee_class_level,
                    "fee_stream": enquiry.fee_stream,
                    "fee_structure_id": enquiry.fee_structure_id,
                    "fee_structure_name": fee_structure.name if fee_structure else None,
                    "manual_fee_amount": float(enquiry.manual_fee_amount) if enquiry.manual_fee_amount is not None else None,
                    "manual_fee_installment_count": enquiry.manual_fee_installment_count,
                    "fee_amount": float(enquiry.fee_amount) if enquiry.fee_amount is not None else None,
                    "negotiable_amount": float(enquiry.negotiable_amount) if enquiry.negotiable_amount is not None else None,
                    "installment_count": enquiry.installment_count,
                    "initial_fee_paid_amount": float(enquiry.initial_fee_paid_amount)
                    if enquiry.initial_fee_paid_amount is not None
                    else None,
                    "initial_fee_paid_on": enquiry.initial_fee_paid_on,
                    "initial_fee_payment_mode": enquiry.initial_fee_payment_mode,
                    "initial_fee_reference_no": enquiry.initial_fee_reference_no,
                    "initial_fee_note": enquiry.initial_fee_note,
                    "batch_id": enquiry.batch_id,
                    "converted_student_id": enquiry.converted_student_id,
                    "converted_at": enquiry.converted_at,
                    "status": enquiry.status,
                    "notes": enquiry.notes,
                    "created_by_user_id": enquiry.created_by_user_id,
                    "created_at": enquiry.created_at,
                    "updated_at": enquiry.updated_at,
                }
            )

        return items, total

    async def create_admin_enquiry(
        self,
        *,
        payload: AdminStudentEnquiryCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        normalized_stream = self._normalize_fee_stream(payload.fee_stream)
        self._validate_fee_structure_stream(class_level=payload.fee_class_level, stream=normalized_stream)

        if payload.batch_id:
            await self._resolve_batch_for_enquiry(
                class_level=payload.class_level,
                stream=normalized_stream,
                preferred_batch_id=payload.batch_id,
                require_explicit=True,
            )

        status_value = payload.status.strip().lower()
        if status_value == "confirmed" and not payload.batch_id:
            raise ForbiddenException("Batch allocation is required when enquiry status is Confirmed")

        manual_fee_amount = float(payload.manual_fee_amount or 0)
        if payload.fee_structure_id and manual_fee_amount > 0:
            raise ForbiddenException("Choose either fee structure or manual fee amount")

        fee_structure = None
        if manual_fee_amount <= 0:
            fee_structure = await self._resolve_fee_structure_for_scope(
                fee_class_level=payload.fee_class_level,
                fee_stream=normalized_stream,
                fee_structure_id=payload.fee_structure_id,
            )

        base_fee_amount = manual_fee_amount if manual_fee_amount > 0 else (float(fee_structure.total_amount) if fee_structure else None)
        negotiable_amount = float(payload.negotiable_amount or 0)

        if (
            payload.negotiable_amount is not None
            and base_fee_amount is not None
            and payload.negotiable_amount > base_fee_amount
        ):
            raise ForbiddenException("Negotiable amount cannot exceed selected fee amount")

        fee_amount = negotiable_amount if negotiable_amount > 0 else base_fee_amount

        initial_paid_amount = float(payload.initial_fee_paid_amount or 0)
        if initial_paid_amount > 0 and fee_amount is None:
            raise ForbiddenException("Select fee structure or manual fee amount before recording initial paid amount")
        if fee_amount is not None and initial_paid_amount > fee_amount + 0.0001:
            raise ForbiddenException("Initial paid amount cannot exceed selected fee amount")

        installment_count = payload.installment_count
        if installment_count is None:
            if manual_fee_amount > 0:
                installment_count = payload.manual_fee_installment_count or 3
            elif fee_structure:
                installment_count = fee_structure.installment_count

        enquiry = StudentEnquiry(
            student_name=payload.student_name.strip(),
            class_level=payload.class_level,
            previous_class=(payload.previous_class or "").strip() or None,
            previous_percentage=payload.previous_percentage,
            school_name=(payload.school_name or "").strip() or None,
            language=payload.language.strip().lower(),
            contact_number=payload.contact_number.strip(),
            parent_contact_number=payload.parent_contact_number.strip(),
            follow_up_at=ensure_utc(payload.follow_up_at) if payload.follow_up_at else None,
            batch_id=payload.batch_id,
            fee_class_level=payload.fee_class_level,
            fee_stream=normalized_stream,
            fee_structure_id=fee_structure.id if fee_structure else None,
            manual_fee_amount=manual_fee_amount if manual_fee_amount > 0 else None,
            manual_fee_installment_count=(payload.manual_fee_installment_count or 3) if manual_fee_amount > 0 else None,
            fee_amount=fee_amount,
            negotiable_amount=payload.negotiable_amount if (payload.negotiable_amount or 0) > 0 else None,
            installment_count=installment_count,
            initial_fee_paid_amount=initial_paid_amount if initial_paid_amount > 0 else None,
            initial_fee_paid_on=self._to_utc_from_date(payload.initial_fee_paid_on) if payload.initial_fee_paid_on else None,
            initial_fee_payment_mode=payload.initial_fee_payment_mode if initial_paid_amount > 0 else None,
            initial_fee_reference_no=(payload.initial_fee_reference_no or "").strip() or None,
            initial_fee_note=(payload.initial_fee_note or "").strip() or None,
            status=status_value,
            notes=(payload.notes or "").strip() or None,
            created_by_user_id=actor_user_id,
        )
        self.session.add(enquiry)
        await self.session.flush()
        await self._append_enquiry_status_history(
            enquiry_id=enquiry.id,
            from_status=None,
            to_status=enquiry.status,
            note="Enquiry created",
            actor_user_id=actor_user_id,
        )

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.enquiry.create",
            entity_type="student_enquiry",
            entity_id=enquiry.id,
            before_state=None,
            after_state={
                "student_name": enquiry.student_name,
                "class_level": enquiry.class_level,
                "fee_class_level": enquiry.fee_class_level,
                "fee_stream": enquiry.fee_stream,
                "fee_structure_id": enquiry.fee_structure_id,
                "manual_fee_amount": float(enquiry.manual_fee_amount) if enquiry.manual_fee_amount is not None else None,
                "fee_amount": float(enquiry.fee_amount) if enquiry.fee_amount is not None else None,
                "negotiable_amount": float(enquiry.negotiable_amount) if enquiry.negotiable_amount is not None else None,
                "installment_count": enquiry.installment_count,
                "initial_fee_paid_amount": float(enquiry.initial_fee_paid_amount)
                if enquiry.initial_fee_paid_amount is not None
                else None,
                "status": enquiry.status,
            },
            ip_address=ip_address,
        )

        await self.session.commit()
        await self.session.refresh(enquiry)

        if enquiry.status == "confirmed" and not enquiry.converted_student_id:
            return await self.update_admin_enquiry(
                enquiry_id=enquiry.id,
                payload=AdminStudentEnquiryUpdateDTO(status="confirmed"),
                actor_user_id=actor_user_id,
                ip_address=ip_address,
            )

        installment_preview = (
            self._build_three_installment_preview(
                total_fee=float(enquiry.fee_amount),
                paid_amount=float(enquiry.initial_fee_paid_amount or 0),
            )
            if enquiry.fee_amount is not None
            else None
        )

        return {
            "enquiry_id": enquiry.id,
            "student_name": enquiry.student_name,
            "class_level": enquiry.class_level,
            "fee_class_level": enquiry.fee_class_level,
            "fee_stream": enquiry.fee_stream,
            "fee_structure_id": enquiry.fee_structure_id,
            "manual_fee_amount": float(enquiry.manual_fee_amount) if enquiry.manual_fee_amount is not None else None,
            "manual_fee_installment_count": enquiry.manual_fee_installment_count,
            "fee_amount": float(enquiry.fee_amount) if enquiry.fee_amount is not None else None,
            "negotiable_amount": float(enquiry.negotiable_amount) if enquiry.negotiable_amount is not None else None,
            "installment_count": enquiry.installment_count,
            "initial_fee_paid_amount": float(enquiry.initial_fee_paid_amount)
            if enquiry.initial_fee_paid_amount is not None
            else None,
            "initial_fee_paid_on": enquiry.initial_fee_paid_on,
            "initial_fee_payment_mode": enquiry.initial_fee_payment_mode,
            "initial_fee_reference_no": enquiry.initial_fee_reference_no,
            "batch_id": enquiry.batch_id,
            "status": enquiry.status,
            "follow_up_at": enquiry.follow_up_at,
            "installment_preview": installment_preview,
            "created_at": enquiry.created_at,
        }

    async def update_admin_enquiry(
        self,
        *,
        enquiry_id: str,
        payload: AdminStudentEnquiryUpdateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        enquiry = await self.session.get(StudentEnquiry, enquiry_id)
        if not enquiry:
            raise NotFoundException("Enquiry not found")
        fields_set = payload.model_fields_set

        before_state = {
            "student_name": enquiry.student_name,
            "class_level": enquiry.class_level,
            "fee_class_level": enquiry.fee_class_level,
            "fee_stream": enquiry.fee_stream,
            "fee_structure_id": enquiry.fee_structure_id,
            "manual_fee_amount": float(enquiry.manual_fee_amount) if enquiry.manual_fee_amount is not None else None,
            "fee_amount": float(enquiry.fee_amount) if enquiry.fee_amount is not None else None,
            "negotiable_amount": float(enquiry.negotiable_amount) if enquiry.negotiable_amount is not None else None,
            "installment_count": enquiry.installment_count,
            "initial_fee_paid_amount": float(enquiry.initial_fee_paid_amount)
            if enquiry.initial_fee_paid_amount is not None
            else None,
            "status": enquiry.status,
            "follow_up_at": enquiry.follow_up_at.isoformat() if enquiry.follow_up_at else None,
            "converted_student_id": enquiry.converted_student_id,
        }

        if "student_name" in fields_set and payload.student_name is not None:
            enquiry.student_name = payload.student_name.strip()
        if "class_level" in fields_set and payload.class_level is not None:
            enquiry.class_level = payload.class_level
        if "previous_class" in fields_set:
            enquiry.previous_class = (payload.previous_class or "").strip() or None
        if "previous_percentage" in fields_set:
            enquiry.previous_percentage = payload.previous_percentage
        if "school_name" in fields_set:
            enquiry.school_name = (payload.school_name or "").strip() or None
        if "language" in fields_set and payload.language is not None:
            enquiry.language = payload.language.strip().lower()
        if "contact_number" in fields_set and payload.contact_number is not None:
            enquiry.contact_number = payload.contact_number.strip()
        if "parent_contact_number" in fields_set and payload.parent_contact_number is not None:
            enquiry.parent_contact_number = payload.parent_contact_number.strip()
        if "follow_up_at" in fields_set:
            enquiry.follow_up_at = ensure_utc(payload.follow_up_at) if payload.follow_up_at else None
        if "batch_id" in fields_set:
            enquiry.batch_id = payload.batch_id

        merged_fee_class_level = payload.fee_class_level if "fee_class_level" in fields_set and payload.fee_class_level is not None else enquiry.fee_class_level
        merged_fee_stream = (
            self._normalize_fee_stream(payload.fee_stream)
            if "fee_stream" in fields_set
            else self._normalize_fee_stream(enquiry.fee_stream)
        )
        self._validate_fee_structure_stream(class_level=merged_fee_class_level, stream=merged_fee_stream)

        if enquiry.batch_id:
            await self._resolve_batch_for_enquiry(
                class_level=enquiry.class_level,
                stream=merged_fee_stream,
                preferred_batch_id=enquiry.batch_id,
                require_explicit=True,
            )

        merged_manual_fee_amount = (
            float(payload.manual_fee_amount or 0)
            if "manual_fee_amount" in fields_set
            else float(enquiry.manual_fee_amount or 0)
        )
        merged_fee_structure_id = payload.fee_structure_id if "fee_structure_id" in fields_set else enquiry.fee_structure_id

        if merged_fee_structure_id and merged_manual_fee_amount > 0:
            raise ForbiddenException("Choose either fee structure or manual fee amount")

        fee_structure = None
        if merged_manual_fee_amount <= 0:
            fee_structure = await self._resolve_fee_structure_for_scope(
                fee_class_level=merged_fee_class_level,
                fee_stream=merged_fee_stream,
                fee_structure_id=merged_fee_structure_id,
            )

        base_fee_amount = merged_manual_fee_amount if merged_manual_fee_amount > 0 else (float(fee_structure.total_amount) if fee_structure else None)
        merged_negotiable_amount = (
            float(payload.negotiable_amount or 0)
            if "negotiable_amount" in fields_set
            else float(enquiry.negotiable_amount or 0)
        )

        if merged_negotiable_amount > 0 and base_fee_amount is None:
            raise ForbiddenException("Select fee structure or manual fee amount before entering negotiable amount")
        if base_fee_amount is not None and merged_negotiable_amount > base_fee_amount + 0.0001:
            raise ForbiddenException("Negotiable amount cannot exceed selected fee amount")

        fee_amount = merged_negotiable_amount if merged_negotiable_amount > 0 else base_fee_amount

        enquiry.fee_class_level = merged_fee_class_level
        enquiry.fee_stream = merged_fee_stream
        enquiry.fee_structure_id = fee_structure.id if fee_structure else None
        enquiry.manual_fee_amount = merged_manual_fee_amount if merged_manual_fee_amount > 0 else None
        if merged_manual_fee_amount > 0:
            if "manual_fee_installment_count" in fields_set:
                enquiry.manual_fee_installment_count = payload.manual_fee_installment_count or 3
            elif enquiry.manual_fee_installment_count is None:
                enquiry.manual_fee_installment_count = 3
        elif "manual_fee_installment_count" in fields_set:
            enquiry.manual_fee_installment_count = None
        enquiry.fee_amount = fee_amount
        enquiry.negotiable_amount = merged_negotiable_amount if merged_negotiable_amount > 0 else None

        if "installment_count" in fields_set:
            enquiry.installment_count = payload.installment_count
        elif enquiry.installment_count is None:
            if merged_manual_fee_amount > 0:
                enquiry.installment_count = enquiry.manual_fee_installment_count or 3
            elif fee_structure:
                enquiry.installment_count = fee_structure.installment_count

        if "initial_fee_paid_amount" in fields_set:
            enquiry.initial_fee_paid_amount = payload.initial_fee_paid_amount
        if "initial_fee_paid_on" in fields_set:
            enquiry.initial_fee_paid_on = self._to_utc_from_date(payload.initial_fee_paid_on) if payload.initial_fee_paid_on else None
        if "initial_fee_payment_mode" in fields_set:
            enquiry.initial_fee_payment_mode = payload.initial_fee_payment_mode
        if "initial_fee_reference_no" in fields_set:
            enquiry.initial_fee_reference_no = (payload.initial_fee_reference_no or "").strip() or None
        if "initial_fee_note" in fields_set:
            enquiry.initial_fee_note = (payload.initial_fee_note or "").strip() or None

        initial_paid_amount = float(enquiry.initial_fee_paid_amount or 0)
        if initial_paid_amount > 0 and fee_amount is None:
            raise ForbiddenException("Select fee structure or manual fee amount before recording initial paid amount")
        if fee_amount is not None and initial_paid_amount > fee_amount + 0.0001:
            raise ForbiddenException("Initial paid amount cannot exceed selected fee amount")

        status_before = enquiry.status
        if "status" in fields_set and payload.status is not None:
            enquiry.status = payload.status.strip().lower()
        if "notes" in fields_set:
            enquiry.notes = (payload.notes or "").strip() or None

        if enquiry.status == "confirmed" and not enquiry.batch_id:
            raise ForbiddenException("Batch allocation is required when enquiry status is Confirmed")

        await self.session.flush()

        status_changed = enquiry.status != status_before
        status_note = ((payload.status_note or "").strip() or None) if "status_note" in fields_set else None
        if status_changed or status_note:
            await self._append_enquiry_status_history(
                enquiry_id=enquiry.id,
                from_status=status_before,
                to_status=enquiry.status,
                note=status_note or ("Status changed" if status_changed else "Enquiry note"),
                actor_user_id=actor_user_id,
            )

        conversion = None
        generated_password = None
        if enquiry.status == "confirmed" and not enquiry.converted_student_id:
            if not enquiry.batch_id:
                raise ForbiddenException("Batch allocation is required when enquiry status is Confirmed")
            batch_id = await self._resolve_batch_for_enquiry(
                class_level=enquiry.class_level,
                stream=enquiry.fee_stream,
                preferred_batch_id=enquiry.batch_id,
                require_explicit=True,
            )
            generated_password = self._generate_login_password()
            admission_no = await self._generate_unique_admission_no(prefix="ENQ")
            roll_no = self._build_roll_no_from_contact(enquiry.contact_number)

            student_payload = AdminStudentCreateDTO(
                full_name=enquiry.student_name,
                email=None,
                phone=enquiry.contact_number,
                password=generated_password,
                admission_no=admission_no,
                roll_no=roll_no,
                batch_id=batch_id,
                class_name=f"{enquiry.class_level}th",
                stream=None if enquiry.class_level == 10 else enquiry.fee_stream,
                parent_contact_number=enquiry.parent_contact_number,
                address=None,
                school_details=enquiry.school_name,
                fee_structure_id=enquiry.fee_structure_id,
                manual_fee_amount=float(enquiry.manual_fee_amount or 0) or None,
                manual_fee_installment_count=enquiry.manual_fee_installment_count or 3,
                negotiable_amount=float(enquiry.negotiable_amount or 0) or None,
                installment_count=enquiry.installment_count,
                initial_fee_paid_amount=float(enquiry.initial_fee_paid_amount or 0) or None,
                initial_fee_paid_on=enquiry.initial_fee_paid_on.date() if enquiry.initial_fee_paid_on else None,
                initial_fee_payment_mode=enquiry.initial_fee_payment_mode or "cash",
                initial_fee_reference_no=enquiry.initial_fee_reference_no,
                initial_fee_note=enquiry.initial_fee_note,
            )
            conversion = await self.create_student(
                payload=student_payload,
                actor_user_id=actor_user_id,
                ip_address=ip_address,
            )
            enquiry = await self.session.get(StudentEnquiry, enquiry_id)
            if not enquiry:
                raise NotFoundException("Enquiry not found after conversion")
            enquiry.converted_student_id = conversion["student_id"]
            enquiry.converted_at = datetime.now(UTC)

        after_state = {
            "student_name": enquiry.student_name,
            "class_level": enquiry.class_level,
            "fee_class_level": enquiry.fee_class_level,
            "fee_stream": enquiry.fee_stream,
            "fee_structure_id": enquiry.fee_structure_id,
            "manual_fee_amount": float(enquiry.manual_fee_amount) if enquiry.manual_fee_amount is not None else None,
            "fee_amount": float(enquiry.fee_amount) if enquiry.fee_amount is not None else None,
            "negotiable_amount": float(enquiry.negotiable_amount) if enquiry.negotiable_amount is not None else None,
            "installment_count": enquiry.installment_count,
            "initial_fee_paid_amount": float(enquiry.initial_fee_paid_amount)
            if enquiry.initial_fee_paid_amount is not None
            else None,
            "status": enquiry.status,
            "follow_up_at": enquiry.follow_up_at.isoformat() if enquiry.follow_up_at else None,
            "converted_student_id": enquiry.converted_student_id,
        }

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.enquiry.update",
            entity_type="student_enquiry",
            entity_id=enquiry.id,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
        )

        await self.session.commit()
        await self.session.refresh(enquiry)

        installment_preview = (
            self._build_three_installment_preview(
                total_fee=float(enquiry.fee_amount),
                paid_amount=float(enquiry.initial_fee_paid_amount or 0),
            )
            if enquiry.fee_amount is not None
            else None
        )

        response = {
            "enquiry_id": enquiry.id,
            "student_name": enquiry.student_name,
            "class_level": enquiry.class_level,
            "fee_class_level": enquiry.fee_class_level,
            "fee_stream": enquiry.fee_stream,
            "fee_structure_id": enquiry.fee_structure_id,
            "manual_fee_amount": float(enquiry.manual_fee_amount) if enquiry.manual_fee_amount is not None else None,
            "manual_fee_installment_count": enquiry.manual_fee_installment_count,
            "fee_amount": float(enquiry.fee_amount) if enquiry.fee_amount is not None else None,
            "negotiable_amount": float(enquiry.negotiable_amount) if enquiry.negotiable_amount is not None else None,
            "installment_count": enquiry.installment_count,
            "initial_fee_paid_amount": float(enquiry.initial_fee_paid_amount)
            if enquiry.initial_fee_paid_amount is not None
            else None,
            "initial_fee_paid_on": enquiry.initial_fee_paid_on,
            "initial_fee_payment_mode": enquiry.initial_fee_payment_mode,
            "initial_fee_reference_no": enquiry.initial_fee_reference_no,
            "status": enquiry.status,
            "follow_up_at": enquiry.follow_up_at,
            "converted_student_id": enquiry.converted_student_id,
            "converted_at": enquiry.converted_at,
            "installment_preview": installment_preview,
            "updated_at": enquiry.updated_at,
        }
        if conversion is not None:
            response["conversion"] = {
                "student_id": conversion["student_id"],
                "user_id": conversion["user_id"],
                "generated_password": generated_password,
            }
        return response

    async def list_enquiry_timeline(self, *, enquiry_id: str, limit: int, offset: int) -> tuple[list[dict], int]:
        enquiry = await self.session.get(StudentEnquiry, enquiry_id)
        if not enquiry:
            raise NotFoundException("Enquiry not found")

        changed_by = aliased(User)
        query = (
            select(StudentEnquiryStatusHistory, changed_by)
            .outerjoin(changed_by, changed_by.id == StudentEnquiryStatusHistory.changed_by_user_id)
            .where(StudentEnquiryStatusHistory.enquiry_id == enquiry_id)
            .order_by(StudentEnquiryStatusHistory.changed_at.desc())
        )
        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (await self.session.execute(query.limit(limit).offset(offset))).all()

        items = [
            {
                "timeline_id": entry.id,
                "enquiry_id": entry.enquiry_id,
                "from_status": entry.from_status,
                "to_status": entry.to_status,
                "note": entry.note,
                "changed_at": entry.changed_at,
                "changed_by_user_id": entry.changed_by_user_id,
                "changed_by_name": user.full_name if user else None,
            }
            for entry, user in rows
        ]
        return items, total

    async def _resolve_fee_structure_for_scope(
        self,
        *,
        fee_class_level: int,
        fee_stream: str | None,
        fee_structure_id: str | None,
    ) -> FeeStructure | None:
        self._validate_fee_structure_stream(class_level=fee_class_level, stream=fee_stream)
        if fee_structure_id:
            fee_structure = await self.session.get(FeeStructure, fee_structure_id)
            if not fee_structure:
                raise NotFoundException("Fee structure not found")
            if not fee_structure.is_active:
                raise ForbiddenException("Selected fee structure is inactive")
            if fee_structure.class_level != fee_class_level:
                raise ForbiddenException("Selected fee structure class does not match selected fee class")
            structure_stream = self._normalize_fee_stream(fee_structure.stream)
            if fee_class_level in {11, 12} and structure_stream != fee_stream:
                raise ForbiddenException("Selected fee structure stream does not match selected fee stream")
            if fee_class_level == 10 and structure_stream is not None:
                raise ForbiddenException("Class 10 enquiry cannot use stream-based fee structure")
            return fee_structure

        stream_filter = FeeStructure.stream.is_(None) if fee_stream is None else FeeStructure.stream == fee_stream
        return (
            await self.session.execute(
                select(FeeStructure)
                .where(
                    FeeStructure.class_level == fee_class_level,
                    stream_filter,
                    FeeStructure.is_active.is_(True),
                )
                .order_by(FeeStructure.updated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def _append_enquiry_status_history(
        self,
        *,
        enquiry_id: str,
        from_status: str | None,
        to_status: str,
        note: str | None,
        actor_user_id: str | None,
    ) -> None:
        self.session.add(
            StudentEnquiryStatusHistory(
                enquiry_id=enquiry_id,
                from_status=from_status,
                to_status=to_status,
                note=note,
                changed_by_user_id=actor_user_id,
                changed_at=datetime.now(UTC),
            )
        )

    @staticmethod
    def _to_utc_from_date(value: date | None) -> datetime | None:
        if value is None:
            return None
        return datetime(value.year, value.month, value.day, tzinfo=UTC)

    @staticmethod
    def _build_roll_no_from_contact(contact_number: str | None) -> str:
        digits = "".join(ch for ch in (contact_number or "") if ch.isdigit())
        if not digits:
            return "PENDING"
        return f"R{digits[-6:]}"

    async def _generate_unique_admission_no(self, *, prefix: str = "ADM") -> str:
        for _ in range(20):
            candidate = f"{prefix}-{uuid4().hex[:8].upper()}"
            exists = (
                await self.session.execute(
                    select(StudentProfile.id).where(StudentProfile.admission_no == candidate)
                )
            ).scalar_one_or_none()
            if exists is None:
                return candidate
        return f"{prefix}-{uuid4().hex.upper()}"

    async def _resolve_batch_for_enquiry(
        self,
        *,
        class_level: int,
        stream: str | None,
        preferred_batch_id: str | None,
        require_explicit: bool = False,
    ) -> str:
        normalized_stream = self._normalize_fee_stream(stream)

        def _matches_standard(name: str | None, require_stream: bool) -> bool:
            source = (name or "").lower()
            if str(class_level) not in source:
                return False
            if class_level in {11, 12} and require_stream:
                return normalized_stream in {"science", "commerce"} and (normalized_stream in source)
            return True

        if preferred_batch_id:
            row = (
                await self.session.execute(
                    select(Batch, Standard)
                    .join(Standard, Standard.id == Batch.standard_id)
                    .where(Batch.id == preferred_batch_id)
                )
            ).first()
            if row is None:
                raise NotFoundException("Selected batch for enquiry does not exist")
            batch, standard = row
            if not _matches_standard(standard.name if standard else None, True):
                raise ForbiddenException("Selected batch does not match selected class/stream")
            return batch.id

        if require_explicit:
            raise ForbiddenException("Batch allocation is required when enquiry status is Confirmed")

        rows = (
            await self.session.execute(
                select(Batch, Standard)
                .join(Standard, Standard.id == Batch.standard_id)
                .order_by(Batch.academic_year.desc(), Batch.created_at.desc())
            )
        ).all()

        for batch, standard in rows:
            if _matches_standard(standard.name if standard else None, True):
                return batch.id

        for batch, standard in rows:
            if _matches_standard(standard.name if standard else None, False):
                return batch.id

        raise ForbiddenException(
            f"No batch found for class {class_level}{' ' + (normalized_stream or '') if class_level in {11, 12} else ''}."
        )

    @staticmethod
    def _build_three_installment_preview(*, total_fee: float, paid_amount: float) -> dict:
        safe_total = round(max(total_fee, 0), 2)
        first = round(min(max(paid_amount, 0), safe_total), 2)
        remaining = round(max(safe_total - first, 0), 2)
        second = round(remaining / 2, 2)
        third = round(max(remaining - second, 0), 2)
        return {
            "total_fee": safe_total,
            "paid_amount": first,
            "first_installment": first,
            "second_installment": second,
            "third_installment": third,
            "remaining_after_paid": remaining,
        }

    async def _create_manual_fee_structure(
        self,
        *,
        class_level: int,
        stream: str | None,
        total_amount: float,
        installment_count: int,
        actor_user_id: str,
        student_label: str,
    ) -> FeeStructure:
        suffix = uuid4().hex[:6].upper()
        compact_name = re.sub(r"\s+", " ", (student_label or "Student").strip())[:40]
        structure = FeeStructure(
            name=f"Manual-{class_level}-{compact_name}-{suffix}",
            class_level=class_level,
            stream=stream if class_level in {11, 12} else None,
            total_amount=total_amount,
            installment_count=max(1, min(24, installment_count)),
            description="Auto-generated manual fee structure for student onboarding",
            is_active=True,
        )
        self.session.add(structure)
        await self.session.flush()

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.fee_structure.create_manual",
            entity_type="fee_structure",
            entity_id=structure.id,
            before_state=None,
            after_state={
                "name": structure.name,
                "class_level": structure.class_level,
                "stream": structure.stream,
                "total_amount": float(structure.total_amount),
                "installment_count": structure.installment_count,
                "source": "student_onboarding_manual",
            },
            ip_address=None,
        )
        return structure

    async def _load_subject_maps_for_students(
        self,
        *,
        batch_ids: set[str],
        class_stream_pairs: set[tuple[int, str]],
    ) -> tuple[dict[str, list[str]], dict[tuple[int, str], list[str]]]:
        batch_subjects: dict[str, list[str]] = {}
        if batch_ids:
            rows = (
                await self.session.execute(
                    select(BatchSubject.batch_id, Subject.name)
                    .join(Subject, Subject.id == BatchSubject.subject_id)
                    .where(BatchSubject.batch_id.in_(batch_ids))
                    .order_by(Subject.name.asc())
                )
            ).all()
            for batch_id, subject_name in rows:
                bucket = batch_subjects.setdefault(batch_id, [])
                if subject_name not in bucket:
                    bucket.append(subject_name)

        scope_subjects: dict[tuple[int, str], list[str]] = {}
        if class_stream_pairs:
            scope_filters = [
                and_(
                    SubjectAcademicScope.class_level == class_level,
                    SubjectAcademicScope.stream == stream,
                )
                for class_level, stream in class_stream_pairs
            ]
            rows = (
                await self.session.execute(
                    select(SubjectAcademicScope.class_level, SubjectAcademicScope.stream, Subject.name)
                    .join(Subject, Subject.id == SubjectAcademicScope.subject_id)
                    .where(or_(*scope_filters))
                    .order_by(Subject.name.asc())
                )
            ).all()
            for class_level, stream, subject_name in rows:
                key = (int(class_level), str(stream))
                bucket = scope_subjects.setdefault(key, [])
                if subject_name not in bucket:
                    bucket.append(subject_name)

        return batch_subjects, scope_subjects

    async def list_student_details(
        self,
        *,
        search: str | None,
        status: str | None,
        class_level: int | None,
        stream: str | None,
        student_id: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        payment_rollup = self._student_payment_rollup_subquery()

        attendance_rollup = (
            select(
                AttendanceRecord.student_id.label("student_id"),
                func.count(AttendanceRecord.id).label("total_sessions"),
                func.coalesce(
                    func.sum(case((AttendanceRecord.status == AttendanceStatus.PRESENT, 1), else_=0)),
                    0,
                ).label("present_sessions"),
            )
            .group_by(AttendanceRecord.student_id)
            .subquery()
        )

        result_rollup = (
            select(
                Result.student_id.label("student_id"),
                func.count(Result.id).label("tests_taken"),
                func.coalesce(func.sum(Result.score), 0).label("scored_marks"),
                func.coalesce(func.sum(Result.total_marks), 0).label("total_marks"),
                func.max(Result.published_at).label("last_result_at"),
            )
            .group_by(Result.student_id)
            .subquery()
        )

        query = (
            select(
                StudentProfile,
                User,
                Batch,
                Standard,
                StudentFeeStructureAssignment.id.label("assignment_id"),
                FeeStructure.id.label("fee_structure_id"),
                FeeStructure.name.label("fee_structure_name"),
                FeeStructure.total_amount.label("fee_structure_amount"),
                FeeStructure.installment_count.label("fee_structure_installment_count"),
                func.coalesce(payment_rollup.c.paid_amount, 0).label("paid_amount"),
                payment_rollup.c.last_paid_at.label("last_paid_at"),
                func.coalesce(attendance_rollup.c.total_sessions, 0).label("attendance_total_sessions"),
                func.coalesce(attendance_rollup.c.present_sessions, 0).label("attendance_present_sessions"),
                func.coalesce(result_rollup.c.tests_taken, 0).label("tests_taken"),
                func.coalesce(result_rollup.c.scored_marks, 0).label("scored_marks"),
                func.coalesce(result_rollup.c.total_marks, 0).label("result_total_marks"),
                result_rollup.c.last_result_at.label("last_result_at"),
            )
            .join(User, User.id == StudentProfile.user_id)
            .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
            .outerjoin(Standard, Standard.id == Batch.standard_id)
            .outerjoin(
                StudentFeeStructureAssignment,
                and_(
                    StudentFeeStructureAssignment.student_id == StudentProfile.id,
                    StudentFeeStructureAssignment.is_active.is_(True),
                ),
            )
            .outerjoin(FeeStructure, FeeStructure.id == StudentFeeStructureAssignment.fee_structure_id)
            .outerjoin(payment_rollup, payment_rollup.c.student_id == StudentProfile.id)
            .outerjoin(attendance_rollup, attendance_rollup.c.student_id == StudentProfile.id)
            .outerjoin(result_rollup, result_rollup.c.student_id == StudentProfile.id)
        )

        filters = []
        if student_id:
            filters.append(StudentProfile.id == student_id)
        if search:
            filters.append(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                    User.phone.ilike(f"%{search}%"),
                    StudentProfile.admission_no.ilike(f"%{search}%"),
                    StudentProfile.parent_contact_number.ilike(f"%{search}%"),
                )
            )
        if status:
            filters.append(User.status == UserStatus(status))
        if class_level is not None:
            filters.append(
                or_(
                    StudentProfile.class_name.ilike(f"%{class_level}%"),
                    Standard.name.ilike(f"%{class_level}%"),
                )
            )
        normalized_stream = self._normalize_fee_stream(stream)
        if normalized_stream:
            filters.append(StudentProfile.stream.ilike(f"%{normalized_stream}%"))

        if filters:
            query = query.where(and_(*filters))

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(query.order_by(User.full_name.asc()).limit(limit).offset(offset))
        ).all()

        batch_ids: set[str] = set()
        class_stream_pairs: set[tuple[int, str]] = set()
        for profile, _, _, standard, *_ in rows:
            if profile.current_batch_id:
                batch_ids.add(profile.current_batch_id)

            grade = self._extract_grade(profile.class_name, standard.name if standard else None)
            if grade is None:
                continue
            class_level_value = int(grade)
            normalized_student_stream = self._normalize_fee_stream(profile.stream)
            if class_level_value == 10:
                stream_value = "common"
            else:
                stream_value = normalized_student_stream or "common"
            class_stream_pairs.add((class_level_value, stream_value))

        batch_subjects, scope_subjects = await self._load_subject_maps_for_students(
            batch_ids=batch_ids,
            class_stream_pairs=class_stream_pairs,
        )

        items: list[dict] = []
        for (
            profile,
            user,
            batch,
            standard,
            assignment_id,
            fee_structure_id,
            fee_structure_name,
            fee_structure_amount,
            fee_structure_installment_count,
            paid_amount_raw,
            last_paid_at,
            attendance_total_sessions_raw,
            attendance_present_sessions_raw,
            tests_taken_raw,
            scored_marks_raw,
            result_total_marks_raw,
            last_result_at,
        ) in rows:
            class_name = profile.class_name or (standard.name if standard else None)
            grade = self._extract_grade(profile.class_name, standard.name if standard else None)
            class_level_value = int(grade) if grade is not None else None

            normalized_student_stream = self._normalize_fee_stream(profile.stream)
            if class_level_value == 10:
                stream_for_lookup = "common"
            else:
                stream_for_lookup = normalized_student_stream or "common"

            if profile.current_batch_id and profile.current_batch_id in batch_subjects:
                subjects = batch_subjects[profile.current_batch_id]
            elif class_level_value is not None:
                subjects = scope_subjects.get((class_level_value, stream_for_lookup), [])
            else:
                subjects = []

            fee_amount = float(fee_structure_amount) if fee_structure_amount is not None else None
            paid_amount_raw_float = float(paid_amount_raw or 0)
            paid_amount, pending_amount, is_fully_paid = self._compute_fee_progress(
                fee_amount=fee_amount,
                paid_amount=paid_amount_raw_float,
            )
            fee_status = "not_assigned"
            if fee_amount is not None:
                fee_status = "paid" if is_fully_paid else "pending"

            attendance_total_sessions = int(attendance_total_sessions_raw or 0)
            attendance_present_sessions = int(attendance_present_sessions_raw or 0)
            attendance_percentage = (
                round((attendance_present_sessions / attendance_total_sessions) * 100, 2)
                if attendance_total_sessions > 0
                else 0.0
            )

            tests_taken = int(tests_taken_raw or 0)
            scored_marks = float(scored_marks_raw or 0)
            result_total_marks = float(result_total_marks_raw or 0)
            progress_percentage = round((scored_marks / result_total_marks) * 100, 2) if result_total_marks > 0 else 0.0

            items.append(
                {
                    "student_id": profile.id,
                    "user_id": user.id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "phone": user.phone,
                    "status": user.status.value if hasattr(user.status, "value") else str(user.status),
                    "admission_no": profile.admission_no,
                    "roll_no": profile.roll_no,
                    "class_name": class_name,
                    "class_level": class_level_value,
                    "stream": self._stream_for_display(class_level_value, profile.stream),
                    "parent_contact_number": profile.parent_contact_number,
                    "subjects": subjects,
                    "progress": {
                        "tests_taken": tests_taken,
                        "scored_marks": scored_marks,
                        "total_marks": result_total_marks,
                        "percentage": progress_percentage,
                        "last_result_at": last_result_at.isoformat() if last_result_at else None,
                    },
                    "attendance": {
                        "present_sessions": attendance_present_sessions,
                        "total_sessions": attendance_total_sessions,
                        "percentage": attendance_percentage,
                    },
                    "fee": {
                        "fee_structure_assigned": assignment_id is not None,
                        "fee_structure_id": fee_structure_id,
                        "fee_structure_name": fee_structure_name,
                        "installment_target_count": int(fee_structure_installment_count)
                        if fee_structure_installment_count
                        else None,
                        "total_amount": float(fee_amount or 0),
                        "paid_amount": paid_amount,
                        "pending_amount": pending_amount,
                        "status": fee_status,
                        "is_fully_paid": is_fully_paid,
                        "last_paid_at": last_paid_at.isoformat() if last_paid_at else None,
                    },
                    "batch": {
                        "id": batch.id,
                        "name": batch.name,
                        "academic_year": batch.academic_year,
                        "standard_name": standard.name if standard else None,
                    }
                    if batch
                    else None,
                }
            )

        return items, total

    async def get_student_report_card(self, *, student_id: str) -> dict:
        items, total = await self.list_student_details(
            search=None,
            status=None,
            class_level=None,
            stream=None,
            student_id=student_id,
            limit=1,
            offset=0,
        )
        if total == 0 or len(items) == 0:
            raise NotFoundException("Student not found")

        detail = items[0]
        generated_at = datetime.now(app_timezone())
        media_dir, media_url = self._media_config()
        report_dir = media_dir / "report_cards"
        report_dir.mkdir(parents=True, exist_ok=True)

        file_name = f"REPORT-CARD-{student_id[:6].upper()}-{generated_at.strftime('%Y%m%d%H%M%S')}.pdf"
        file_path = report_dir / file_name
        download_url = f"{media_url}/report_cards/{file_name}"

        result_rows = (
            await self.session.execute(
                select(Subject.name, Assessment.title, Result.score, Result.total_marks, Result.published_at)
                .join(Assessment, Assessment.id == Result.assessment_id)
                .join(Subject, Subject.id == Assessment.subject_id)
                .where(Result.student_id == student_id)
                .order_by(Result.published_at.desc(), Result.created_at.desc())
                .limit(120)
            )
        ).all()

        subject_rollups: dict[str, dict[str, float]] = {}
        recent_results: list[dict[str, str | float]] = []
        for subject_name, assessment_title, score, total_marks, published_at in result_rows:
            subject_label = str(subject_name or "-")
            score_value = float(score or 0)
            total_value = float(total_marks or 0)
            percentage = round((score_value / total_value) * 100, 2) if total_value > 0 else 0.0

            bucket = subject_rollups.setdefault(
                subject_label,
                {"attempts": 0.0, "percentage_sum": 0.0, "best_percentage": 0.0},
            )
            bucket["attempts"] += 1.0
            bucket["percentage_sum"] += percentage
            bucket["best_percentage"] = max(bucket["best_percentage"], percentage)

            if len(recent_results) < 8:
                display_date = "-"
                published_utc = ensure_utc(published_at)
                if published_utc:
                    display_date = published_utc.astimezone(app_timezone()).strftime("%d-%b-%Y")
                recent_results.append(
                    {
                        "subject": subject_label,
                        "title": str(assessment_title or "Assessment"),
                        "percentage": percentage,
                        "date": display_date,
                    }
                )

        subject_performance: list[dict[str, float | int | str]] = []
        for subject, values in subject_rollups.items():
            attempts = int(values["attempts"])
            avg = round(values["percentage_sum"] / attempts, 2) if attempts > 0 else 0.0
            subject_performance.append(
                {
                    "subject": subject,
                    "attempts": attempts,
                    "average_percentage": avg,
                    "best_percentage": round(values["best_percentage"], 2),
                }
            )
        subject_performance.sort(key=lambda row: float(row["average_percentage"]), reverse=True)

        settings = get_settings()
        file_path.write_bytes(
            self._build_report_card_pdf(
                institute_name=settings.institute_display_name,
                generated_at=generated_at,
                detail=detail,
                subject_performance=subject_performance,
                recent_results=recent_results,
            )
        )

        return {
            "student_id": detail["student_id"],
            "student": detail,
            "report_card": {
                "file_name": file_name,
                "download_url": download_url,
                "generated_at": generated_at.isoformat(),
            },
        }

    async def get_student_full_profile(self, *, student_id: str) -> dict:
        items, total = await self.list_student_details(
            search=None,
            status=None,
            class_level=None,
            stream=None,
            student_id=student_id,
            limit=1,
            offset=0,
        )
        if total == 0 or len(items) == 0:
            raise NotFoundException("Student not found")

        student = items[0]

        result_rows = (
            await self.session.execute(
                select(Result, Assessment, Subject)
                .join(Assessment, Assessment.id == Result.assessment_id)
                .join(Subject, Subject.id == Assessment.subject_id)
                .where(Result.student_id == student_id)
                .order_by(Result.published_at.desc())
                .limit(20)
            )
        ).all()
        recent_results = []
        for result, assessment, subject in result_rows:
            score = float(result.score or 0)
            total_marks = float(result.total_marks or 0)
            percentage = round((score / total_marks) * 100, 2) if total_marks > 0 else 0.0
            recent_results.append(
                {
                    "result_id": result.id,
                    "assessment_id": assessment.id,
                    "title": assessment.title,
                    "topic": assessment.topic,
                    "subject": subject.name,
                    "assessment_type": assessment.assessment_type.value
                    if hasattr(assessment.assessment_type, "value")
                    else str(assessment.assessment_type),
                    "score": score,
                    "total_marks": total_marks,
                    "percentage": percentage,
                    "rank": int(result.rank) if result.rank is not None else None,
                    "published_at": result.published_at.isoformat() if result.published_at else None,
                }
            )

        attendance_rows = (
            await self.session.execute(
                select(AttendanceRecord.attendance_date, AttendanceRecord.status)
                .where(AttendanceRecord.student_id == student_id)
                .order_by(AttendanceRecord.attendance_date.desc())
                .limit(60)
            )
        ).all()
        attendance_timeline = []
        attendance_status_counts = {"present": 0, "absent": 0, "late": 0, "leave": 0}
        for attendance_date, attendance_status in attendance_rows:
            status_value = attendance_status.value if hasattr(attendance_status, "value") else str(attendance_status)
            if status_value in attendance_status_counts:
                attendance_status_counts[status_value] += 1
            attendance_timeline.append(
                {
                    "date": attendance_date.isoformat(),
                    "status": status_value,
                }
            )

        payment_rows = (
            await self.session.execute(
                select(PaymentTransaction, FeeInvoice)
                .join(FeeInvoice, FeeInvoice.id == PaymentTransaction.invoice_id)
                .where(
                    PaymentTransaction.student_id == student_id,
                    PaymentTransaction.status == "success",
                )
                .order_by(PaymentTransaction.paid_at.desc(), PaymentTransaction.created_at.desc())
                .limit(20)
            )
        ).all()
        payment_ledger = []
        for tx, invoice in payment_rows:
            payment_ledger.append(
                {
                    "payment_id": tx.id,
                    "invoice_no": invoice.invoice_no,
                    "period_label": invoice.period_label,
                    "amount": float(tx.amount or 0),
                    "payment_mode": tx.payment_mode,
                    "reference_no": tx.external_ref,
                    "paid_at": (tx.paid_at or tx.created_at).isoformat(),
                }
            )

        return {
            "student": student,
            "analytics": {
                "recent_results": recent_results,
                "attendance_timeline": attendance_timeline,
                "attendance_status_counts": attendance_status_counts,
                "payment_ledger": payment_ledger,
            },
        }

    async def export_student_full_profile_pdf(self, *, student_id: str) -> dict:
        payload = await self.get_student_full_profile(student_id=student_id)
        student = payload["student"]
        analytics = payload["analytics"]

        generated_at = datetime.now(app_timezone())
        media_dir, media_url = self._media_config()
        export_dir = media_dir / "profile_exports"
        try:
            export_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as exc:
            raise ForbiddenException(
                "Profile export directory is not writable. Please configure MEDIA_BASE_DIR with write access."
            ) from exc

        file_name = f"STUDENT-PROFILE-{student_id[:6].upper()}-{generated_at.strftime('%Y%m%d%H%M%S')}.pdf"
        file_path = export_dir / file_name
        download_url = f"{media_url}/profile_exports/{file_name}"

        lines = [
            get_settings().institute_display_name,
            "Student Full Profile Export",
            "",
            f"Generated At (IST): {generated_at.isoformat()}",
            "",
            f"Student Name: {student['full_name']}",
            f"Class: {student.get('class_name') or '-'}",
            f"Stream: {student.get('stream') or '-'}",
            f"Contact: {student.get('phone') or '-'}",
            f"Parent Contact: {student.get('parent_contact_number') or '-'}",
            "",
            "Attendance Summary:",
            f"Present: {student['attendance']['present_sessions']}",
            f"Total Sessions: {student['attendance']['total_sessions']}",
            f"Attendance %: {student['attendance']['percentage']}%",
            "",
            "Progress Summary:",
            f"Tests Taken: {student['progress']['tests_taken']}",
            f"Score %: {student['progress']['percentage']}%",
            "",
            "Fee Summary:",
            f"Fee Structure: {student['fee']['fee_structure_name'] or '-'}",
            f"Total Fee: {self._format_inr(student['fee']['total_amount'])}",
            f"Paid: {self._format_inr(student['fee']['paid_amount'])}",
            f"Pending: {self._format_inr(student['fee']['pending_amount'])}",
            "",
            "Recent Results:",
        ]
        for idx, item in enumerate(analytics["recent_results"][:10], start=1):
            lines.append(
                f"{idx}. {item['subject']} - {item['title']} | {item['score']}/{item['total_marks']} ({item['percentage']}%)"
            )

        lines.append("")
        lines.append("Recent Fee Payments:")
        for idx, item in enumerate(analytics["payment_ledger"][:10], start=1):
            lines.append(
                f"{idx}. {item['invoice_no']} | {self._format_inr(item['amount'])} | {item['payment_mode']} | {item['paid_at']}"
            )

        lines.extend(["", f"Download URL: {download_url}"])
        try:
            file_path.write_bytes(self._build_text_pdf(lines))
        except PermissionError as exc:
            raise ForbiddenException(
                "Unable to write profile export file. Please check media directory permissions."
            ) from exc

        return {
            "student_id": student_id,
            "student": student,
            "profile_export": {
                "file_name": file_name,
                "download_url": download_url,
                "generated_at": generated_at.isoformat(),
            },
        }

    async def send_student_report_card_whatsapp(
        self,
        *,
        student_id: str,
        phone: str | None,
        custom_message: str | None,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        report = await self.get_student_report_card(student_id=student_id)
        student = report["student"]
        report_card = report["report_card"]

        to_phone = phone or student.get("parent_contact_number") or student.get("phone")
        if not to_phone:
            raise ForbiddenException("Parent contact number is required")

        message = (custom_message or "").strip()
        if not message:
            message_lines = [
                f"Report card for {student['full_name']}",
                f"Class: {student.get('class_name') or '-'} | Stream: {student.get('stream') or '-'}",
                f"Attendance: {student['attendance']['percentage']}%",
                f"Progress: {student['progress']['percentage']}%",
                f"Download: {report_card['download_url']}",
            ]
            message = "\n".join(message_lines)

        delivery = await self._send_whatsapp_text_message(
            to_phone=to_phone,
            message=message,
        )

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.student_report_card.whatsapp",
            entity_type="student_report_card",
            entity_id=student_id,
            before_state=None,
            after_state={
                "student_id": student_id,
                "to_phone": self._normalize_whatsapp_phone(to_phone),
                "delivery_status": delivery.get("status"),
                "file_name": report_card.get("file_name"),
            },
            ip_address=ip_address,
        )
        await self.session.commit()

        return {
            "student_id": student_id,
            "report_card": report_card,
            "delivery": delivery,
        }

    async def create_student(
        self,
        *,
        payload: AdminStudentCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        batch = await self.session.get(Batch, payload.batch_id)
        if not batch:
            raise NotFoundException("Batch not found")
        standard = await self.session.get(Standard, batch.standard_id)

        role_stmt = select(Role).where(Role.code == RoleCode.STUDENT)
        student_role = (await self.session.execute(role_stmt)).scalar_one_or_none()
        if not student_role:
            raise NotFoundException("Student role not configured")

        derived_class_name, derived_stream = self._derive_class_stream_from_standard_name(
            standard.name if standard else None
        )
        class_name = payload.class_name.strip() if payload.class_name else derived_class_name
        stream = self._normalize_optional_stream(payload.stream) or derived_stream
        grade_hint = self._extract_grade(class_name, standard.name if standard else None)
        if grade_hint == "10":
            stream = None
        normalized_student_stream = self._normalize_fee_stream(stream)

        selected_fee_structure: FeeStructure | None = None
        manual_fee_amount = float(payload.manual_fee_amount or 0)
        class_level = int(grade_hint) if grade_hint is not None else None
        standard_grade_hint = self._extract_grade(None, standard.name if standard else None)
        if class_level is not None and standard_grade_hint is not None and str(class_level) != standard_grade_hint:
            raise ForbiddenException("Selected batch does not match selected class level")
        if class_level in {11, 12} and normalized_student_stream in {"science", "commerce"}:
            standard_name_source = (standard.name if standard else "").lower()
            if normalized_student_stream not in standard_name_source:
                raise ForbiddenException("Selected batch does not match selected class stream")

        if payload.fee_structure_id and manual_fee_amount > 0:
            raise ForbiddenException("Choose either fee structure or manual fee amount")

        base_fee_amount: float | None = None
        selected_installment_count = max(1, int(payload.installment_count or 0)) if payload.installment_count else None

        if payload.fee_structure_id:
            selected_fee_structure = await self.session.get(FeeStructure, payload.fee_structure_id)
            if not selected_fee_structure:
                raise NotFoundException("Fee structure not found")
            if not selected_fee_structure.is_active:
                raise ForbiddenException("Selected fee structure is inactive")

            if class_level is not None and selected_fee_structure.class_level != class_level:
                raise ForbiddenException("Selected fee structure class does not match student class")
            if selected_fee_structure.class_level in {11, 12}:
                if normalized_student_stream not in {"science", "commerce"}:
                    raise ForbiddenException("Student stream is required for class 11 and 12 fee structure")
                if selected_fee_structure.stream != normalized_student_stream:
                    raise ForbiddenException("Selected fee structure stream does not match student stream")
            if selected_fee_structure.class_level == 10 and selected_fee_structure.stream is not None:
                raise ForbiddenException("Class 10 assignment cannot use stream-based fee structure")
            base_fee_amount = float(selected_fee_structure.total_amount)
            if selected_installment_count is None:
                selected_installment_count = max(1, int(selected_fee_structure.installment_count or 1))
        elif manual_fee_amount > 0:
            if class_level is None:
                raise ForbiddenException("Class is required to create manual fee structure")
            if class_level in {11, 12} and normalized_student_stream not in {"science", "commerce"}:
                raise ForbiddenException("Stream is required for class 11 and 12 manual fee")
            base_fee_amount = manual_fee_amount
            if selected_installment_count is None:
                selected_installment_count = max(1, int(payload.manual_fee_installment_count or 3))

        negotiable_amount = float(payload.negotiable_amount or 0)
        if negotiable_amount > 0 and base_fee_amount is None:
            raise ForbiddenException("Select fee structure or manual fee amount before entering negotiable amount")
        if base_fee_amount is not None and negotiable_amount > base_fee_amount + 0.0001:
            raise ForbiddenException("Negotiable amount cannot exceed selected fee amount")

        effective_fee_amount = negotiable_amount if negotiable_amount > 0 else base_fee_amount
        initial_paid_amount = float(payload.initial_fee_paid_amount or 0)
        if initial_paid_amount > 0 and effective_fee_amount is None:
            raise ForbiddenException("Select fee structure or manual fee amount before recording initial paid amount")
        if effective_fee_amount is not None and initial_paid_amount > effective_fee_amount + 0.0001:
            raise ForbiddenException("Initial paid amount cannot exceed selected fee amount")

        if effective_fee_amount is not None:
            if class_level is None:
                raise ForbiddenException("Class is required to create fee structure")
            if class_level in {11, 12} and normalized_student_stream not in {"science", "commerce"}:
                raise ForbiddenException("Stream is required for class 11 and 12 fee setup")

            needs_derived_structure = (
                selected_fee_structure is None
                or abs(float(selected_fee_structure.total_amount) - effective_fee_amount) > 0.0001
                or (
                    selected_installment_count is not None
                    and int(selected_fee_structure.installment_count or 1) != selected_installment_count
                )
            )

            if needs_derived_structure:
                selected_fee_structure = await self._create_manual_fee_structure(
                    class_level=class_level,
                    stream=normalized_student_stream,
                    total_amount=effective_fee_amount,
                    installment_count=selected_installment_count or 3,
                    actor_user_id=actor_user_id,
                    student_label=payload.full_name,
                )

        normalized_admission_no = payload.admission_no.strip()
        existing_admission = (
            await self.session.execute(
                select(StudentProfile.id).where(StudentProfile.admission_no == normalized_admission_no)
            )
        ).scalar_one_or_none()
        if existing_admission:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Admission number already exists. Please use a different admission number.",
            )

        normalized_phone = (payload.phone or "").strip()
        if not normalized_phone:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Student primary contact number is required.",
            )
        if not normalized_phone.isdigit() or len(normalized_phone) < 10 or len(normalized_phone) > 15:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Phone number must contain 10 to 15 digits.",
            )

        existing_phone = (
            await self.session.execute(
                select(User.id).where(User.phone == normalized_phone)
            )
        ).scalar_one_or_none()
        if existing_phone:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Phone number already exists. Please use a different phone number.",
            )

        normalized_email = (payload.email or "").strip().lower()
        if normalized_email:
            existing_email = (
                await self.session.execute(
                    select(User.id).where(func.lower(User.email) == normalized_email)
                )
            ).scalar_one_or_none()
            if existing_email:
                raise HTTPException(
                    status_code=http_status.HTTP_409_CONFLICT,
                    detail="Email already exists. Please use a different email.",
                )

        generated_password: str | None = None
        effective_password = (payload.password or "").strip()
        if not effective_password:
            generated_password = self._generate_login_password()
            effective_password = generated_password

        if not self._is_valid_login_password(effective_password):
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must be 6-8 characters and include both letters and numbers.",
            )

        user = User(
            full_name=payload.full_name,
            email=normalized_email or None,
            phone=normalized_phone or None,
            password_hash=get_password_hash(effective_password),
            status=UserStatus.ACTIVE,
        )
        self.session.add(user)
        await self.session.flush()

        self.session.add(UserRole(user_id=user.id, role_id=student_role.id))

        await self._upsert_student_credential_snapshot(
            user_id=user.id,
            login_id=normalized_phone,
            password_plain=effective_password,
            actor_user_id=actor_user_id,
        )

        student_profile = StudentProfile(
            user_id=user.id,
            admission_no=normalized_admission_no,
            roll_no=payload.roll_no,
            current_batch_id=payload.batch_id,
            class_name=class_name,
            stream=stream,
            parent_contact_number=payload.parent_contact_number,
            address=payload.address,
            school_details=payload.school_details,
        )
        self.session.add(student_profile)
        await self.session.flush()

        self.session.add(
            StudentBatchEnrollment(
                student_id=student_profile.id,
                batch_id=payload.batch_id,
                from_date=date.today(),
                to_date=None,
            )
        )

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.student.create",
            entity_type="student_profile",
            entity_id=student_profile.id,
            before_state=None,
            after_state={
                "student_id": student_profile.id,
                "user_id": user.id,
                "batch_id": payload.batch_id,
            },
            ip_address=ip_address,
        )

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            message = str(getattr(exc, "orig", exc)).lower()
            if "student_profiles.admission_no" in message:
                raise HTTPException(
                    status_code=http_status.HTTP_409_CONFLICT,
                    detail="Admission number already exists. Please use a different admission number.",
                ) from exc
            if "users.phone" in message:
                raise HTTPException(
                    status_code=http_status.HTTP_409_CONFLICT,
                    detail="Phone number already exists. Please use a different phone number.",
                ) from exc
            if "users.email" in message:
                raise HTTPException(
                    status_code=http_status.HTTP_409_CONFLICT,
                    detail="Email already exists. Please use a different email.",
                ) from exc
            raise

        fee_assignment = None
        fee_payment = None
        fee_receipt = None
        if selected_fee_structure:
            fee_assignment = await self.assign_student_fee_structure(
                student_id=student_profile.id,
                payload=AdminStudentFeeStructureAssignDTO(fee_structure_id=selected_fee_structure.id),
                actor_user_id=actor_user_id,
                ip_address=ip_address,
            )

            if initial_paid_amount > 0:
                fee_payment = await self.record_student_fee_payment(
                    student_id=student_profile.id,
                    payload=AdminStudentFeePaymentCreateDTO(
                        amount=initial_paid_amount,
                        paid_on=payload.initial_fee_paid_on or date.today(),
                        payment_mode=payload.initial_fee_payment_mode,
                        reference_no=payload.initial_fee_reference_no,
                        note=payload.initial_fee_note,
                        period_label="Initial Payment",
                    ),
                    actor_user_id=actor_user_id,
                    ip_address=ip_address,
                )

            fee_receipt, _, _ = await self._ensure_latest_fee_receipt(
                student_id=student_profile.id,
                regenerate=True,
            )

        installment_preview = None
        if effective_fee_amount is not None:
            installment_preview = self._build_three_installment_preview(
                total_fee=effective_fee_amount,
                paid_amount=initial_paid_amount,
            )

        return {
            "student_id": student_profile.id,
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "login_id": user.phone,
            "status": user.status.value,
            "generated_password": generated_password,
            "issued_password": effective_password,
            "password_generated": generated_password is not None,
            "admission_no": student_profile.admission_no,
            "roll_no": student_profile.roll_no,
            "batch_id": student_profile.current_batch_id,
            "class_name": student_profile.class_name,
            "stream": student_profile.stream,
            "parent_contact_number": student_profile.parent_contact_number,
            "fee_assignment": fee_assignment,
            "initial_fee_payment": fee_payment,
            "fee_receipt": fee_receipt,
            "fee_amount": effective_fee_amount,
            "negotiable_amount": negotiable_amount if negotiable_amount > 0 else None,
            "installment_preview": installment_preview,
        }

    async def list_student_credentials(
        self,
        *,
        search: str | None,
        status: str | None,
        class_level: int | None,
        stream: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = (
            select(StudentProfile, User, Batch, Standard, StudentCredential)
            .join(User, User.id == StudentProfile.user_id)
            .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
            .outerjoin(Standard, Standard.id == Batch.standard_id)
            .outerjoin(StudentCredential, StudentCredential.user_id == User.id)
        )

        filters = []
        if search:
            filters.append(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.phone.ilike(f"%{search}%"),
                    StudentProfile.admission_no.ilike(f"%{search}%"),
                )
            )

        if status:
            filters.append(User.status == UserStatus(status))

        if class_level is not None:
            filters.append(
                or_(
                    StudentProfile.class_name.ilike(f"%{class_level}%"),
                    Standard.name.ilike(f"%{class_level}%"),
                )
            )

        if stream:
            normalized_stream = self._normalize_stream(stream)
            if normalized_stream in {"science", "commerce"}:
                filters.append(StudentProfile.stream.is_not(None))
                filters.append(StudentProfile.stream.ilike(f"%{normalized_stream}%"))

        if filters:
            query = query.where(and_(*filters))

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(User.created_at.desc()).limit(limit).offset(offset)
            )
        ).all()

        items = [
            {
                "student_id": profile.id,
                "user_id": user.id,
                "full_name": user.full_name,
                "login_id": user.phone,
                "status": user.status.value if hasattr(user.status, "value") else str(user.status),
                "class_name": profile.class_name or (standard.name if standard else None),
                "stream": profile.stream,
                "parent_contact_number": profile.parent_contact_number,
                "credentials_ready": bool((user.phone or "").strip() and (user.password_hash or "").strip()),
                "current_password": credential.password_plain if credential else None,
                "password_last_updated_at": credential.password_updated_at if credential else None,
                "batch": {
                    "id": batch.id,
                    "name": batch.name,
                    "academic_year": batch.academic_year,
                    "standard_name": standard.name if standard else None,
                }
                if batch
                else None,
                "created_at": user.created_at,
            }
            for profile, user, batch, standard, credential in rows
        ]
        return items, total

    async def reset_student_credentials(
        self,
        *,
        student_id: str,
        new_password: str | None,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        profile = await self.session.get(StudentProfile, student_id)
        if not profile:
            raise NotFoundException("Student profile not found")

        user = await self.session.get(User, profile.user_id)
        if not user:
            raise NotFoundException("Student user account not found")

        login_id = (user.phone or "").strip()
        if not login_id:
            raise ForbiddenException("Student login ID is missing. Please set a primary contact number first.")

        generated = False
        password_value = (new_password or "").strip()
        if not password_value:
            password_value = self._generate_login_password()
            generated = True

        if not self._is_valid_login_password(password_value):
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must be 6-8 characters and include both letters and numbers.",
            )

        user.password_hash = get_password_hash(password_value)
        await self._upsert_student_credential_snapshot(
            user_id=user.id,
            login_id=login_id,
            password_plain=password_value,
            actor_user_id=actor_user_id,
        )
        await self.session.execute(
            update(RefreshSession)
            .where(RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.student.credentials.reset",
            entity_type="student_profile",
            entity_id=profile.id,
            before_state={"login_id": login_id},
            after_state={"login_id": login_id, "password_reset": True, "generated": generated},
            ip_address=ip_address,
        )
        await self.session.commit()

        return {
            "student_id": profile.id,
            "user_id": user.id,
            "login_id": login_id,
            "temporary_password": password_value,
            "generated": generated,
        }

    async def update_student(
        self,
        *,
        user_id: str,
        payload: AdminStudentUpdateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        user = await self.session.get(User, user_id)
        if not user:
            raise NotFoundException("User not found")

        profile_stmt = select(StudentProfile).where(StudentProfile.user_id == user_id)
        profile = (await self.session.execute(profile_stmt)).scalar_one_or_none()
        if not profile:
            raise NotFoundException("Student profile not found")

        before = {
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "status": user.status.value if hasattr(user.status, "value") else str(user.status),
            "roll_no": profile.roll_no,
            "batch_id": profile.current_batch_id,
        }

        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.email is not None:
            user.email = payload.email
        if payload.phone is not None:
            user.phone = payload.phone
        if payload.status is not None:
            user.status = UserStatus(payload.status)
        if payload.roll_no is not None:
            profile.roll_no = payload.roll_no

        if payload.batch_id is not None and payload.batch_id != profile.current_batch_id:
            batch = await self.session.get(Batch, payload.batch_id)
            if not batch:
                raise NotFoundException("Batch not found")
            profile.current_batch_id = payload.batch_id
            self.session.add(
                StudentBatchEnrollment(
                    student_id=profile.id,
                    batch_id=payload.batch_id,
                    from_date=date.today(),
                    to_date=None,
                )
            )

        after = {
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "status": user.status.value if hasattr(user.status, "value") else str(user.status),
            "roll_no": profile.roll_no,
            "batch_id": profile.current_batch_id,
        }

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.student.update",
            entity_type="student_profile",
            entity_id=profile.id,
            before_state=before,
            after_state=after,
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "student_id": profile.id,
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "status": user.status.value if hasattr(user.status, "value") else str(user.status),
            "roll_no": profile.roll_no,
            "batch_id": profile.current_batch_id,
        }

    async def list_batches(self, *, limit: int, offset: int) -> tuple[list[dict], int]:
        query = (
            select(Batch, Standard)
            .join(Standard, Standard.id == Batch.standard_id)
            .order_by(Batch.academic_year.desc(), Batch.name.asc())
        )

        total = (await self.session.execute(select(func.count()).select_from(Batch))).scalar_one()
        rows = (await self.session.execute(query.limit(limit).offset(offset))).all()

        items = [
            {
                "id": batch.id,
                "name": batch.name,
                "academic_year": batch.academic_year,
                "standard": {
                    "id": standard.id,
                    "name": standard.name,
                },
            }
            for batch, standard in rows
        ]
        return items, total

    async def create_batch(
        self,
        *,
        payload: AdminBatchCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        standard = await self.session.get(Standard, payload.standard_id)
        if not standard:
            raise NotFoundException("Standard not found")

        batch = Batch(
            standard_id=payload.standard_id,
            name=payload.name,
            academic_year=payload.academic_year,
        )
        self.session.add(batch)
        await self.session.flush()

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.batch.create",
            entity_type="batch",
            entity_id=batch.id,
            before_state=None,
            after_state={
                "name": batch.name,
                "academic_year": batch.academic_year,
                "standard_id": batch.standard_id,
            },
            ip_address=ip_address,
        )
        await self.session.commit()

        return {
            "id": batch.id,
            "name": batch.name,
            "academic_year": batch.academic_year,
            "standard_id": batch.standard_id,
        }

    async def list_notices(self, *, status: str | None, limit: int, offset: int) -> tuple[list[dict], int]:
        query = select(Notice)
        if status:
            query = query.where(Notice.status == NoticeStatus(status))

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(Notice.created_at.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()

        return [
            {
                "id": n.id,
                "title": n.title,
                "status": n.status.value if hasattr(n.status, "value") else str(n.status),
                "priority": n.priority,
                "publish_at": n.publish_at,
                "created_at": n.created_at,
            }
            for n in rows
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

        before = {
            "status": notice.status.value if hasattr(notice.status, "value") else str(notice.status),
            "publish_at": notice.publish_at,
        }

        notice.status = NoticeStatus.PUBLISHED
        if notice.publish_at is None:
            notice.publish_at = datetime.now(UTC)

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.notice.publish",
            entity_type="notice",
            entity_id=notice.id,
            before_state=before,
            after_state={"status": notice.status.value, "publish_at": notice.publish_at},
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "id": notice.id,
            "status": notice.status.value,
            "publish_at": notice.publish_at,
        }

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
            query = query.where(Homework.due_date >= due_from)
        if due_to:
            query = query.where(Homework.due_date <= due_to)

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(Homework.due_date.asc(), Homework.created_at.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()

        return [
            {
                "id": row.id,
                "title": row.title,
                "subject_id": row.subject_id,
                "due_date": row.due_date,
                "status": row.status.value if hasattr(row.status, "value") else str(row.status),
                "created_at": row.created_at,
            }
            for row in rows
        ], total

    async def create_homework(
        self,
        *,
        payload: AdminHomeworkCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        homework = Homework(
            title=payload.title,
            description=payload.description,
            subject_id=payload.subject_id,
            due_date=payload.due_date,
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

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.homework.create",
            entity_type="homework",
            entity_id=homework.id,
            before_state=None,
            after_state={
                "title": homework.title,
                "status": homework.status.value,
                "targets": [target.model_dump() for target in payload.targets],
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "id": homework.id,
            "title": homework.title,
            "status": homework.status.value,
            "due_date": homework.due_date,
        }

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

        before = {"status": homework.status.value if hasattr(homework.status, "value") else str(homework.status)}
        homework.status = HomeworkStatus.PUBLISHED

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.homework.publish",
            entity_type="homework",
            entity_id=homework.id,
            before_state=before,
            after_state={"status": homework.status.value},
            ip_address=ip_address,
        )

        await self.session.commit()

        return {"id": homework.id, "status": homework.status.value}

    async def list_attendance(
        self,
        *,
        batch_id: str | None,
        attendance_date: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = (
            select(AttendanceRecord, StudentProfile, User)
            .join(StudentProfile, StudentProfile.id == AttendanceRecord.student_id)
            .join(User, User.id == StudentProfile.user_id)
        )
        if batch_id:
            query = query.where(AttendanceRecord.batch_id == batch_id)
        if attendance_date:
            query = query.where(AttendanceRecord.attendance_date == attendance_date)

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(AttendanceRecord.attendance_date.desc()).limit(limit).offset(offset)
            )
        ).all()

        return [
            {
                "id": record.id,
                "student_id": record.student_id,
                "student_name": user.full_name,
                "batch_id": record.batch_id,
                "attendance_date": record.attendance_date,
                "session_code": record.session_code,
                "status": record.status.value if hasattr(record.status, "value") else str(record.status),
                "source": record.source,
            }
            for record, _, user in rows
        ], total

    async def create_attendance_correction(
        self,
        *,
        payload: AdminAttendanceCorrectionCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        record = await self.session.get(AttendanceRecord, payload.attendance_record_id)
        if not record:
            raise NotFoundException("Attendance record not found")

        correction = AttendanceCorrection(
            attendance_record_id=payload.attendance_record_id,
            requested_by=actor_user_id,
            reason=payload.reason,
            status="pending",
        )
        self.session.add(correction)
        await self.session.flush()

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.attendance_correction.create",
            entity_type="attendance_correction",
            entity_id=correction.id,
            before_state=None,
            after_state={
                "attendance_record_id": correction.attendance_record_id,
                "status": correction.status,
                "reason": correction.reason,
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "id": correction.id,
            "attendance_record_id": correction.attendance_record_id,
            "status": correction.status,
            "reason": correction.reason,
        }

    async def decide_attendance_correction(
        self,
        *,
        correction_id: str,
        payload: AdminAttendanceCorrectionApproveDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        correction = await self.session.get(AttendanceCorrection, correction_id)
        if not correction:
            raise NotFoundException("Attendance correction not found")

        record = await self.session.get(AttendanceRecord, correction.attendance_record_id)
        if not record:
            raise NotFoundException("Attendance record not found")

        before = {
            "correction_status": correction.status,
            "attendance_status": record.status.value if hasattr(record.status, "value") else str(record.status),
        }

        correction.status = payload.status
        correction.approved_by = actor_user_id

        if payload.status == "approved" and payload.new_attendance_status is not None:
            record.status = AttendanceStatus(payload.new_attendance_status)
            record.source = "admin_correction"
            record.marked_at = datetime.now(UTC)

        after = {
            "correction_status": correction.status,
            "attendance_status": record.status.value if hasattr(record.status, "value") else str(record.status),
        }

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.attendance_correction.decide",
            entity_type="attendance_correction",
            entity_id=correction.id,
            before_state=before,
            after_state=after,
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "id": correction.id,
            "status": correction.status,
            "attendance_record_id": correction.attendance_record_id,
        }

    async def list_assessments(
        self,
        *,
        status: str | None,
        assessment_type: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = select(Assessment)
        if status:
            query = query.where(Assessment.status == AssessmentStatus(status))
        if assessment_type:
            try:
                normalized_assessment_type = require_assessment_type(assessment_type)
            except ValueError as exc:
                raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
            query = query.where(Assessment.assessment_type == normalized_assessment_type)

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(Assessment.created_at.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()

        return [
            {
                "id": row.id,
                "title": row.title,
                "subject_id": row.subject_id,
                "assessment_type": row.assessment_type.value if hasattr(row.assessment_type, "value") else str(row.assessment_type),
                "status": row.status.value if hasattr(row.status, "value") else str(row.status),
                "starts_at": self._to_utc(row.starts_at),
                "ends_at": self._to_utc(row.ends_at),
                "duration_sec": row.duration_sec,
                "attempt_limit": row.attempt_limit,
            }
            for row in rows
        ], total

    async def create_assessment(
        self,
        *,
        payload: AdminAssessmentCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        try:
            normalized_assessment_type = require_assessment_type(payload.assessment_type)
        except ValueError as exc:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        assessment = Assessment(
            title=payload.title,
            description=payload.description,
            subject_id=payload.subject_id,
            assessment_type=normalized_assessment_type,
            status=AssessmentStatus.DRAFT,
            starts_at=self._to_utc_from_app_input(payload.starts_at),
            ends_at=self._to_utc_from_app_input(payload.ends_at),
            duration_sec=payload.duration_sec,
            attempt_limit=payload.attempt_limit,
            total_marks=payload.total_marks,
        )
        self.session.add(assessment)
        await self.session.flush()

        for target in payload.targets:
            self.session.add(
                AssessmentAssignment(
                    assessment_id=assessment.id,
                    target_type=target.target_type,
                    target_id=target.target_id,
                )
            )

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.assessment.create",
            entity_type="assessment",
            entity_id=assessment.id,
            before_state=None,
            after_state={
                "title": assessment.title,
                "status": assessment.status.value,
                "targets": [target.model_dump() for target in payload.targets],
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "id": assessment.id,
            "title": assessment.title,
            "status": assessment.status.value,
        }

    async def publish_assessment(
        self,
        *,
        assessment_id: str,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        assessment = await self.session.get(Assessment, assessment_id)
        if not assessment:
            raise NotFoundException("Assessment not found")

        before = {
            "status": assessment.status.value if hasattr(assessment.status, "value") else str(assessment.status)
        }
        assessment.status = AssessmentStatus.PUBLISHED

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.assessment.publish",
            entity_type="assessment",
            entity_id=assessment.id,
            before_state=before,
            after_state={"status": assessment.status.value},
            ip_address=ip_address,
        )

        await self.session.commit()

        return {"id": assessment.id, "status": assessment.status.value}

    async def publish_result(
        self,
        *,
        payload: AdminResultPublishDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        assessment = await self.session.get(Assessment, payload.assessment_id)
        if not assessment:
            raise NotFoundException("Assessment not found")

        student = await self.session.get(StudentProfile, payload.student_id)
        if not student:
            raise NotFoundException("Student not found")

        stmt = select(Result).where(
            Result.assessment_id == payload.assessment_id,
            Result.student_id == payload.student_id,
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()

        before = None
        if existing:
            before = {
                "score": float(existing.score),
                "total_marks": float(existing.total_marks),
                "rank": existing.rank,
            }
            existing.score = payload.score
            existing.total_marks = payload.total_marks
            existing.rank = payload.rank
            existing.published_at = datetime.now(UTC)
            result = existing
        else:
            result = Result(
                assessment_id=payload.assessment_id,
                student_id=payload.student_id,
                score=payload.score,
                total_marks=payload.total_marks,
                rank=payload.rank,
                published_at=datetime.now(UTC),
            )
            self.session.add(result)
            await self.session.flush()

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.result.publish",
            entity_type="result",
            entity_id=result.id,
            before_state=before,
            after_state={
                "assessment_id": result.assessment_id,
                "student_id": result.student_id,
                "score": float(result.score),
                "total_marks": float(result.total_marks),
                "rank": result.rank,
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "id": result.id,
            "assessment_id": result.assessment_id,
            "student_id": result.student_id,
            "score": float(result.score),
            "total_marks": float(result.total_marks),
            "rank": result.rank,
            "published_at": result.published_at,
        }
    async def list_doubts(
        self,
        *,
        status: str | None,
        subject_id: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        teacher_user = aliased(User)

        stmt = (
            select(Doubt, StudentProfile, User, TeacherProfile, teacher_user, CompletedLecture)
            .join(StudentProfile, StudentProfile.id == Doubt.student_id)
            .join(User, User.id == StudentProfile.user_id)
            .outerjoin(TeacherProfile, TeacherProfile.id == Doubt.teacher_id)
            .outerjoin(teacher_user, teacher_user.id == TeacherProfile.user_id)
            .outerjoin(CompletedLecture, CompletedLecture.id == Doubt.lecture_id)
        )

        filters = []
        if status:
            filters.append(Doubt.status == DoubtStatus(status))
        if subject_id:
            filters.append(Doubt.subject_id == subject_id)
        if query:
            filters.append(or_(Doubt.topic.ilike(f"%{query}%"), Doubt.description.ilike(f"%{query}%")))

        if filters:
            stmt = stmt.where(and_(*filters))

        total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                stmt.order_by(Doubt.updated_at.desc()).limit(limit).offset(offset)
            )
        ).all()

        return [
            {
                "id": doubt.id,
                "student_id": doubt.student_id,
                "student_name": student_user.full_name,
                "teacher_id": doubt.teacher_id,
                "teacher_name": teacher_user_row.full_name if teacher_user_row else None,
                "lecture_id": doubt.lecture_id,
                "lecture_topic": lecture.topic if lecture else None,
                "subject_id": doubt.subject_id,
                "topic": doubt.topic,
                "status": doubt.status.value if hasattr(doubt.status, "value") else str(doubt.status),
                "priority": doubt.priority,
                "created_at": doubt.created_at,
                "updated_at": doubt.updated_at,
            }
            for doubt, _student, student_user, _teacher, teacher_user_row, lecture in rows
        ], total

    async def get_doubt_conversation(self, *, doubt_id: str) -> dict:
        student_user = aliased(User)
        teacher_user = aliased(User)

        row = (
            await self.session.execute(
                select(Doubt, StudentProfile, student_user, TeacherProfile, teacher_user, CompletedLecture)
                .join(StudentProfile, StudentProfile.id == Doubt.student_id)
                .join(student_user, student_user.id == StudentProfile.user_id)
                .outerjoin(TeacherProfile, TeacherProfile.id == Doubt.teacher_id)
                .outerjoin(teacher_user, teacher_user.id == TeacherProfile.user_id)
                .outerjoin(CompletedLecture, CompletedLecture.id == Doubt.lecture_id)
                .where(Doubt.id == doubt_id)
            )
        ).first()
        if not row:
            raise NotFoundException("Doubt not found")

        doubt, _student_profile, student_user_row, _teacher_profile, teacher_user_row, lecture = row

        sender_user = aliased(User)
        message_rows = (
            await self.session.execute(
                select(DoubtMessage, sender_user)
                .outerjoin(sender_user, sender_user.id == DoubtMessage.sender_user_id)
                .where(DoubtMessage.doubt_id == doubt_id)
                .order_by(DoubtMessage.created_at.asc(), DoubtMessage.id.asc())
            )
        ).all()

        return {
            "doubt": {
                "id": doubt.id,
                "student_id": doubt.student_id,
                "student_name": student_user_row.full_name,
                "teacher_id": doubt.teacher_id,
                "teacher_name": teacher_user_row.full_name if teacher_user_row else None,
                "lecture_id": doubt.lecture_id,
                "lecture_topic": lecture.topic if lecture else None,
                "subject_id": doubt.subject_id,
                "topic": doubt.topic,
                "description": doubt.description,
                "status": doubt.status.value if hasattr(doubt.status, "value") else str(doubt.status),
                "priority": doubt.priority,
                "created_at": doubt.created_at,
                "updated_at": doubt.updated_at,
            },
            "messages": [
                {
                    "id": message.id,
                    "sender_user_id": message.sender_user_id,
                    "sender_name": sender.full_name if sender else "Unknown",
                    "message": message.message,
                    "created_at": message.created_at,
                }
                for message, sender in message_rows
            ],
        }

    async def update_doubt(
        self,
        *,
        doubt_id: str,
        payload: AdminDoubtUpdateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        doubt = await self.session.get(Doubt, doubt_id)
        if not doubt:
            raise NotFoundException("Doubt not found")

        before = {"status": doubt.status.value if hasattr(doubt.status, "value") else str(doubt.status)}
        doubt.status = DoubtStatus(payload.status)

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.doubt.update",
            entity_type="doubt",
            entity_id=doubt.id,
            before_state=before,
            after_state={"status": doubt.status.value},
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "id": doubt.id,
            "status": doubt.status.value,
            "updated_at": doubt.updated_at,
        }

    async def _resolve_target_user_ids(self, targets: list[dict]) -> list[str]:
        user_ids: set[str] = set()

        for target in targets:
            target_type = target["target_type"]
            target_id = target["target_id"]

            if target_type == "all":
                rows = (
                    await self.session.execute(
                        select(User.id).where(User.status == UserStatus.ACTIVE)
                    )
                ).all()
                user_ids.update([row[0] for row in rows])

            elif target_type == "all_students":
                rows = (
                    await self.session.execute(
                        select(StudentProfile.user_id)
                        .join(User, User.id == StudentProfile.user_id)
                        .where(User.status == UserStatus.ACTIVE)
                    )
                ).all()
                user_ids.update([row[0] for row in rows])

            elif target_type == "batch":
                rows = (
                    await self.session.execute(
                        select(StudentProfile.user_id)
                        .join(User, User.id == StudentProfile.user_id)
                        .where(
                            StudentProfile.current_batch_id == target_id,
                            User.status == UserStatus.ACTIVE,
                        )
                    )
                ).all()
                user_ids.update([row[0] for row in rows])

            elif target_type == "grade":
                grade_raw, _, stream_raw = target_id.partition(":")
                try:
                    grade = int(grade_raw)
                except ValueError:
                    continue
                if grade not in {10, 11, 12}:
                    continue
                stream_filter = self._normalize_stream(stream_raw) if stream_raw else None

                rows = (
                    await self.session.execute(
                        select(StudentProfile, User, Batch, Standard)
                        .join(User, User.id == StudentProfile.user_id)
                        .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
                        .outerjoin(Standard, Standard.id == Batch.standard_id)
                        .where(User.status == UserStatus.ACTIVE)
                    )
                ).all()

                for profile, user, _batch, standard in rows:
                    student_grade = self._extract_grade(
                        profile.class_name,
                        standard.name if standard else None,
                    )
                    if student_grade != grade:
                        continue

                    if stream_filter and grade in {11, 12}:
                        student_stream = self._normalize_stream(profile.stream)
                        if student_stream != stream_filter:
                            continue

                    user_ids.add(user.id)

            elif target_type == "student":
                row = (
                    await self.session.execute(
                        select(StudentProfile.user_id)
                        .join(User, User.id == StudentProfile.user_id)
                        .where(StudentProfile.id == target_id, User.status == UserStatus.ACTIVE)
                    )
                ).first()
                if row:
                    user_ids.add(row[0])

            elif target_type == "teacher":
                row = (
                    await self.session.execute(
                        select(TeacherProfile.user_id)
                        .join(User, User.id == TeacherProfile.user_id)
                        .where(TeacherProfile.id == target_id, User.status == UserStatus.ACTIVE)
                    )
                ).first()
                if row:
                    user_ids.add(row[0])

        return list(user_ids)

    async def create_notification(
        self,
        *,
        payload: AdminNotificationCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        targets = [target.model_dump() for target in payload.targets]
        user_ids = await self._resolve_target_user_ids(targets)

        notification_type = NotificationType(payload.notification_type)
        for user_id in user_ids:
            self.session.add(
                Notification(
                    recipient_user_id=user_id,
                    notification_type=notification_type,
                    title=payload.title,
                    body=payload.body,
                    is_read=False,
                )
            )

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.notification.create",
            entity_type="notification_broadcast",
            entity_id=f"bulk:{datetime.now(UTC).isoformat()}",
            before_state=None,
            after_state={
                "notification_type": payload.notification_type,
                "targets": targets,
                "recipient_count": len(user_ids),
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "notification_type": payload.notification_type,
            "recipient_count": len(user_ids),
        }

    async def list_standards(self, *, limit: int, offset: int) -> tuple[list[dict], int]:
        query = (
            select(Standard, Branch)
            .join(Branch, Branch.id == Standard.branch_id)
            .order_by(Branch.name.asc(), Standard.name.asc())
        )

        total = (await self.session.execute(select(func.count()).select_from(Standard))).scalar_one()
        rows = (await self.session.execute(query.limit(limit).offset(offset))).all()

        items = [
            {
                "id": standard.id,
                "name": standard.name,
                "branch": {
                    "id": branch.id,
                    "code": branch.code,
                    "name": branch.name,
                },
            }
            for standard, branch in rows
        ]
        return items, total

    async def create_standard(
        self,
        *,
        payload: AdminStandardCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        branch = None
        if payload.branch_id:
            branch = await self.session.get(Branch, payload.branch_id)
            if not branch:
                raise NotFoundException("Branch not found")
        else:
            branch = (
                await self.session.execute(select(Branch).order_by(Branch.created_at.asc()).limit(1))
            ).scalar_one_or_none()
            if not branch:
                raise ForbiddenException("No branch configured. Seed branch first.")

        name = payload.name.strip()
        existing = (
            await self.session.execute(
                select(Standard).where(Standard.branch_id == branch.id, func.lower(Standard.name) == name.lower())
            )
        ).scalar_one_or_none()
        if existing:
            raise ForbiddenException("Standard already exists for this branch")

        standard = Standard(branch_id=branch.id, name=name)
        self.session.add(standard)
        await self.session.flush()

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.standard.create",
            entity_type="standard",
            entity_id=standard.id,
            before_state=None,
            after_state={
                "standard_id": standard.id,
                "name": standard.name,
                "branch_id": standard.branch_id,
                "branch_code": branch.code,
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "id": standard.id,
            "name": standard.name,
            "branch": {
                "id": branch.id,
                "code": branch.code,
                "name": branch.name,
            },
        }

    async def list_subjects(
        self,
        *,
        search: str | None,
        class_level: int | None,
        stream: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = select(Subject).distinct()
        if class_level is not None:
            query = query.join(SubjectAcademicScope, SubjectAcademicScope.subject_id == Subject.id)
            query = query.where(SubjectAcademicScope.class_level == class_level)
            if class_level == 10:
                query = query.where(SubjectAcademicScope.stream == "common")
            elif stream:
                query = query.where(SubjectAcademicScope.stream == self._normalize_stream(stream))

        if search:
            query = query.where(or_(Subject.name.ilike(f"%{search}%"), Subject.code.ilike(f"%{search}%")))

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(Subject.name.asc(), Subject.code.asc()).limit(limit).offset(offset)
            )
        ).scalars().all()

        subject_ids = [row.id for row in rows]
        scope_map: dict[str, list[dict]] = {}
        if subject_ids:
            scope_rows = (
                await self.session.execute(
                    select(SubjectAcademicScope).where(SubjectAcademicScope.subject_id.in_(subject_ids))
                )
            ).scalars().all()

            for scope in scope_rows:
                scope_map.setdefault(scope.subject_id, []).append(
                    {
                        "class_level": int(scope.class_level),
                        "stream": None if int(scope.class_level) == 10 else scope.stream,
                        "estimated_hours": int(scope.estimated_hours or 0),
                    }
                )

        return [
            {
                "id": row.id,
                "code": row.code,
                "name": row.name,
                "scopes": scope_map.get(row.id, []),
            }
            for row in rows
        ], total

    async def create_subject(
        self,
        *,
        payload: AdminSubjectCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        scope_stream = self._subject_scope_stream(payload.class_level, payload.stream)

        preferred_code = payload.code.strip() if payload.code else payload.name
        preferred_code = re.sub(r"[^A-Za-z0-9]+", "_", preferred_code).strip("_").upper()

        subject = None
        if preferred_code:
            subject = (
                await self.session.execute(
                    select(Subject).where(func.upper(Subject.code) == preferred_code)
                )
            ).scalar_one_or_none()

        if subject is None:
            subject = (
                await self.session.execute(
                    select(Subject).where(func.lower(Subject.name) == payload.name.strip().lower())
                )
            ).scalar_one_or_none()

        created_subject = False
        if subject is None:
            code = await self._next_subject_code(preferred=preferred_code)
            subject = Subject(
                code=code,
                name=payload.name.strip(),
            )
            self.session.add(subject)
            await self.session.flush()
            created_subject = True

        existing_scope = (
            await self.session.execute(
                select(SubjectAcademicScope).where(
                    SubjectAcademicScope.subject_id == subject.id,
                    SubjectAcademicScope.class_level == payload.class_level,
                    SubjectAcademicScope.stream == scope_stream,
                )
            )
        ).scalar_one_or_none()

        scope_added = False
        estimate_updated = False
        estimated_hours = int(payload.estimated_hours or 0)
        if existing_scope is None:
            self.session.add(
                SubjectAcademicScope(
                    subject_id=subject.id,
                    class_level=payload.class_level,
                    stream=scope_stream,
                    estimated_hours=estimated_hours,
                )
            )
            scope_added = True
        elif payload.estimated_hours is not None:
            existing_scope.estimated_hours = estimated_hours
            estimate_updated = True

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.subject.create",
            entity_type="subject",
            entity_id=subject.id,
            before_state=None,
            after_state={
                "code": subject.code,
                "name": subject.name,
                "class_level": payload.class_level,
                "stream": None if payload.class_level == 10 else scope_stream,
                "created_subject": created_subject,
                "scope_added": scope_added,
                "estimated_hours": estimated_hours,
                "estimate_updated": estimate_updated,
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "id": subject.id,
            "code": subject.code,
            "name": subject.name,
            "class_level": payload.class_level,
            "stream": None if payload.class_level == 10 else scope_stream,
            "created_subject": created_subject,
            "scope_added": scope_added,
            "estimated_hours": estimated_hours,
            "estimate_updated": estimate_updated,
        }

    @staticmethod
    def _default_subject_catalog() -> dict[tuple[int, str], list[str]]:
        return {
            (10, "common"): ["Hindi", "English", "Mathematics", "Science", "Social Science", "Geography"],
            (11, "science"): ["English", "Hindi", "Algebra", "Geometry", "Physics", "Chemistry", "Biology"],
            (11, "commerce"): [
                "English",
                "Hindi",
                "Economics",
                "Book Keeping",
                "Organization of Commerce",
                "Secretarial Practice",
            ],
            (12, "science"): ["English", "Physics", "Chemistry", "Biology", "Mathematics"],
            (12, "commerce"): [
                "English",
                "Economics",
                "Book Keeping",
                "Organization of Commerce",
                "Secretarial Practice",
            ],
        }

    async def upsert_subject_estimated_hours(
        self,
        *,
        subject_id: str,
        payload: AdminSubjectEstimateUpsertDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        subject = await self.session.get(Subject, subject_id)
        if not subject:
            raise NotFoundException("Subject not found")

        scope_stream = self._subject_scope_stream(payload.class_level, payload.stream)
        scope = (
            await self.session.execute(
                select(SubjectAcademicScope).where(
                    SubjectAcademicScope.subject_id == subject_id,
                    SubjectAcademicScope.class_level == payload.class_level,
                    SubjectAcademicScope.stream == scope_stream,
                )
            )
        ).scalar_one_or_none()
        if not scope:
            raise NotFoundException("Subject scope not found for selected class/stream")

        before_hours = int(scope.estimated_hours or 0)
        scope.estimated_hours = int(payload.estimated_hours)

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.subject.estimate.upsert",
            entity_type="subject_scope",
            entity_id=scope.id,
            before_state={
                "subject_id": subject_id,
                "class_level": payload.class_level,
                "stream": None if payload.class_level == 10 else scope_stream,
                "estimated_hours": before_hours,
            },
            after_state={
                "subject_id": subject_id,
                "class_level": payload.class_level,
                "stream": None if payload.class_level == 10 else scope_stream,
                "estimated_hours": int(payload.estimated_hours),
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "subject_id": subject.id,
            "subject_name": subject.name,
            "class_level": payload.class_level,
            "stream": None if payload.class_level == 10 else scope_stream,
            "estimated_hours": int(scope.estimated_hours),
        }

    async def syllabus_completion_report(self) -> dict:
        scope_rows = (
            await self.session.execute(
                select(SubjectAcademicScope, Subject)
                .join(Subject, Subject.id == SubjectAcademicScope.subject_id)
                .order_by(
                    SubjectAcademicScope.class_level.asc(),
                    SubjectAcademicScope.stream.asc(),
                    Subject.name.asc(),
                )
            )
        ).all()

        completed_rows = (
            await self.session.execute(
                select(
                    LectureSchedule.class_level,
                    LectureSchedule.stream,
                    LectureSchedule.subject_id,
                    func.coalesce(func.sum(LectureSchedule.duration_minutes), 0).label("completed_minutes"),
                )
                .where(LectureSchedule.status == LectureScheduleStatus.DONE)
                .group_by(
                    LectureSchedule.class_level,
                    LectureSchedule.stream,
                    LectureSchedule.subject_id,
                )
            )
        ).all()

        completed_minutes_map: dict[tuple[int, str, str], int] = {}
        for class_level, stream, subject_id, completed_minutes in completed_rows:
            completed_minutes_map[(int(class_level), str(stream), str(subject_id))] = int(completed_minutes or 0)

        groups: dict[tuple[int, str], dict] = {}

        for scope, subject in scope_rows:
            class_level = int(scope.class_level)
            stream = "common" if class_level == 10 else str(scope.stream)
            scope_key = (class_level, stream)
            if scope_key not in groups:
                label = f"{class_level}th" if class_level == 10 else f"{class_level}th {stream.title()}"
                groups[scope_key] = {
                    "class_level": class_level,
                    "stream": None if class_level == 10 else stream,
                    "label": label,
                    "subjects": [],
                }

            estimated_hours = int(scope.estimated_hours or 0)
            completed_minutes = completed_minutes_map.get((class_level, stream, subject.id), 0)
            estimated_minutes = estimated_hours * 60
            completion_percentage = (
                round(min(100.0, (completed_minutes / estimated_minutes) * 100), 2)
                if estimated_minutes > 0
                else 0.0
            )

            groups[scope_key]["subjects"].append(
                {
                    "subject_id": subject.id,
                    "subject_name": subject.name,
                    "estimated_hours": estimated_hours,
                    "completed_hours": round(completed_minutes / 60, 2),
                    "completion_percentage": completion_percentage,
                }
            )

        defaults = self._default_subject_catalog()
        for scope_key, default_subjects in defaults.items():
            class_level, stream = scope_key
            if scope_key not in groups:
                label = f"{class_level}th" if class_level == 10 else f"{class_level}th {stream.title()}"
                groups[scope_key] = {
                    "class_level": class_level,
                    "stream": None if class_level == 10 else stream,
                    "label": label,
                    "subjects": [],
                }

            existing_names = {
                str(item["subject_name"]).strip().lower()
                for item in groups[scope_key]["subjects"]
            }
            for subject_name in default_subjects:
                if subject_name.strip().lower() in existing_names:
                    continue
                groups[scope_key]["subjects"].append(
                    {
                        "subject_id": None,
                        "subject_name": subject_name,
                        "estimated_hours": 0,
                        "completed_hours": 0.0,
                        "completion_percentage": 0.0,
                    }
                )

        ordered_keys = sorted(groups.keys(), key=lambda item: (item[0], {"common": 0, "science": 1, "commerce": 2}.get(item[1], 9)))
        result_groups: list[dict] = []
        for scope_key in ordered_keys:
            group = groups[scope_key]
            subjects = sorted(group["subjects"], key=lambda item: str(item["subject_name"]).lower())
            total_estimated_hours = int(sum(int(item["estimated_hours"]) for item in subjects))
            total_completed_hours = round(sum(float(item["completed_hours"]) for item in subjects), 2)
            overall_completion_percentage = (
                round(min(100.0, (total_completed_hours / total_estimated_hours) * 100), 2)
                if total_estimated_hours > 0
                else 0.0
            )

            result_groups.append(
                {
                    "class_level": group["class_level"],
                    "stream": group["stream"],
                    "label": group["label"],
                    "overall_completion_percentage": overall_completion_percentage,
                    "total_estimated_hours": total_estimated_hours,
                    "total_completed_hours": total_completed_hours,
                    "subjects": subjects,
                }
            )

        return {
            "groups": result_groups,
            "y_axis_ticks": [20, 40, 60, 80, 100],
            "generated_at": datetime.now(UTC),
        }

    async def list_attendance_corrections(
        self,
        *,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = (
            select(AttendanceCorrection, AttendanceRecord, StudentProfile, User)
            .join(AttendanceRecord, AttendanceRecord.id == AttendanceCorrection.attendance_record_id)
            .join(StudentProfile, StudentProfile.id == AttendanceRecord.student_id)
            .join(User, User.id == StudentProfile.user_id)
        )

        if status:
            query = query.where(AttendanceCorrection.status == status)

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(AttendanceCorrection.created_at.desc()).limit(limit).offset(offset)
            )
        ).all()

        return [
            {
                "id": correction.id,
                "attendance_record_id": correction.attendance_record_id,
                "student_id": profile.id,
                "student_name": user.full_name,
                "attendance_date": record.attendance_date,
                "current_status": record.status.value if hasattr(record.status, "value") else str(record.status),
                "requested_status": correction.status,
                "reason": correction.reason,
                "requested_by": correction.requested_by,
                "approved_by": correction.approved_by,
                "created_at": correction.created_at,
                "updated_at": correction.updated_at,
            }
            for correction, record, profile, user in rows
        ], total

    async def list_result_topics(
        self,
        *,
        class_level: int,
        stream: str | None,
        subject_id: str | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = (
            select(
                Assessment.id.label("assessment_id"),
                Assessment.title.label("assessment_title"),
                Assessment.topic.label("topic"),
                Assessment.class_level.label("class_level"),
                Assessment.stream.label("stream"),
                Assessment.starts_at.label("starts_at"),
                Assessment.ends_at.label("ends_at"),
                Assessment.created_at.label("created_at"),
                Assessment.total_marks.label("total_marks"),
                Assessment.passing_marks.label("passing_marks"),
                Subject.id.label("subject_id"),
                Subject.code.label("subject_code"),
                Subject.name.label("subject_name"),
                func.count(Result.id).label("submitted_count"),
                func.avg(Result.score).label("avg_score"),
                func.max(Result.score).label("max_score"),
                func.max(Result.published_at).label("last_published_at"),
                func.count(func.distinct(AssessmentQuestion.question_id)).label("question_count"),
            )
            .join(Result, Result.assessment_id == Assessment.id)
            .join(Subject, Subject.id == Assessment.subject_id)
            .outerjoin(AssessmentQuestion, AssessmentQuestion.assessment_id == Assessment.id)
            .where(Assessment.class_level == class_level)
        )

        if class_level in {11, 12}:
            normalized_stream = self._normalize_stream(stream)
            if normalized_stream not in {"science", "commerce"}:
                raise ForbiddenException("stream is required for class 11 and 12")
            query = query.where(Assessment.stream == normalized_stream)

        if subject_id:
            query = query.where(Assessment.subject_id == subject_id)

        if search:
            search_term = f"%{search.strip()}%"
            if search_term != "%%":
                query = query.where(
                    or_(
                        Assessment.title.ilike(search_term),
                        Assessment.topic.ilike(search_term),
                        Subject.name.ilike(search_term),
                        Subject.code.ilike(search_term),
                    )
                )

        grouped = query.group_by(
            Assessment.id,
            Assessment.title,
            Assessment.topic,
            Assessment.class_level,
            Assessment.stream,
            Assessment.starts_at,
            Assessment.ends_at,
            Assessment.created_at,
            Assessment.total_marks,
            Assessment.passing_marks,
            Subject.id,
            Subject.code,
            Subject.name,
        )

        total = (await self.session.execute(select(func.count()).select_from(grouped.subquery()))).scalar_one()

        rows = (
            await self.session.execute(
                grouped
                .order_by(
                    Subject.name.asc(),
                    case((Assessment.starts_at.is_(None), 1), else_=0).asc(),
                    Assessment.starts_at.desc(),
                    Assessment.created_at.desc(),
                )
                .limit(limit)
                .offset(offset)
            )
        ).all()

        items = [
            {
                "assessment_id": row.assessment_id,
                "assessment_title": row.assessment_title,
                "topic": row.topic,
                "class_level": row.class_level,
                "stream": row.stream,
                "starts_at": row.starts_at,
                "ends_at": row.ends_at,
                "created_at": row.created_at,
                "subject": {
                    "id": row.subject_id,
                    "code": row.subject_code,
                    "name": row.subject_name,
                },
                "question_count": int(row.question_count or 0),
                "submitted_count": int(row.submitted_count or 0),
                "avg_score": float(row.avg_score) if row.avg_score is not None else None,
                "max_score": float(row.max_score) if row.max_score is not None else None,
                "total_marks": float(row.total_marks or 0),
                "passing_marks": float(row.passing_marks or 0),
                "last_published_at": row.last_published_at,
            }
            for row in rows
        ]
        return items, total

    async def list_result_topic_students(
        self,
        *,
        assessment_id: str,
        search: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        assessment_row = (
            await self.session.execute(
                select(Assessment, Subject)
                .join(Subject, Subject.id == Assessment.subject_id)
                .where(Assessment.id == assessment_id)
            )
        ).first()
        if not assessment_row:
            raise NotFoundException("Assessment not found")

        assessment, subject = assessment_row

        rank_expr = func.dense_rank().over(
            order_by=(Result.score.desc(), Result.published_at.asc(), Result.student_id.asc())
        )

        query = (
            select(
                Result.id.label("result_id"),
                Result.student_id.label("student_id"),
                Result.score.label("score"),
                Result.total_marks.label("total_marks"),
                Result.rank.label("stored_rank"),
                Result.published_at.label("published_at"),
                User.full_name.label("student_name"),
                User.phone.label("student_phone"),
                StudentProfile.admission_no.label("admission_no"),
                StudentProfile.roll_no.label("roll_no"),
                StudentProfile.class_name.label("class_name"),
                StudentProfile.stream.label("student_stream"),
                StudentProfile.parent_contact_number.label("parent_contact_number"),
                rank_expr.label("computed_rank"),
            )
            .join(StudentProfile, StudentProfile.id == Result.student_id)
            .join(User, User.id == StudentProfile.user_id)
            .where(Result.assessment_id == assessment_id)
        )

        if search:
            search_term = f"%{search.strip()}%"
            if search_term != "%%":
                query = query.where(
                    or_(
                        User.full_name.ilike(search_term),
                        User.phone.ilike(search_term),
                        StudentProfile.admission_no.ilike(search_term),
                        StudentProfile.roll_no.ilike(search_term),
                        StudentProfile.parent_contact_number.ilike(search_term),
                    )
                )

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

        rows = (
            await self.session.execute(
                query.order_by(
                    Result.score.desc(),
                    Result.published_at.asc(),
                    User.full_name.asc(),
                )
                .limit(limit)
                .offset(offset)
            )
        ).all()

        items = []
        for row in rows:
            rank_value = int(row.stored_rank) if row.stored_rank is not None else int(row.computed_rank)
            score = float(row.score)
            total_marks = float(row.total_marks)
            percentage = round((score / total_marks) * 100, 2) if total_marks > 0 else 0.0
            items.append(
                {
                    "result_id": row.result_id,
                    "student": {
                        "id": row.student_id,
                        "name": row.student_name,
                        "phone": row.student_phone,
                        "admission_no": row.admission_no,
                        "roll_no": row.roll_no,
                        "class_name": row.class_name,
                        "stream": row.student_stream,
                        "parent_contact_number": row.parent_contact_number,
                    },
                    "score": score,
                    "total_marks": total_marks,
                    "percentage": percentage,
                    "rank": rank_value,
                    "published_at": row.published_at,
                }
            )

        return {
            "assessment": {
                "id": assessment.id,
                "title": assessment.title,
                "topic": assessment.topic,
                "class_level": assessment.class_level,
                "stream": assessment.stream,
                "starts_at": assessment.starts_at,
                "ends_at": assessment.ends_at,
                "subject": {
                    "id": subject.id,
                    "code": subject.code,
                    "name": subject.name,
                },
                "total_marks": float(assessment.total_marks or 0),
                "passing_marks": float(assessment.passing_marks or 0),
            },
            "items": items,
            "total": total,
        }

    def _build_result_whatsapp_message(
        self,
        *,
        assessment: Assessment,
        subject: Subject,
        student_name: str,
        class_name: str | None,
        stream: str | None,
        score: float,
        total_marks: float,
        percentage: float,
        rank: int,
        custom_message: str | None,
    ) -> str:
        if custom_message and custom_message.strip():
            return custom_message.strip()

        settings = get_settings()
        stream_text = stream if stream else "General"
        test_time = assessment.starts_at.isoformat() if assessment.starts_at else "-"
        lines = [
            settings.institute_display_name,
            "Student Assessment Result",
            f"Student: {student_name}",
            f"Class: {class_name or assessment.class_level or '-'} ({stream_text})",
            f"Subject: {subject.name}",
            f"Topic: {assessment.topic or assessment.title}",
            f"Test Time: {test_time}",
            f"Score: {score:.2f}/{total_marks:.2f} ({percentage:.2f}%)",
            f"Rank: {rank}",
        ]
        if settings.fee_payment_contact_number:
            lines.append(f"Support: {settings.fee_payment_contact_number}")
        return "\n".join(lines)

    async def send_student_result_whatsapp(
        self,
        *,
        assessment_id: str,
        student_id: str,
        payload: AdminResultWhatsappDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        row = (
            await self.session.execute(
                select(Result, Assessment, Subject, StudentProfile, User)
                .join(Assessment, Assessment.id == Result.assessment_id)
                .join(Subject, Subject.id == Assessment.subject_id)
                .join(StudentProfile, StudentProfile.id == Result.student_id)
                .join(User, User.id == StudentProfile.user_id)
                .where(Result.assessment_id == assessment_id, Result.student_id == student_id)
            )
        ).first()
        if not row:
            raise NotFoundException("Result not found for student")

        result, assessment, subject, profile, user = row

        rank_stmt = select(func.count(func.distinct(Result.score))).where(
            Result.assessment_id == assessment_id,
            Result.score > result.score,
        )
        higher_distinct_scores = (await self.session.execute(rank_stmt)).scalar_one() or 0
        rank = int(result.rank or (higher_distinct_scores + 1))

        score = float(result.score)
        total_marks = float(result.total_marks)
        percentage = round((score / total_marks) * 100, 2) if total_marks > 0 else 0.0

        target_phone = payload.phone or profile.parent_contact_number
        if not target_phone:
            raise ForbiddenException("Parent contact number is missing for WhatsApp delivery")

        message = self._build_result_whatsapp_message(
            assessment=assessment,
            subject=subject,
            student_name=user.full_name,
            class_name=profile.class_name,
            stream=profile.stream,
            score=score,
            total_marks=total_marks,
            percentage=percentage,
            rank=rank,
            custom_message=payload.message,
        )

        delivery = await self._send_whatsapp_text_message(
            to_phone=target_phone,
            message=message,
        )

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.result.whatsapp",
            entity_type="result",
            entity_id=result.id,
            before_state=None,
            after_state={
                "assessment_id": assessment.id,
                "student_id": student_id,
                "to_phone": delivery.get("to_phone"),
                "delivery_status": delivery.get("status"),
                "provider": delivery.get("provider"),
            },
            ip_address=ip_address,
        )
        await self.session.commit()

        return {
            "result_id": result.id,
            "assessment_id": assessment.id,
            "student_id": student_id,
            "to_phone": delivery.get("to_phone"),
            "delivery_status": delivery.get("status"),
            "provider": delivery.get("provider"),
            "provider_message_id": delivery.get("provider_message_id"),
        }

    async def list_results(
        self,
        *,
        assessment_id: str | None,
        batch_id: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = (
            select(
                Result.id.label("result_id"),
                Result.score.label("score"),
                Result.total_marks.label("total_marks"),
                Result.rank.label("rank"),
                Result.published_at.label("published_at"),
                Result.assessment_id.label("assessment_id"),
                Result.student_id.label("student_id"),
                Assessment.title.label("assessment_title"),
                User.full_name.label("student_name"),
                StudentProfile.admission_no.label("admission_no"),
                StudentProfile.roll_no.label("roll_no"),
                StudentProfile.current_batch_id.label("batch_id"),
            )
            .join(Assessment, Assessment.id == Result.assessment_id)
            .join(StudentProfile, StudentProfile.id == Result.student_id)
            .join(User, User.id == StudentProfile.user_id)
        )

        if assessment_id:
            query = query.where(Result.assessment_id == assessment_id)
        if batch_id:
            query = query.where(StudentProfile.current_batch_id == batch_id)

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(Result.published_at.desc()).limit(limit).offset(offset)
            )
        ).all()

        return [
            {
                "id": row.result_id,
                "assessment": {
                    "id": row.assessment_id,
                    "title": row.assessment_title,
                },
                "student": {
                    "id": row.student_id,
                    "name": row.student_name,
                    "admission_no": row.admission_no,
                    "roll_no": row.roll_no,
                    "batch_id": row.batch_id,
                },
                "score": float(row.score),
                "total_marks": float(row.total_marks),
                "rank": row.rank,
                "published_at": row.published_at,
            }
            for row in rows
        ], total

    async def list_banners(
        self,
        *,
        active_on: date | None,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = select(Banner)
        if active_on:
            query = query.where(func.date(Banner.active_from) <= active_on, func.date(Banner.active_to) >= active_on)
        if is_active is not None:
            query = query.where(Banner.is_active.is_(is_active))

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(Banner.priority.desc(), Banner.active_from.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()
        now = datetime.now(UTC)

        return [
            {
                "id": row.id,
                "title": row.title,
                "media_url": row.media_url,
                "action_url": row.action_url,
                "active_from": row.active_from,
                "active_to": row.active_to,
                "priority": row.priority,
                "is_popup": row.is_popup,
                "is_active": row.is_active,
                "is_live": bool(
                    row.is_active
                    and ensure_utc(row.active_from) is not None
                    and ensure_utc(row.active_to) is not None
                    and ensure_utc(row.active_from) <= now <= ensure_utc(row.active_to)
                ),
                "created_at": row.created_at,
            }
            for row in rows
        ], total

    async def upload_banner_image(
        self,
        *,
        file: UploadFile,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        content_type = (file.content_type or "").lower().strip()
        if content_type not in self._ALLOWED_BANNER_IMAGE_TYPES:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Only JPG, PNG, and WEBP images are allowed",
            )

        raw = await file.read()
        if not raw:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Uploaded banner image is empty",
            )

        max_upload_bytes = 15 * 1024 * 1024
        if len(raw) > max_upload_bytes:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Banner image is too large. Max supported size is 15MB",
            )

        stored_bytes, width, height = self._normalize_and_crop_banner(raw)

        media_dir, media_url = self._media_config()
        banner_dir = media_dir / "banners"
        banner_dir.mkdir(parents=True, exist_ok=True)

        stored_name = f"{uuid4().hex}.jpg"
        stored_path = banner_dir / stored_name
        stored_path.write_bytes(stored_bytes)

        relative_path = f"banners/{stored_name}"
        file_url = f"{media_url}/{relative_path}"
        display_name = self._safe_display_name(file.filename, "banner.jpg")

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.banner.upload",
            entity_type="banner_upload",
            entity_id=stored_name,
            before_state=None,
            after_state={
                "file_name": display_name,
                "storage_path": relative_path,
                "file_url": file_url,
                "width": width,
                "height": height,
            },
            ip_address=ip_address,
        )
        await self.session.commit()

        return {
            "file_name": display_name,
            "storage_path": relative_path,
            "file_url": file_url,
            "content_type": "image/jpeg",
            "file_size_bytes": len(stored_bytes),
            "width": width,
            "height": height,
        }

    async def create_banner(
        self,
        *,
        payload: AdminBannerCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        banner = Banner(
            title=payload.title,
            media_url=payload.media_url,
            action_url=payload.action_url,
            active_from=payload.active_from,
            active_to=payload.active_to,
            priority=payload.priority,
            is_popup=payload.is_popup,
            is_active=payload.is_active,
        )
        self.session.add(banner)
        await self.session.flush()

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.banner.create",
            entity_type="banner",
            entity_id=banner.id,
            before_state=None,
            after_state={
                "title": banner.title,
                "active_from": banner.active_from,
                "active_to": banner.active_to,
                "priority": banner.priority,
                "is_popup": banner.is_popup,
                "is_active": banner.is_active,
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "id": banner.id,
            "title": banner.title,
            "media_url": banner.media_url,
            "action_url": banner.action_url,
            "active_from": banner.active_from,
            "active_to": banner.active_to,
            "priority": banner.priority,
            "is_popup": banner.is_popup,
            "is_active": banner.is_active,
        }

    async def update_banner(
        self,
        *,
        banner_id: str,
        payload: AdminBannerUpdateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        banner = await self.session.get(Banner, banner_id)
        if not banner:
            raise NotFoundException("Banner not found")

        before = {
            "title": banner.title,
            "media_url": banner.media_url,
            "action_url": banner.action_url,
            "active_from": banner.active_from,
            "active_to": banner.active_to,
            "priority": banner.priority,
            "is_popup": banner.is_popup,
            "is_active": banner.is_active,
        }

        if payload.title is not None:
            banner.title = payload.title
        if payload.media_url is not None:
            banner.media_url = payload.media_url
        if payload.action_url is not None:
            banner.action_url = payload.action_url
        if payload.active_from is not None:
            banner.active_from = payload.active_from
        if payload.active_to is not None:
            banner.active_to = payload.active_to
        if payload.priority is not None:
            banner.priority = payload.priority
        if payload.is_popup is not None:
            banner.is_popup = payload.is_popup
        if payload.is_active is not None:
            banner.is_active = payload.is_active

        if banner.active_to <= banner.active_from:
            raise ValueError("active_to must be greater than active_from")

        after = {
            "title": banner.title,
            "media_url": banner.media_url,
            "action_url": banner.action_url,
            "active_from": banner.active_from,
            "active_to": banner.active_to,
            "priority": banner.priority,
            "is_popup": banner.is_popup,
            "is_active": banner.is_active,
        }

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.banner.update",
            entity_type="banner",
            entity_id=banner.id,
            before_state=before,
            after_state=after,
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "id": banner.id,
            "title": banner.title,
            "media_url": banner.media_url,
            "action_url": banner.action_url,
            "active_from": banner.active_from,
            "active_to": banner.active_to,
            "priority": banner.priority,
            "is_popup": banner.is_popup,
            "is_active": banner.is_active,
        }

    async def list_daily_thoughts(
        self,
        *,
        from_date: date | None,
        to_date: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = select(DailyThought)
        if from_date:
            query = query.where(DailyThought.thought_date >= from_date)
        if to_date:
            query = query.where(DailyThought.thought_date <= to_date)

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(DailyThought.thought_date.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()

        return [
            {
                "id": row.id,
                "thought_date": row.thought_date,
                "text": row.text,
                "is_active": row.is_active,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ], total

    async def upsert_daily_thought(
        self,
        *,
        payload: AdminDailyThoughtUpsertDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        stmt = select(DailyThought).where(DailyThought.thought_date == payload.thought_date)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()

        if existing:
            before = {
                "text": existing.text,
                "is_active": existing.is_active,
            }
            existing.text = payload.text
            existing.is_active = payload.is_active
            thought = existing
            action = "admin.daily_thought.update"
        else:
            thought = DailyThought(
                thought_date=payload.thought_date,
                text=payload.text,
                is_active=payload.is_active,
            )
            self.session.add(thought)
            await self.session.flush()
            before = None
            action = "admin.daily_thought.create"

        await self._audit(
            actor_user_id=actor_user_id,
            action=action,
            entity_type="daily_thought",
            entity_id=thought.id,
            before_state=before,
            after_state={
                "thought_date": thought.thought_date,
                "text": thought.text,
                "is_active": thought.is_active,
            },
            ip_address=ip_address,
        )

        await self.session.commit()
        await self.session.refresh(thought)

        return {
            "id": thought.id,
            "thought_date": thought.thought_date,
            "text": thought.text,
            "is_active": thought.is_active,
            "updated_at": thought.updated_at,
        }

    async def list_audit_logs(
        self,
        *,
        action: str | None,
        entity_type: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = select(AuditLog)
        if action:
            query = query.where(AuditLog.action == action)
        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()

        return [
            {
                "id": row.id,
                "actor_user_id": row.actor_user_id,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "before_state": row.before_state,
                "after_state": row.after_state,
                "ip_address": row.ip_address,
                "created_at": row.created_at,
            }
            for row in rows
        ], total

    async def list_parents(
        self,
        *,
        search: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = (
            select(ParentProfile, User, func.count(ParentStudentLink.id).label("linked_students_count"))
            .join(User, User.id == ParentProfile.user_id)
            .outerjoin(
                ParentStudentLink,
                and_(
                    ParentStudentLink.parent_id == ParentProfile.id,
                    ParentStudentLink.is_active.is_(True),
                ),
            )
            .group_by(ParentProfile.id, User.id)
        )

        if search:
            query = query.where(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                    User.phone.ilike(f"%{search}%"),
                )
            )

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(User.created_at.desc()).limit(limit).offset(offset)
            )
        ).all()

        return [
            {
                "parent_id": parent.id,
                "user_id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "linked_students_count": int(linked_students_count or 0),
                "created_at": parent.created_at,
            }
            for parent, user, linked_students_count in rows
        ], total

    async def list_parent_links(
        self,
        *,
        parent_id: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        parent = await self.session.get(ParentProfile, parent_id)
        if not parent:
            raise NotFoundException("Parent profile not found")

        query = (
            select(ParentStudentLink, StudentProfile, User)
            .join(StudentProfile, StudentProfile.id == ParentStudentLink.student_id)
            .join(User, User.id == StudentProfile.user_id)
            .where(ParentStudentLink.parent_id == parent_id)
        )

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(ParentStudentLink.is_primary.desc(), ParentStudentLink.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()

        return [
            {
                "link_id": link.id,
                "student_id": student.id,
                "student_user_id": user.id,
                "student_name": user.full_name,
                "admission_no": student.admission_no,
                "roll_no": student.roll_no,
                "relation_type": link.relation_type,
                "is_primary": link.is_primary,
                "is_active": link.is_active,
                "created_at": link.created_at,
            }
            for link, student, user in rows
        ], total

    async def create_parent_link(
        self,
        *,
        payload: AdminParentLinkCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        parent_user = await self.session.get(User, payload.parent_user_id)
        if not parent_user:
            raise NotFoundException("Parent user not found")

        has_parent_role = (
            await self.session.execute(
                select(Role.id)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == parent_user.id, Role.code == RoleCode.PARENT)
            )
        ).scalar_one_or_none()
        if not has_parent_role:
            raise ForbiddenException("User does not have parent role")

        student = await self.session.get(StudentProfile, payload.student_id)
        if not student:
            raise NotFoundException("Student profile not found")

        parent_profile = (
            await self.session.execute(select(ParentProfile).where(ParentProfile.user_id == parent_user.id))
        ).scalar_one_or_none()
        if not parent_profile:
            parent_profile = ParentProfile(user_id=parent_user.id)
            self.session.add(parent_profile)
            await self.session.flush()

        existing = (
            await self.session.execute(
                select(ParentStudentLink).where(
                    ParentStudentLink.parent_id == parent_profile.id,
                    ParentStudentLink.student_id == student.id,
                )
            )
        ).scalar_one_or_none()
        if existing and existing.is_active:
            raise ForbiddenException("Parent is already linked to this student")

        if payload.is_primary:
            await self.session.execute(
                select(ParentStudentLink)
                .where(
                    ParentStudentLink.parent_id == parent_profile.id,
                    ParentStudentLink.is_primary.is_(True),
                )
            )
            active_links = (
                await self.session.execute(
                    select(ParentStudentLink).where(ParentStudentLink.parent_id == parent_profile.id)
                )
            ).scalars().all()
            for link in active_links:
                link.is_primary = False

        if existing and not existing.is_active:
            before = {
                "relation_type": existing.relation_type,
                "is_primary": existing.is_primary,
                "is_active": existing.is_active,
            }
            existing.relation_type = payload.relation_type
            existing.is_primary = payload.is_primary
            existing.is_active = True
            link = existing
            action = "admin.parent.link.reactivate"
        else:
            link = ParentStudentLink(
                parent_id=parent_profile.id,
                student_id=student.id,
                relation_type=payload.relation_type,
                is_primary=payload.is_primary,
                is_active=True,
            )
            self.session.add(link)
            await self.session.flush()
            before = None
            action = "admin.parent.link.create"

        await self._audit(
            actor_user_id=actor_user_id,
            action=action,
            entity_type="parent_student_link",
            entity_id=link.id,
            before_state=before,
            after_state={
                "parent_id": parent_profile.id,
                "parent_user_id": parent_user.id,
                "student_id": student.id,
                "relation_type": link.relation_type,
                "is_primary": link.is_primary,
                "is_active": link.is_active,
            },
            ip_address=ip_address,
        )

        await self.session.commit()
        await self.session.refresh(link)

        return {
            "link_id": link.id,
            "parent_id": parent_profile.id,
            "parent_user_id": parent_user.id,
            "student_id": student.id,
            "relation_type": link.relation_type,
            "is_primary": link.is_primary,
            "is_active": link.is_active,
            "created_at": link.created_at,
        }

    @staticmethod
    def _normalize_fee_stream(stream: str | None) -> str | None:
        value = (stream or "").strip().lower()
        if value in {"", "none", "null"}:
            return None
        if value in {"science", "sci"}:
            return "science"
        if value in {"commerce", "comm"}:
            return "commerce"
        return value

    @staticmethod
    def _stream_for_display(class_level: int | None, stream: str | None) -> str:
        normalized = AdminService._normalize_fee_stream(stream)
        if class_level == 10:
            return "general science"
        return normalized or "-"

    @staticmethod
    def _validate_fee_structure_stream(*, class_level: int, stream: str | None) -> None:
        if class_level <= 10 and stream is not None:
            raise ForbiddenException("Stream is not allowed for class 10 and below fee structure")
        if class_level in {11, 12} and stream not in {"science", "commerce"}:
            raise ForbiddenException("Class 11 and 12 fee structure requires stream: science or commerce")

    async def list_fee_structures(
        self,
        *,
        class_level: int | None,
        stream: str | None,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = select(FeeStructure)

        normalized_stream = self._normalize_fee_stream(stream)
        if class_level is not None:
            query = query.where(FeeStructure.class_level == class_level)
        if normalized_stream is not None:
            query = query.where(FeeStructure.stream == normalized_stream)
        if is_active is not None:
            query = query.where(FeeStructure.is_active.is_(is_active))

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(FeeStructure.class_level.asc(), FeeStructure.stream.asc().nullsfirst(), FeeStructure.name.asc())
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()

        items = [
            {
                "id": row.id,
                "name": row.name,
                "class_level": row.class_level,
                "stream": row.stream,
                "total_amount": float(row.total_amount),
                "installment_count": row.installment_count,
                "description": row.description,
                "is_active": row.is_active,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]
        return items, total

    async def create_fee_structure(
        self,
        *,
        payload: AdminFeeStructureCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        normalized_stream = self._normalize_fee_stream(payload.stream)
        self._validate_fee_structure_stream(class_level=payload.class_level, stream=normalized_stream)

        stream_filter = FeeStructure.stream.is_(None) if normalized_stream is None else FeeStructure.stream == normalized_stream
        duplicate_stmt = select(FeeStructure).where(
            FeeStructure.class_level == payload.class_level,
            stream_filter,
            FeeStructure.is_active.is_(True),
        )
        duplicate = (await self.session.execute(duplicate_stmt)).scalar_one_or_none()
        if duplicate and payload.is_active:
            raise ForbiddenException("An active fee structure already exists for this class and stream")

        structure = FeeStructure(
            name=payload.name.strip(),
            class_level=payload.class_level,
            stream=normalized_stream,
            total_amount=payload.total_amount,
            installment_count=payload.installment_count,
            description=payload.description,
            is_active=payload.is_active,
        )
        self.session.add(structure)
        await self.session.flush()

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.fee_structure.create",
            entity_type="fee_structure",
            entity_id=structure.id,
            before_state=None,
            after_state={
                "name": structure.name,
                "class_level": structure.class_level,
                "stream": structure.stream,
                "total_amount": float(structure.total_amount),
                "installment_count": structure.installment_count,
                "is_active": structure.is_active,
            },
            ip_address=ip_address,
        )

        await self.session.commit()
        await self.session.refresh(structure)

        return {
            "id": structure.id,
            "name": structure.name,
            "class_level": structure.class_level,
            "stream": structure.stream,
            "total_amount": float(structure.total_amount),
            "installment_count": structure.installment_count,
            "description": structure.description,
            "is_active": structure.is_active,
            "created_at": structure.created_at,
        }

    async def update_fee_structure(
        self,
        *,
        structure_id: str,
        payload: AdminFeeStructureUpdateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        structure = await self.session.get(FeeStructure, structure_id)
        if not structure:
            raise NotFoundException("Fee structure not found")

        before = {
            "name": structure.name,
            "class_level": structure.class_level,
            "stream": structure.stream,
            "total_amount": float(structure.total_amount),
            "installment_count": structure.installment_count,
            "description": structure.description,
            "is_active": structure.is_active,
        }

        next_class_level = payload.class_level if payload.class_level is not None else structure.class_level
        next_stream = self._normalize_fee_stream(payload.stream) if payload.stream is not None else structure.stream
        next_is_active = payload.is_active if payload.is_active is not None else structure.is_active

        self._validate_fee_structure_stream(class_level=next_class_level, stream=next_stream)

        stream_filter = FeeStructure.stream.is_(None) if next_stream is None else FeeStructure.stream == next_stream
        duplicate_stmt = select(FeeStructure).where(
            FeeStructure.id != structure.id,
            FeeStructure.class_level == next_class_level,
            stream_filter,
            FeeStructure.is_active.is_(True),
        )
        duplicate = (await self.session.execute(duplicate_stmt)).scalar_one_or_none()
        if duplicate and next_is_active:
            raise ForbiddenException("Another active fee structure already exists for this class and stream")

        if payload.name is not None:
            structure.name = payload.name.strip()
        if payload.class_level is not None:
            structure.class_level = payload.class_level
        if payload.stream is not None:
            structure.stream = next_stream
        if payload.total_amount is not None:
            structure.total_amount = payload.total_amount
        if payload.installment_count is not None:
            structure.installment_count = payload.installment_count
        if payload.description is not None:
            structure.description = payload.description
        if payload.is_active is not None:
            structure.is_active = payload.is_active

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.fee_structure.update",
            entity_type="fee_structure",
            entity_id=structure.id,
            before_state=before,
            after_state={
                "name": structure.name,
                "class_level": structure.class_level,
                "stream": structure.stream,
                "total_amount": float(structure.total_amount),
                "installment_count": structure.installment_count,
                "description": structure.description,
                "is_active": structure.is_active,
            },
            ip_address=ip_address,
        )

        await self.session.commit()
        await self.session.refresh(structure)

        return {
            "id": structure.id,
            "name": structure.name,
            "class_level": structure.class_level,
            "stream": structure.stream,
            "total_amount": float(structure.total_amount),
            "installment_count": structure.installment_count,
            "description": structure.description,
            "is_active": structure.is_active,
            "updated_at": structure.updated_at,
        }

    async def delete_fee_structure(
        self,
        *,
        structure_id: str,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        structure = await self.session.get(FeeStructure, structure_id)
        if not structure:
            raise NotFoundException("Fee structure not found")

        before = {
            "name": structure.name,
            "class_level": structure.class_level,
            "stream": structure.stream,
            "total_amount": float(structure.total_amount),
            "installment_count": structure.installment_count,
            "description": structure.description,
            "is_active": structure.is_active,
        }

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.fee_structure.delete",
            entity_type="fee_structure",
            entity_id=structure.id,
            before_state=before,
            after_state=None,
            ip_address=ip_address,
        )

        await self.session.delete(structure)
        await self.session.commit()

        return {"id": structure_id, "deleted": True}

    @staticmethod
    def _student_payment_rollup_subquery():
        return (
            select(
                PaymentTransaction.student_id.label("student_id"),
                func.coalesce(
                    func.sum(case((PaymentTransaction.status == "success", PaymentTransaction.amount), else_=0)),
                    0,
                ).label("paid_amount"),
                func.coalesce(
                    func.sum(case((PaymentTransaction.status == "success", 1), else_=0)),
                    0,
                ).label("installments_paid_count"),
                func.max(case((PaymentTransaction.status == "success", PaymentTransaction.paid_at), else_=None)).label(
                    "last_paid_at"
                ),
            )
            .group_by(PaymentTransaction.student_id)
            .subquery()
        )

    @staticmethod
    def _build_fee_invoice_no(student_id: str) -> str:
        # Keep invoice/receipt IDs short and readable for admins/parents.
        now_local = datetime.now(app_timezone())
        student_tag = re.sub(r"[^A-Z0-9]", "", (student_id or "").upper())[:3] or "STD"
        return f"FR-{now_local.strftime('%y%m%d')}-{student_tag}{uuid4().hex[:4].upper()}"

    async def _build_unique_payment_external_ref(self, *, provider: str, external_ref: str | None) -> str | None:
        normalized = (external_ref or "").strip()
        if not normalized:
            return None

        candidate = normalized[:120]
        exists = (
            await self.session.execute(
                select(PaymentTransaction.id).where(
                    PaymentTransaction.provider == provider,
                    PaymentTransaction.external_ref == candidate,
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            return candidate

        base = candidate[:110]
        for _ in range(10):
            retry_candidate = f"{base}-{uuid4().hex[:8].upper()}"[:120]
            retry_exists = (
                await self.session.execute(
                    select(PaymentTransaction.id).where(
                        PaymentTransaction.provider == provider,
                        PaymentTransaction.external_ref == retry_candidate,
                    )
                )
            ).scalar_one_or_none()
            if retry_exists is None:
                return retry_candidate

        return f"PMT-{uuid4().hex[:24].upper()}"[:120]

    @staticmethod
    def _compute_fee_progress(*, fee_amount: float | None, paid_amount: float) -> tuple[float, float, bool]:
        if fee_amount is None:
            return 0.0, 0.0, False

        normalized_fee = max(float(fee_amount), 0.0)
        normalized_paid = max(min(float(paid_amount), normalized_fee), 0.0)
        pending = max(normalized_fee - normalized_paid, 0.0)
        is_fully_paid = normalized_fee > 0 and pending <= 0.0001
        return normalized_paid, pending, is_fully_paid

    @staticmethod
    def _format_inr(value: float) -> str:
        return f"INR {float(value):,.2f}"

    @staticmethod
    def _escape_pdf_text(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    @classmethod
    def _build_text_pdf(cls, lines: list[str]) -> bytes:
        safe_lines = [cls._escape_pdf_text((line or "").strip()) for line in lines if (line or "").strip()]
        if not safe_lines:
            safe_lines = ["No data available"]

        stream_rows = ["BT", "/F1 11 Tf", "14 TL", "50 800 Td"]
        for index, line in enumerate(safe_lines):
            if index == 0:
                stream_rows.append(f"({line}) Tj")
            else:
                stream_rows.append(f"T* ({line}) Tj")
        stream_rows.append("ET")
        stream = "\n".join(stream_rows).encode("latin-1", errors="replace")

        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream",
        ]

        payload = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets: list[int] = []
        for idx, obj in enumerate(objects, start=1):
            offsets.append(len(payload))
            payload.extend(f"{idx} 0 obj\n".encode("ascii"))
            payload.extend(obj)
            payload.extend(b"\nendobj\n")

        xref_start = len(payload)
        payload.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        payload.extend(b"0000000000 65535 f \n")
        for off in offsets:
            payload.extend(f"{off:010d} 00000 n \n".encode("ascii"))

        payload.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii"))
        payload.extend(f"startxref\n{xref_start}\n%%EOF\n".encode("ascii"))
        return bytes(payload)


    @classmethod
    def _build_report_card_pdf(
        cls,
        *,
        institute_name: str,
        generated_at: datetime,
        detail: dict,
        subject_performance: list[dict[str, float | int | str]],
        recent_results: list[dict[str, str | float]],
    ) -> bytes:
        def clamp_percentage(value: float) -> float:
            return max(0.0, min(float(value or 0), 100.0))

        def as_str(value: object, fallback: str = "-") -> str:
            text_value = str(value).strip() if value is not None else ""
            return text_value or fallback

        progress = detail.get("progress") or {}
        attendance = detail.get("attendance") or {}
        fee = detail.get("fee") or {}

        progress_pct = clamp_percentage(float(progress.get("percentage") or 0))
        attendance_pct = clamp_percentage(float(attendance.get("percentage") or 0))

        subject_rows = subject_performance[:6]
        chart_rows = subject_performance[:4]

        commands: list[str] = []

        def rect(
            x: float,
            y: float,
            w: float,
            h: float,
            *,
            fill: tuple[float, float, float] | None = None,
            stroke: tuple[float, float, float] | None = None,
            line_width: float = 1.0,
        ) -> None:
            if fill is not None:
                commands.append(f"{fill[0]:.3f} {fill[1]:.3f} {fill[2]:.3f} rg")
                commands.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re f")
            if stroke is not None:
                commands.append(f"{stroke[0]:.3f} {stroke[1]:.3f} {stroke[2]:.3f} RG")
                commands.append(f"{line_width:.2f} w")
                commands.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re S")

        def text_at(
            x: float,
            y: float,
            value: str,
            *,
            font: str = "F1",
            size: int = 10,
            color: tuple[float, float, float] = (0.17, 0.12, 0.29),
        ) -> None:
            safe = cls._escape_pdf_text(as_str(value, ""))
            commands.append(f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} rg")
            commands.append("BT")
            commands.append(f"/{font} {size} Tf")
            commands.append(f"1 0 0 1 {x:.2f} {y:.2f} Tm")
            commands.append(f"({safe}) Tj")
            commands.append("ET")

        rect(28, 760, 539, 58, fill=(0.95, 0.92, 1.00), stroke=(0.79, 0.70, 0.96))
        text_at(42, 796, as_str(institute_name, "Institute"), font="F2", size=15, color=(0.25, 0.16, 0.50))
        text_at(42, 778, "Student Report Card", font="F2", size=18, color=(0.19, 0.12, 0.41))
        text_at(
            360,
            796,
            f"Generated: {generated_at.strftime('%d-%b-%Y %I:%M %p IST')}",
            font="F1",
            size=9,
            color=(0.37, 0.30, 0.56),
        )

        rect(28, 620, 350, 126, fill=(1.00, 1.00, 1.00), stroke=(0.86, 0.80, 0.97))
        text_at(40, 730, "Student Information", font="F2", size=11, color=(0.28, 0.20, 0.49))
        text_at(40, 708, f"Name: {as_str(detail.get('full_name'))}")
        text_at(40, 690, f"Class: {as_str(detail.get('class_name'))}")
        text_at(40, 672, f"Stream: {as_str(detail.get('stream'))}")
        text_at(40, 654, f"Admission No: {as_str(detail.get('admission_no'))}")
        text_at(210, 654, f"Roll No: {as_str(detail.get('roll_no'))}")
        text_at(40, 636, f"Student Contact: {as_str(detail.get('phone'))}")
        text_at(40, 622, f"Parent Contact: {as_str(detail.get('parent_contact_number'))}")

        rect(390, 620, 177, 126, fill=(1.00, 1.00, 1.00), stroke=(0.86, 0.80, 0.97))
        text_at(402, 730, "Performance Snapshot", font="F2", size=11, color=(0.28, 0.20, 0.49))
        text_at(402, 708, f"Attendance: {attendance_pct:.2f}%", font="F2", size=10)
        text_at(402, 690, f"Progress: {progress_pct:.2f}%", font="F2", size=10)
        text_at(402, 672, f"Tests Taken: {int(progress.get('tests_taken') or 0)}", size=10)
        text_at(402, 654, f"Fee Pending: {cls._format_inr(float(fee.get('pending_amount') or 0))}", size=10)
        text_at(402, 636, f"Fee Status: {as_str(fee.get('status'))}", size=10)

        rect(28, 362, 539, 246, fill=(1.00, 1.00, 1.00), stroke=(0.86, 0.80, 0.97))
        text_at(40, 592, "Subject Performance Summary", font="F2", size=11, color=(0.28, 0.20, 0.49))
        rect(40, 564, 515, 24, fill=(0.95, 0.92, 1.00), stroke=(0.86, 0.80, 0.97))
        text_at(48, 572, "Subject", font="F2", size=9, color=(0.30, 0.22, 0.54))
        text_at(292, 572, "Attempts", font="F2", size=9, color=(0.30, 0.22, 0.54))
        text_at(376, 572, "Average %", font="F2", size=9, color=(0.30, 0.22, 0.54))
        text_at(468, 572, "Best %", font="F2", size=9, color=(0.30, 0.22, 0.54))

        if not subject_rows:
            text_at(48, 542, "No test performance data available yet.", size=10, color=(0.45, 0.38, 0.60))
        else:
            row_y = 542
            for index, row in enumerate(subject_rows):
                if index % 2 == 1:
                    rect(40, row_y - 4, 515, 22, fill=(0.99, 0.97, 1.00))
                text_at(48, row_y, as_str(row.get('subject'))[:38], size=10)
                text_at(300, row_y, str(int(row.get('attempts') or 0)), size=10)
                avg_value = clamp_percentage(float(row.get('average_percentage') or 0))
                best_value = clamp_percentage(float(row.get('best_percentage') or 0))
                text_at(382, row_y, f"{avg_value:.2f}%", size=10)
                text_at(474, row_y, f"{best_value:.2f}%", size=10)
                row_y -= 24

        rect(28, 192, 539, 156, fill=(1.00, 1.00, 1.00), stroke=(0.86, 0.80, 0.97))
        text_at(40, 332, "Subject Average Chart", font="F2", size=11, color=(0.28, 0.20, 0.49))

        if not chart_rows:
            text_at(48, 306, "Chart will appear after test attempts are recorded.", size=10, color=(0.45, 0.38, 0.60))
        else:
            chart_row_y = 300
            for row in chart_rows:
                label = as_str(row.get('subject'))[:16]
                avg_value = clamp_percentage(float(row.get('average_percentage') or 0))
                text_at(48, chart_row_y + 2, label, size=9)
                rect(182, chart_row_y, 310, 14, fill=(0.94, 0.92, 0.98), stroke=(0.85, 0.80, 0.95))
                rect(182, chart_row_y, 3.10 * avg_value, 14, fill=(0.62, 0.49, 0.93))
                text_at(500, chart_row_y + 2, f"{avg_value:.1f}%", size=9)
                chart_row_y -= 28

        rect(28, 30, 539, 146, fill=(1.00, 1.00, 1.00), stroke=(0.86, 0.80, 0.97))
        text_at(40, 160, "Recent Test Attempts", font="F2", size=11, color=(0.28, 0.20, 0.49))
        if not recent_results:
            text_at(48, 136, "No attempts recorded yet.", size=10, color=(0.45, 0.38, 0.60))
        else:
            y_cursor = 136
            for item in recent_results[:5]:
                text_at(
                    48,
                    y_cursor,
                    f"{as_str(item.get('date'))}  |  {as_str(item.get('subject'))}  |  {as_str(item.get('title'))[:24]}",
                    size=9,
                )
                text_at(476, y_cursor, f"{clamp_percentage(float(item.get('percentage') or 0)):.1f}%", font="F2", size=9)
                y_cursor -= 22

        stream = "\n".join(commands).encode("latin-1", errors="replace")

        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream",
        ]

        payload = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets: list[int] = []
        for idx, obj in enumerate(objects, start=1):
            offsets.append(len(payload))
            payload.extend(f"{idx} 0 obj\n".encode("ascii"))
            payload.extend(obj)
            payload.extend(b"\nendobj\n")

        xref_start = len(payload)
        payload.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        payload.extend(b"0000000000 65535 f \n")
        for off in offsets:
            payload.extend(f"{off:010d} 00000 n \n".encode("ascii"))

        payload.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii"))
        payload.extend(f"startxref\n{xref_start}\n%%EOF\n".encode("ascii"))
        return bytes(payload)

    @staticmethod
    def _normalize_whatsapp_phone(phone: str | None) -> str | None:
        if not phone:
            return None
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 10:
            return f"91{digits}"
        if len(digits) == 11 and digits.startswith("0"):
            return f"91{digits[1:]}"
        if len(digits) >= 11:
            return digits
        return None

    @staticmethod
    def _media_config() -> tuple[Path, str]:
        settings = get_settings()
        media_dir = Path(settings.media_base_dir).expanduser().resolve()
        media_dir.mkdir(parents=True, exist_ok=True)
        media_url = settings.media_base_url.strip() or "/media"
        if not media_url.startswith("/"):
            media_url = f"/{media_url}"
        return media_dir, media_url.rstrip("/")

    async def _load_fee_receipt_context(self, *, student_id: str) -> dict:
        student_row = (
            await self.session.execute(
                select(StudentProfile, User, Batch, Standard, StudentFeeStructureAssignment, FeeStructure)
                .join(User, User.id == StudentProfile.user_id)
                .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
                .outerjoin(Standard, Standard.id == Batch.standard_id)
                .outerjoin(
                    StudentFeeStructureAssignment,
                    and_(
                        StudentFeeStructureAssignment.student_id == StudentProfile.id,
                        StudentFeeStructureAssignment.is_active.is_(True),
                    ),
                )
                .outerjoin(FeeStructure, FeeStructure.id == StudentFeeStructureAssignment.fee_structure_id)
                .where(StudentProfile.id == student_id)
            )
        ).first()
        if not student_row:
            raise NotFoundException("Student not found")

        profile, user, _batch, standard, assignment, structure = student_row
        class_name = profile.class_name or (standard.name if standard else "-")
        grade = self._extract_grade(profile.class_name, standard.name if standard else None)
        class_level = int(grade) if grade is not None else None

        if assignment is None or structure is None:
            raise ForbiddenException("Assign fee structure first")

        payment_rows = (
            await self.session.execute(
                select(PaymentTransaction, FeeInvoice)
                .join(FeeInvoice, FeeInvoice.id == PaymentTransaction.invoice_id)
                .where(
                    PaymentTransaction.student_id == student_id,
                    PaymentTransaction.status == "success",
                )
                .order_by(PaymentTransaction.paid_at.asc(), PaymentTransaction.created_at.asc())
            )
        ).all()

        fee_amount = float(structure.total_amount)
        paid_total_raw = sum(float(tx.amount or 0) for tx, _ in payment_rows)
        paid_amount, pending_amount, is_fully_paid = self._compute_fee_progress(
            fee_amount=fee_amount,
            paid_amount=paid_total_raw,
        )

        return {
            "student_id": profile.id,
            "student_name": user.full_name,
            "student_phone": user.phone,
            "parent_contact_number": profile.parent_contact_number,
            "class_name": class_name,
            "stream": self._stream_for_display(class_level, profile.stream),
            "fee_structure_id": structure.id,
            "fee_structure_name": structure.name,
            "fee_amount": fee_amount,
            "installment_target_count": int(structure.installment_count),
            "payment_rows": payment_rows,
            "paid_amount": paid_amount,
            "pending_amount": pending_amount,
            "is_fully_paid": is_fully_paid,
        }

    def _extract_existing_receipt(self, *, context: dict) -> dict | None:
        payment_rows = context["payment_rows"]
        if not payment_rows:
            return None

        latest_tx, _ = payment_rows[-1]
        metadata = latest_tx.metadata_json if isinstance(latest_tx.metadata_json, dict) else {}
        receipt = metadata.get("receipt") if isinstance(metadata, dict) else None
        if not isinstance(receipt, dict):
            return None

        file_name = receipt.get("file_name")
        if not file_name:
            return None

        media_dir, media_url = self._media_config()
        file_path = media_dir / "receipts" / file_name
        if not file_path.exists():
            return None

        download_url = receipt.get("download_url") or f"{media_url}/receipts/{file_name}"
        return {
            "file_name": file_name,
            "download_url": download_url,
            "generated_at": receipt.get("generated_at") or latest_tx.updated_at.isoformat(),
            "invoice_no": receipt.get("invoice_no"),
            "payment_id": latest_tx.id,
        }

    @staticmethod
    def _read_jpeg_size(jpeg_bytes: bytes) -> tuple[int, int] | None:
        if len(jpeg_bytes) < 4 or jpeg_bytes[0:2] != b"\xFF\xD8":
            return None

        index = 2
        sof_markers = {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }

        while index + 9 < len(jpeg_bytes):
            if jpeg_bytes[index] != 0xFF:
                index += 1
                continue

            marker = jpeg_bytes[index + 1]
            index += 2

            if marker in {0xD8, 0xD9}:
                continue
            if index + 2 > len(jpeg_bytes):
                break

            segment_length = int.from_bytes(jpeg_bytes[index : index + 2], "big")
            if segment_length < 2 or index + segment_length > len(jpeg_bytes):
                break

            if marker in sof_markers and index + 7 <= len(jpeg_bytes):
                height = int.from_bytes(jpeg_bytes[index + 3 : index + 5], "big")
                width = int.from_bytes(jpeg_bytes[index + 5 : index + 7], "big")
                if width > 0 and height > 0:
                    return width, height

            index += segment_length

        return None

    @classmethod
    def _load_fee_receipt_logo_jpeg(cls) -> tuple[bytes, int, int] | None:
        settings = get_settings()
        project_root = Path(__file__).resolve().parents[3]

        candidates: list[Path] = []
        custom_logo = settings.institute_logo_path.strip()
        if custom_logo:
            candidates.append(Path(custom_logo).expanduser())

        candidates.extend(
            [
                project_root / "admin_web/public/branding/adrika-logo.jpg",
                project_root / "admin_web/public/branding/adrika-logo.jpeg",
                project_root / "admin_web/public/branding/adrika-logo.png",
                project_root / "mobile_app/assets/branding/adrika_logo.png",
            ]
        )

        for path in candidates:
            try:
                if not path.exists() or not path.is_file():
                    continue

                suffix = path.suffix.lower()
                if suffix in {".jpg", ".jpeg"}:
                    data = path.read_bytes()
                    size = cls._read_jpeg_size(data)
                    if size:
                        return data, size[0], size[1]
                    continue

                if suffix in {".png", ".webp"} and Image is not None:
                    with Image.open(path) as image:
                        if image.mode not in {"RGB", "L"}:
                            image = image.convert("RGB")
                        elif image.mode == "L":
                            image = image.convert("RGB")
                        width, height = image.size
                        if width <= 0 or height <= 0:
                            continue
                        buffer = BytesIO()
                        image.save(buffer, format="JPEG", quality=88, optimize=True)
                        return buffer.getvalue(), width, height
            except Exception:
                continue

        return None

    @classmethod
    def _build_fee_receipt_pdf(
        cls,
        *,
        context: dict,
        generated_at: datetime,
        download_url: str,
        file_name: str,
    ) -> bytes:
        def as_str(value: object, fallback: str = "-") -> str:
            text_value = str(value).strip() if value is not None else ""
            return text_value or fallback

        payment_rows = context.get("payment_rows") or []
        latest_invoice = payment_rows[-1][1] if payment_rows else None

        target_installments = max(1, int(context.get("installment_target_count") or 1))
        paid_installments = len(payment_rows)
        remaining_installments = max(target_installments - paid_installments, 0)
        remaining_amount = float(context.get("pending_amount") or 0)

        installment_projection: list[float] = []
        if remaining_installments > 0 and remaining_amount > 0:
            even_amount = round(remaining_amount / remaining_installments, 2)
            running = remaining_amount
            for index in range(remaining_installments):
                if index == remaining_installments - 1:
                    amount = round(max(running, 0), 2)
                else:
                    amount = even_amount
                    running = round(running - even_amount, 2)
                installment_projection.append(amount)

        commands: list[str] = []

        def rect(
            x: float,
            y: float,
            w: float,
            h: float,
            *,
            fill: tuple[float, float, float] | None = None,
            stroke: tuple[float, float, float] | None = None,
            line_width: float = 1.0,
        ) -> None:
            if fill is not None:
                commands.append(f"{fill[0]:.3f} {fill[1]:.3f} {fill[2]:.3f} rg")
                commands.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re f")
            if stroke is not None:
                commands.append(f"{stroke[0]:.3f} {stroke[1]:.3f} {stroke[2]:.3f} RG")
                commands.append(f"{line_width:.2f} w")
                commands.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re S")

        def line(x1: float, y1: float, x2: float, y2: float, *, color: tuple[float, float, float], width: float = 1.0) -> None:
            commands.append(f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} RG")
            commands.append(f"{width:.2f} w")
            commands.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

        def text_at(
            x: float,
            y: float,
            value: str,
            *,
            font: str = "F1",
            size: int = 10,
            color: tuple[float, float, float] = (0.12, 0.12, 0.18),
        ) -> None:
            safe = cls._escape_pdf_text(as_str(value, ""))
            commands.append(f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} rg")
            commands.append("BT")
            commands.append(f"/{font} {size} Tf")
            commands.append(f"1 0 0 1 {x:.2f} {y:.2f} Tm")
            commands.append(f"({safe}) Tj")
            commands.append("ET")

        rect(24, 760, 547, 64, fill=(0.96, 0.94, 1.00), stroke=(0.80, 0.72, 0.96))

        logo = cls._load_fee_receipt_logo_jpeg()
        if logo:
            _, logo_w, logo_h = logo
            box_w = 58.0
            box_h = 58.0
            scale = min(box_w / float(logo_w), box_h / float(logo_h))
            draw_w = float(logo_w) * scale
            draw_h = float(logo_h) * scale
            draw_x = 30.0 + (box_w - draw_w) / 2
            draw_y = 763.0 + (box_h - draw_h) / 2
            commands.append("q")
            commands.append(f"{draw_w:.2f} 0 0 {draw_h:.2f} {draw_x:.2f} {draw_y:.2f} cm")
            commands.append("/Im1 Do")
            commands.append("Q")

        settings = get_settings()
        text_at(96, 804, as_str(settings.institute_display_name, "Adrika Coaching Classes"), font="F2", size=16, color=(0.20, 0.14, 0.42))
        text_at(96, 786, "FEE RECEIPT", font="F2", size=18, color=(0.16, 0.12, 0.34))
        text_at(410, 803, f"Receipt No: {as_str(latest_invoice.invoice_no if latest_invoice else file_name)}", size=9, color=(0.33, 0.28, 0.52))
        text_at(410, 787, f"Generated: {generated_at.astimezone(app_timezone()).strftime('%d-%b-%Y %I:%M %p IST')}", size=9, color=(0.33, 0.28, 0.52))

        rect(24, 636, 547, 110, fill=(1.0, 1.0, 1.0), stroke=(0.86, 0.82, 0.94))
        text_at(34, 730, "Student Details", font="F2", size=11, color=(0.22, 0.18, 0.43))
        text_at(34, 710, f"Student Name: {as_str(context.get('student_name'))}")
        text_at(34, 692, f"Class: {as_str(context.get('class_name'))}")
        text_at(34, 674, f"Stream: {as_str(context.get('stream'))}")
        text_at(286, 710, f"Student Contact: {as_str(context.get('student_phone'))}")
        text_at(286, 692, f"Parent Contact: {as_str(context.get('parent_contact_number'))}")
        text_at(286, 674, f"Fee Structure: {as_str(context.get('fee_structure_name'))}")

        rect(24, 538, 547, 86, fill=(1.0, 1.0, 1.0), stroke=(0.86, 0.82, 0.94))
        rect(24, 601, 547, 23, fill=(0.95, 0.94, 0.99), stroke=(0.86, 0.82, 0.94))
        text_at(36, 609, "Original Fee", font="F2", size=10, color=(0.27, 0.21, 0.48))
        text_at(170, 609, "Paid", font="F2", size=10, color=(0.27, 0.21, 0.48))
        text_at(292, 609, "Pending", font="F2", size=10, color=(0.27, 0.21, 0.48))
        text_at(418, 609, "Installments", font="F2", size=10, color=(0.27, 0.21, 0.48))

        text_at(36, 572, cls._format_inr(float(context.get('fee_amount') or 0)), font="F2", size=11)
        text_at(170, 572, cls._format_inr(float(context.get('paid_amount') or 0)), font="F2", size=11)
        text_at(292, 572, cls._format_inr(float(context.get('pending_amount') or 0)), font="F2", size=11)
        text_at(418, 572, f"{paid_installments}/{target_installments}", font="F2", size=11)

        table_top = 504
        row_height = 24
        max_rows = 8
        table_height = 30 + (max_rows * row_height)
        rect(24, table_top - table_height, 547, table_height, fill=(1.0, 1.0, 1.0), stroke=(0.86, 0.82, 0.94))
        rect(24, table_top - 30, 547, 30, fill=(0.95, 0.94, 0.99), stroke=(0.86, 0.82, 0.94))
        text_at(34, table_top - 20, "Inst.", font="F2", size=9, color=(0.27, 0.21, 0.48))
        text_at(78, table_top - 20, "Invoice No", font="F2", size=9, color=(0.27, 0.21, 0.48))
        text_at(198, table_top - 20, "Paid Date (IST)", font="F2", size=9, color=(0.27, 0.21, 0.48))
        text_at(320, table_top - 20, "Mode", font="F2", size=9, color=(0.27, 0.21, 0.48))
        text_at(392, table_top - 20, "Reference", font="F2", size=9, color=(0.27, 0.21, 0.48))
        text_at(500, table_top - 20, "Amount", font="F2", size=9, color=(0.27, 0.21, 0.48))

        y_cursor = table_top - 50
        if payment_rows:
            for index, (tx, invoice) in enumerate(payment_rows[-max_rows:], start=1):
                if index % 2 == 0:
                    rect(24, y_cursor - 4, 547, row_height, fill=(0.99, 0.98, 1.00))
                paid_at = tx.paid_at.astimezone(app_timezone()).strftime('%d-%b-%Y %I:%M %p') if tx.paid_at else tx.created_at.astimezone(app_timezone()).strftime('%d-%b-%Y %I:%M %p')
                text_at(34, y_cursor, str(invoice.installment_no if invoice.installment_no is not None else '-'), size=9)
                text_at(78, y_cursor, as_str(invoice.invoice_no)[:20], size=9)
                text_at(198, y_cursor, paid_at, size=9)
                text_at(320, y_cursor, as_str((tx.payment_mode or 'manual').replace('_', ' ').title()), size=9)
                text_at(392, y_cursor, as_str(tx.external_ref)[:18], size=9)
                text_at(500, y_cursor, cls._format_inr(float(tx.amount or 0)), size=9)
                y_cursor -= row_height
        else:
            text_at(34, y_cursor, "No paid installment yet.", size=9, color=(0.40, 0.36, 0.52))

        rect(24, 64, 547, 110, fill=(1.0, 1.0, 1.0), stroke=(0.86, 0.82, 0.94))
        rect(24, 146, 547, 28, fill=(0.95, 0.94, 0.99), stroke=(0.86, 0.82, 0.94))
        text_at(34, 156, "Next Installments", font="F2", size=10, color=(0.27, 0.21, 0.48))

        next_y = 126
        if installment_projection:
            for idx, amount in enumerate(installment_projection[:3], start=1):
                text_at(40, next_y, f"Installment {idx}", size=10)
                text_at(180, next_y, cls._format_inr(amount), font="F2", size=10)
                next_y -= 20
        else:
            text_at(40, next_y, "No upcoming installment. Fee fully paid.", size=10, color=(0.16, 0.45, 0.23))

        line(390, 96, 550, 96, color=(0.45, 0.40, 0.58), width=1.0)
        text_at(430, 82, "Authorized Signature", size=9, color=(0.40, 0.36, 0.52))
        text_at(34, 42, f"Receipt URL: {download_url}", size=8, color=(0.38, 0.34, 0.50))

        stream = "\n".join(commands).encode("latin-1", errors="replace")

        logo_entry = ""
        objects: list[bytes] = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        ]

        if logo:
            logo_entry = " /XObject << /Im1 6 0 R >>"

        page_obj = (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 4 0 R /F2 5 0 R >>{logo_entry} >> "
            f"/Contents {'7 0 R' if logo else '6 0 R'} >>"
        ).encode("ascii")
        objects.append(page_obj)
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

        if logo:
            logo_bytes, logo_w, logo_h = logo
            image_obj = (
                f"<< /Type /XObject /Subtype /Image /Width {logo_w} /Height {logo_h} "
                f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(logo_bytes)} >>\nstream\n"
            ).encode("ascii") + logo_bytes + b"\nendstream"
            objects.append(image_obj)

        content_obj = f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream"
        objects.append(content_obj)

        payload = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets: list[int] = []
        for idx, obj in enumerate(objects, start=1):
            offsets.append(len(payload))
            payload.extend(f"{idx} 0 obj\n".encode("ascii"))
            payload.extend(obj)
            payload.extend(b"\nendobj\n")

        xref_start = len(payload)
        payload.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        payload.extend(b"0000000000 65535 f \n")
        for off in offsets:
            payload.extend(f"{off:010d} 00000 n \n".encode("ascii"))

        payload.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii"))
        payload.extend(f"startxref\n{xref_start}\n%%EOF\n".encode("ascii"))
        return bytes(payload)

    def _persist_fee_receipt_pdf(self, *, context: dict) -> dict:
        payment_rows = context["payment_rows"]
        latest_tx = payment_rows[-1][0] if payment_rows else None
        latest_invoice = payment_rows[-1][1] if payment_rows else None

        generated_at = datetime.now(UTC)
        media_dir, media_url = self._media_config()
        receipt_dir = media_dir / "receipts"
        receipt_dir.mkdir(parents=True, exist_ok=True)

        file_name = f"FEE-RECEIPT-{context['student_id'][:6].upper()}-{generated_at.strftime('%Y%m%d%H%M%S')}.pdf"
        file_path = receipt_dir / file_name
        download_url = f"{media_url}/receipts/{file_name}"

        file_path.write_bytes(
            self._build_fee_receipt_pdf(
                context=context,
                generated_at=generated_at,
                download_url=download_url,
                file_name=file_name,
            )
        )

        receipt = {
            "file_name": file_name,
            "download_url": download_url,
            "generated_at": generated_at.isoformat(),
            "invoice_no": latest_invoice.invoice_no if latest_invoice else None,
            "payment_id": latest_tx.id if latest_tx else None,
        }

        if latest_tx is not None:
            metadata = dict(latest_tx.metadata_json or {})
            metadata["receipt"] = receipt
            latest_tx.metadata_json = metadata
            latest_tx.receipt_generated = True
        return receipt

    async def _ensure_latest_fee_receipt(self, *, student_id: str, regenerate: bool = False) -> tuple[dict, bool, dict]:
        context = await self._load_fee_receipt_context(student_id=student_id)

        existing = self._extract_existing_receipt(context=context)
        if existing and not regenerate:
            return existing, False, context

        receipt = self._persist_fee_receipt_pdf(context=context)
        return receipt, True, context

    async def _send_whatsapp_text_message(self, *, to_phone: str, message: str) -> dict:
        normalized_phone = self._normalize_whatsapp_phone(to_phone)
        if not normalized_phone:
            raise ForbiddenException("Valid parent WhatsApp number is required")

        settings = get_settings()
        base_url = settings.whatsapp_base_url.strip()
        access_token = settings.whatsapp_access_token.strip()
        phone_number_id = settings.whatsapp_phone_number_id.strip()

        if not base_url or not access_token or not phone_number_id:
            return {
                "status": "mock_sent",
                "provider": "mock",
                "to_phone": normalized_phone,
                "provider_message_id": f"wa_mock_{uuid4().hex[:12]}",
                "provider_response": "WhatsApp API not configured in environment",
            }

        endpoint = f"{base_url.rstrip('/')}/{phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": normalized_phone,
            "type": "text",
            "text": {"preview_url": True, "body": message},
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(endpoint, json=payload, headers=headers)

            body_text = response.text
            provider_message_id = None
            try:
                parsed = response.json()
                provider_message_id = (parsed.get("messages") or [{}])[0].get("id")
            except Exception:
                provider_message_id = None

            return {
                "status": "sent" if response.is_success else "failed",
                "provider": "whatsapp_business",
                "to_phone": normalized_phone,
                "provider_message_id": provider_message_id,
                "provider_response": body_text,
            }
        except Exception as exc:  # pragma: no cover - network/runtime safety
            return {
                "status": "failed",
                "provider": "whatsapp_business",
                "to_phone": normalized_phone,
                "provider_message_id": None,
                "provider_response": str(exc),
            }

    def _build_fee_receipt_whatsapp_message(self, *, context: dict, receipt: dict, custom_message: str | None) -> str:
        if custom_message and custom_message.strip():
            return custom_message.strip()

        settings = get_settings()
        lines = [
            f"{settings.institute_display_name}",
            f"Fee receipt for {context['student_name']}",
            f"Class: {context['class_name']} ({context['stream']})",
            f"Total Fee: {self._format_inr(context['fee_amount'])}",
            f"Paid: {self._format_inr(context['paid_amount'])}",
            f"Pending: {self._format_inr(context['pending_amount'])}",
            f"Receipt: {receipt['download_url']}",
        ]
        if settings.fee_payment_contact_number:
            lines.append(f"Support: {settings.fee_payment_contact_number}")
        if settings.fee_payment_upi_id:
            lines.append(f"UPI: {settings.fee_payment_upi_id}")
        return "\n".join(lines)

    async def get_student_fee_assignment(self, *, student_id: str) -> dict:
        student_stmt = (
            select(StudentProfile, User, Batch, Standard)
            .join(User, User.id == StudentProfile.user_id)
            .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
            .outerjoin(Standard, Standard.id == Batch.standard_id)
            .where(StudentProfile.id == student_id)
        )
        student_row = (await self.session.execute(student_stmt)).first()
        if not student_row:
            raise NotFoundException("Student not found")

        profile, user, _, standard = student_row
        class_name = profile.class_name or (standard.name if standard else None)
        grade = self._extract_grade(profile.class_name, standard.name if standard else None)
        class_level = int(grade) if grade is not None else None
        normalized_student_stream = self._normalize_fee_stream(profile.stream)

        assignment_stmt = (
            select(StudentFeeStructureAssignment, FeeStructure)
            .join(FeeStructure, FeeStructure.id == StudentFeeStructureAssignment.fee_structure_id)
            .where(
                StudentFeeStructureAssignment.student_id == profile.id,
                StudentFeeStructureAssignment.is_active.is_(True),
            )
        )
        assignment_row = (await self.session.execute(assignment_stmt)).first()

        structures_query = select(FeeStructure).where(FeeStructure.is_active.is_(True))
        if class_level is not None:
            structures_query = structures_query.where(FeeStructure.class_level == class_level)
            if class_level == 10:
                structures_query = structures_query.where(FeeStructure.stream.is_(None))
            elif class_level in {11, 12} and normalized_student_stream in {"science", "commerce"}:
                structures_query = structures_query.where(FeeStructure.stream == normalized_student_stream)

        available_structures = (
            await self.session.execute(
                structures_query.order_by(FeeStructure.total_amount.asc(), FeeStructure.name.asc())
            )
        ).scalars().all()

        rollup_row = (
            await self.session.execute(
                select(
                    func.coalesce(
                        func.sum(case((PaymentTransaction.status == "success", PaymentTransaction.amount), else_=0)),
                        0,
                    ).label("paid_amount"),
                    func.coalesce(
                        func.sum(case((PaymentTransaction.status == "success", 1), else_=0)),
                        0,
                    ).label("installments_paid_count"),
                    func.max(case((PaymentTransaction.status == "success", PaymentTransaction.paid_at), else_=None)).label(
                        "last_paid_at"
                    ),
                ).where(PaymentTransaction.student_id == profile.id)
            )
        ).mappings().one()

        raw_paid_amount = float(rollup_row["paid_amount"] or 0)
        installments_paid_count = int(rollup_row["installments_paid_count"] or 0)
        last_paid_at = rollup_row["last_paid_at"]

        payments_rows = (
            await self.session.execute(
                select(PaymentTransaction, FeeInvoice)
                .join(FeeInvoice, FeeInvoice.id == PaymentTransaction.invoice_id)
                .where(
                    PaymentTransaction.student_id == profile.id,
                    PaymentTransaction.status == "success",
                )
                .order_by(PaymentTransaction.paid_at.desc(), PaymentTransaction.created_at.desc())
            )
        ).all()

        installment_rows = []
        if assignment_row is not None:
            assignment_obj, _ = assignment_row
            installment_rows = (
                await self.session.execute(
                    select(FeeInvoice)
                    .where(
                        FeeInvoice.student_id == profile.id,
                        FeeInvoice.student_fee_account_id == assignment_obj.id,
                        FeeInvoice.installment_no.is_not(None),
                    )
                    .order_by(FeeInvoice.installment_no.asc(), FeeInvoice.due_date.asc())
                )
            ).scalars().all()

        def installment_outstanding(invoice: FeeInvoice) -> float:
            base = invoice.balance_amount if invoice.balance_amount is not None else invoice.amount
            return max(float(base or 0), 0.0)

        today_local = datetime.now(app_timezone()).date()
        installments_paid_count = 0
        next_due_date = None
        missed_payment_count = 0
        for inv in installment_rows:
            outstanding = installment_outstanding(inv)
            if outstanding <= 0.0001 or inv.status == "paid":
                installments_paid_count += 1
                continue
            if inv.due_date and (next_due_date is None or inv.due_date < next_due_date):
                next_due_date = inv.due_date
            if inv.due_date and inv.due_date < today_local:
                missed_payment_count += 1

        current_assignment = None
        fee_amount = None
        installment_target_count = None
        if assignment_row is not None:
            assignment, structure = assignment_row
            fee_amount = float(structure.total_amount)
            installment_target_count = int(structure.installment_count)
            current_assignment = {
                "assignment_id": assignment.id,
                "fee_structure_id": structure.id,
                "fee_structure_name": structure.name,
                "fee_amount": fee_amount,
                "installment_count": structure.installment_count,
                "assigned_at": assignment.created_at,
                "updated_at": assignment.updated_at,
            }

        paid_amount, pending_amount, is_fully_paid = self._compute_fee_progress(
            fee_amount=fee_amount,
            paid_amount=raw_paid_amount,
        )

        if fee_amount is not None and installment_rows:
            schedule_pending = round(sum(installment_outstanding(inv) for inv in installment_rows), 2)
            schedule_pending = max(min(schedule_pending, float(fee_amount)), 0.0)
            pending_amount = schedule_pending
            paid_amount = round(max(float(fee_amount) - schedule_pending, 0.0), 2)
            is_fully_paid = pending_amount <= 0.0001

        payments = []
        for tx, invoice in payments_rows:
            payments.append(
                {
                    "payment_id": tx.id,
                    "invoice_id": invoice.id,
                    "invoice_no": invoice.invoice_no,
                    "installment_no": invoice.installment_no,
                    "period_label": invoice.period_label,
                    "amount": float(tx.amount),
                    "payment_mode": tx.payment_mode,
                    "reference_no": tx.external_ref,
                    "note": tx.note,
                    "paid_at": tx.paid_at,
                    "created_at": tx.created_at,
                }
            )

        installments = []
        for inv in installment_rows:
            outstanding = float(inv.balance_amount if inv.balance_amount is not None else (inv.amount or 0))
            due_date = inv.due_date
            if outstanding <= 0.0001:
                computed_status = "paid"
            elif due_date and due_date < today_local:
                computed_status = "overdue"
            else:
                computed_status = "pending"
            is_missed = computed_status == "overdue"
            days_overdue = (today_local - due_date).days if (due_date and due_date < today_local) else 0
            installments.append(
                {
                    "invoice_id": inv.id,
                    "invoice_no": inv.invoice_no,
                    "installment_no": inv.installment_no,
                    "period_label": inv.period_label,
                    "due_date": due_date.isoformat() if due_date else None,
                    "amount": float(inv.amount or 0),
                    "balance_amount": round(max(outstanding, 0.0), 2),
                    "status": computed_status,
                    "paid_at": inv.paid_at,
                    "is_missed": is_missed,
                    "days_overdue": max(int(days_overdue), 0),
                    "reminder_enabled": bool(inv.reminder_enabled),
                    "last_reminder_sent_at": inv.last_reminder_sent_at,
                }
            )

        return {
            "student": {
                "student_id": profile.id,
                "user_id": user.id,
                "full_name": user.full_name,
                "class_name": class_name,
                "class_level": class_level,
                "stream": self._stream_for_display(class_level, profile.stream),
                "phone": user.phone,
                "parent_contact_number": profile.parent_contact_number,
            },
            "current_assignment": current_assignment,
            "billing": {
                "fee_amount": fee_amount,
                "paid_amount": paid_amount,
                "pending_amount": pending_amount,
                "installments_paid_count": installments_paid_count,
                "installment_target_count": installment_target_count,
                "last_paid_at": last_paid_at,
                "next_due_date": next_due_date.isoformat() if next_due_date else None,
                "missed_payment_count": missed_payment_count,
                "is_overdue": missed_payment_count > 0,
                "is_fully_paid": is_fully_paid,
            },
            "payments": payments,
            "installments": installments,
            "available_structures": [
                {
                    "id": structure.id,
                    "name": structure.name,
                    "class_level": structure.class_level,
                    "stream": structure.stream,
                    "total_amount": float(structure.total_amount),
                    "installment_count": structure.installment_count,
                }
                for structure in available_structures
            ],
        }

    async def assign_student_fee_structure(
        self,
        *,
        student_id: str,
        payload: AdminStudentFeeStructureAssignDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        student_stmt = (
            select(StudentProfile, User, Batch, Standard)
            .join(User, User.id == StudentProfile.user_id)
            .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
            .outerjoin(Standard, Standard.id == Batch.standard_id)
            .where(StudentProfile.id == student_id)
        )
        student_row = (await self.session.execute(student_stmt)).first()
        if not student_row:
            raise NotFoundException("Student not found")

        profile, user, _, standard = student_row
        grade = self._extract_grade(profile.class_name, standard.name if standard else None)
        class_level = int(grade) if grade is not None else None
        normalized_student_stream = self._normalize_fee_stream(profile.stream)

        structure = await self.session.get(FeeStructure, payload.fee_structure_id)
        if not structure:
            raise NotFoundException("Fee structure not found")
        if not structure.is_active:
            raise ForbiddenException("Selected fee structure is inactive")

        if class_level is not None and structure.class_level != class_level:
            raise ForbiddenException("Selected fee structure class does not match student class")
        if structure.class_level in {11, 12}:
            if normalized_student_stream not in {"science", "commerce"}:
                raise ForbiddenException("Student stream is required for class 11 and 12 assignment")
            if structure.stream != normalized_student_stream:
                raise ForbiddenException("Selected fee structure stream does not match student stream")
        if structure.class_level == 10 and structure.stream is not None:
            raise ForbiddenException("Class 10 assignment cannot use stream-based fee structure")

        paid_amount_raw = (
            await self.session.execute(
                select(
                    func.coalesce(
                        func.sum(case((PaymentTransaction.status == "success", PaymentTransaction.amount), else_=0)),
                        0,
                    )
                ).where(PaymentTransaction.student_id == student_id)
            )
        ).scalar_one()
        paid_amount = float(paid_amount_raw or 0)
        structure_total = float(structure.total_amount)
        if paid_amount > structure_total + 0.0001:
            raise ForbiddenException(
                "Selected structure amount is lower than already paid amount. Choose a higher structure."
            )

        existing = (
            await self.session.execute(
                select(StudentFeeStructureAssignment).where(StudentFeeStructureAssignment.student_id == student_id)
            )
        ).scalar_one_or_none()

        before = None
        if existing:
            existing_structure = await self.session.get(FeeStructure, existing.fee_structure_id)
            before = {
                "fee_structure_id": existing.fee_structure_id,
                "fee_structure_name": existing_structure.name if existing_structure else None,
                "is_active": existing.is_active,
            }
            existing.fee_structure_id = structure.id
            existing.assigned_by_user_id = actor_user_id
            existing.is_active = True
            assignment = existing
            action = "admin.student_fee_structure.update"
        else:
            assignment = StudentFeeStructureAssignment(
                student_id=student_id,
                fee_structure_id=structure.id,
                assigned_by_user_id=actor_user_id,
                is_active=True,
            )
            self.session.add(assignment)
            await self.session.flush()
            action = "admin.student_fee_structure.create"

        await self._audit(
            actor_user_id=actor_user_id,
            action=action,
            entity_type="student_fee_structure_assignment",
            entity_id=assignment.id,
            before_state=before,
            after_state={
                "student_id": student_id,
                "student_name": user.full_name,
                "fee_structure_id": structure.id,
                "fee_structure_name": structure.name,
                "fee_amount": float(structure.total_amount),
                "installment_count": structure.installment_count,
                "is_active": assignment.is_active,
            },
            ip_address=ip_address,
        )

        await self.session.commit()
        await self.session.refresh(assignment)

        paid_amount_capped, pending_amount, is_fully_paid = self._compute_fee_progress(
            fee_amount=structure_total,
            paid_amount=paid_amount,
        )

        return {
            "assignment_id": assignment.id,
            "student_id": student_id,
            "fee_structure_id": structure.id,
            "fee_structure_name": structure.name,
            "fee_amount": structure_total,
            "installment_count": structure.installment_count,
            "assigned": True,
            "paid_amount": paid_amount_capped,
            "pending_amount": pending_amount,
            "is_fully_paid": is_fully_paid,
            "updated_at": assignment.updated_at,
        }

    async def _ensure_student_installment_schedule(
        self,
        *,
        student_id: str,
        assignment_id: str,
        total_fee: float,
        installment_count: int,
        anchor_date: date,
        first_paid_amount: float,
    ) -> list[FeeInvoice]:
        safe_count = max(1, int(installment_count or 1))
        rows = (
            await self.session.execute(
                select(FeeInvoice)
                .where(
                    FeeInvoice.student_id == student_id,
                    FeeInvoice.student_fee_account_id == assignment_id,
                    FeeInvoice.installment_no.is_not(None),
                )
                .order_by(FeeInvoice.installment_no.asc(), FeeInvoice.created_at.asc())
            )
        ).scalars().all()

        invoice_by_no: dict[int, FeeInvoice] = {}
        for row in rows:
            if row.installment_no is None:
                continue
            invoice_by_no[int(row.installment_no)] = row

        if not rows:
            target_amounts = self._build_installment_schedule_amounts(
                total_amount=total_fee,
                installment_count=safe_count,
                first_paid_amount=first_paid_amount,
            )
            for index in range(1, safe_count + 1):
                due = self._date_with_month_delta(anchor_date, index - 1)
                amount = float(target_amounts[index - 1]) if index - 1 < len(target_amounts) else 0.0
                invoice = FeeInvoice(
                    student_id=student_id,
                    student_fee_account_id=assignment_id,
                    installment_no=index,
                    invoice_no=self._build_fee_invoice_no(student_id),
                    period_label=f"Installment {index}",
                    due_date=due,
                    amount=amount,
                    balance_amount=amount,
                    status="pending",
                    reminder_enabled=True,
                    next_installment_date=due,
                )
                self.session.add(invoice)

            await self.session.flush()
            rows = (
                await self.session.execute(
                    select(FeeInvoice)
                    .where(
                        FeeInvoice.student_id == student_id,
                        FeeInvoice.student_fee_account_id == assignment_id,
                        FeeInvoice.installment_no.is_not(None),
                    )
                    .order_by(FeeInvoice.installment_no.asc(), FeeInvoice.created_at.asc())
                )
            ).scalars().all()
            return rows

        first_invoice = invoice_by_no.get(1)
        first_amount = float(first_invoice.amount or 0) if first_invoice else 0.0
        target_amounts = self._build_installment_schedule_amounts(
            total_amount=total_fee,
            installment_count=safe_count,
            first_paid_amount=first_amount,
        )
        base_date = first_invoice.due_date if first_invoice and first_invoice.due_date else anchor_date

        for index in range(1, safe_count + 1):
            target_due = self._date_with_month_delta(base_date, index - 1)
            target_amount = float(target_amounts[index - 1]) if index - 1 < len(target_amounts) else 0.0
            invoice = invoice_by_no.get(index)
            if invoice is None:
                self.session.add(
                    FeeInvoice(
                        student_id=student_id,
                        student_fee_account_id=assignment_id,
                        installment_no=index,
                        invoice_no=self._build_fee_invoice_no(student_id),
                        period_label=f"Installment {index}",
                        due_date=target_due,
                        amount=target_amount,
                        balance_amount=target_amount,
                        status="pending",
                        reminder_enabled=True,
                        next_installment_date=target_due,
                    )
                )
                continue

            if invoice.due_date is None:
                invoice.due_date = target_due
            if (invoice.amount is None or float(invoice.amount or 0) <= 0) and target_amount > 0:
                invoice.amount = target_amount
                if invoice.balance_amount is None:
                    invoice.balance_amount = target_amount
            if invoice.status != "paid":
                invoice.next_installment_date = invoice.due_date
                invoice.reminder_enabled = True

        await self.session.flush()
        rows = (
            await self.session.execute(
                select(FeeInvoice)
                .where(
                    FeeInvoice.student_id == student_id,
                    FeeInvoice.student_fee_account_id == assignment_id,
                    FeeInvoice.installment_no.is_not(None),
                )
                .order_by(FeeInvoice.installment_no.asc(), FeeInvoice.created_at.asc())
            )
        ).scalars().all()
        return rows

    async def record_student_fee_payment(
        self,
        *,
        student_id: str,
        payload: AdminStudentFeePaymentCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        assignment_row = (
            await self.session.execute(
                select(StudentFeeStructureAssignment, FeeStructure, StudentProfile, User)
                .join(FeeStructure, FeeStructure.id == StudentFeeStructureAssignment.fee_structure_id)
                .join(StudentProfile, StudentProfile.id == StudentFeeStructureAssignment.student_id)
                .join(User, User.id == StudentProfile.user_id)
                .where(
                    StudentFeeStructureAssignment.student_id == student_id,
                    StudentFeeStructureAssignment.is_active.is_(True),
                )
            )
        ).first()

        if not assignment_row:
            raise ForbiddenException("Assign fee structure first, then record payment")

        assignment, structure, _profile, user = assignment_row

        rollup_row = (
            await self.session.execute(
                select(
                    func.coalesce(
                        func.sum(case((PaymentTransaction.status == "success", PaymentTransaction.amount), else_=0)),
                        0,
                    ).label("paid_amount"),
                ).where(PaymentTransaction.student_id == student_id)
            )
        ).mappings().one()

        current_paid_amount = float(rollup_row["paid_amount"] or 0)

        fee_amount = float(structure.total_amount)
        _, current_pending_amount, _ = self._compute_fee_progress(
            fee_amount=fee_amount,
            paid_amount=current_paid_amount,
        )

        if current_pending_amount <= 0.0001:
            raise ForbiddenException("Fee is already fully paid for this student")

        payment_amount = float(payload.amount)
        if payment_amount > current_pending_amount + 0.0001:
            raise ForbiddenException("Payment amount cannot exceed pending amount")

        selected_installment_no = int(payload.installment_no) if payload.installment_no is not None else None

        paid_at = datetime(
            year=payload.paid_on.year,
            month=payload.paid_on.month,
            day=payload.paid_on.day,
            tzinfo=UTC,
        )

        schedule_rows = await self._ensure_student_installment_schedule(
            student_id=student_id,
            assignment_id=assignment.id,
            total_fee=fee_amount,
            installment_count=int(structure.installment_count or 1),
            anchor_date=payload.paid_on,
            first_paid_amount=current_paid_amount if current_paid_amount > 0 else payment_amount,
        )

        def outstanding_value(invoice: FeeInvoice) -> float:
            base = invoice.balance_amount if invoice.balance_amount is not None else invoice.amount
            return max(float(base or 0), 0.0)

        # Reconcile legacy installment balances with ledger-derived pending amount.
        # Do NOT re-apply full paid amount each time; only correct mismatch.
        schedule_outstanding_total = round(
            sum(outstanding_value(row) for row in schedule_rows),
            2,
        )
        reconcile_reduce = round(max(schedule_outstanding_total - current_pending_amount, 0.0), 2)
        if reconcile_reduce > 0.0001:
            for row in schedule_rows:
                if reconcile_reduce <= 0.0001:
                    break

                due = outstanding_value(row)
                if due <= 0.0001:
                    row.status = "paid"
                    row.balance_amount = 0
                    row.reminder_enabled = False
                    row.next_installment_date = None
                    continue

                consume = min(reconcile_reduce, due)
                reconcile_reduce = round(reconcile_reduce - consume, 2)
                due_after = round(due - consume, 2)
                if due_after <= 0.0001:
                    row.status = "paid"
                    row.balance_amount = 0
                    row.reminder_enabled = False
                    row.next_installment_date = None
                else:
                    row.status = "partial"
                    row.balance_amount = due_after
                    row.reminder_enabled = True
                    row.next_installment_date = row.due_date

        remaining = payment_amount
        primary_invoice: FeeInvoice | None = None
        allocated_items: list[dict] = []

        today_local = datetime.now(app_timezone()).date()

        # Self-heal: if pending exists but all installment balances are zero/paid due to
        # legacy inconsistencies, rebuild outstanding balances so manual payments never block.
        current_outstanding_total = sum(
            outstanding_value(row) for row in schedule_rows if row.status != "paid"
        )
        if current_pending_amount > 0.0001 and current_outstanding_total <= 0.0001:
            editable_rows = [row for row in schedule_rows if row.status != "paid"] or list(schedule_rows)
            if editable_rows:
                distribution = self._split_installment_amounts(
                    total_amount=current_pending_amount,
                    installment_count=len(editable_rows),
                )
                for idx, row in enumerate(editable_rows):
                    due_amount = float(distribution[idx]) if idx < len(distribution) else 0.0
                    row.balance_amount = due_amount
                    if row.amount is None or float(row.amount or 0) < due_amount:
                        row.amount = due_amount
                    if row.due_date is None:
                        row.due_date = self._date_with_month_delta(payload.paid_on, idx)
                    row.status = "pending" if due_amount > 0.0001 else "paid"
                    row.reminder_enabled = due_amount > 0.0001
                    row.next_installment_date = row.due_date if due_amount > 0.0001 else None

        # Normalize status from actual outstanding so stale statuses do not block payment.
        for row in schedule_rows:
            due_now = outstanding_value(row)
            if due_now <= 0.0001:
                row.status = "paid"
                row.balance_amount = 0
                row.reminder_enabled = False
                row.next_installment_date = None
            else:
                if row.due_date and row.due_date < today_local:
                    row.status = "overdue"
                else:
                    row.status = "pending"
                row.reminder_enabled = True
                row.next_installment_date = row.due_date

        def _next_future_installment(current: FeeInvoice) -> FeeInvoice | None:
            current_no = int(current.installment_no or 0)
            if current_no > 0:
                for candidate in schedule_rows:
                    candidate_no = int(candidate.installment_no or 0)
                    if candidate_no > current_no:
                        return candidate
            for candidate in schedule_rows:
                if candidate.id != current.id:
                    return candidate
            return None

        allocation_rows = list(schedule_rows)
        if selected_installment_no is not None:
            preferred = next(
                (row for row in schedule_rows if int(row.installment_no or 0) == selected_installment_no),
                None,
            )
            if preferred is None:
                raise ForbiddenException("Selected installment not found for this student")
            preferred_due = outstanding_value(preferred)
            if preferred_due <= 0.0001:
                fallback = next((row for row in schedule_rows if outstanding_value(row) > 0.0001), None)
                if fallback is None:
                    raise ForbiddenException("Selected installment is already paid. Choose another installment.")
                preferred = fallback
                selected_installment_no = int(preferred.installment_no or 0) or None
            allocation_rows = [preferred, *[row for row in schedule_rows if row.id != preferred.id]]

        for row in allocation_rows:
            if remaining <= 0.0001:
                break

            due = outstanding_value(row)
            if due <= 0.0001:
                row.status = "paid"
                row.balance_amount = 0
                row.reminder_enabled = False
                row.next_installment_date = None
                continue

            apply_amount = min(remaining, due)
            if apply_amount <= 0:
                continue

            if primary_invoice is None:
                primary_invoice = row

            remaining = round(remaining - apply_amount, 2)
            due_after = round(due - apply_amount, 2)

            if due_after <= 0.0001:
                row.status = "paid"
                row.balance_amount = 0
                row.paid_at = paid_at
                row.reminder_enabled = False
                row.next_installment_date = None
            else:
                # Carry-forward policy: remaining unpaid part of current installment
                # is moved to upcoming installment when available.
                future_row = _next_future_installment(row)
                if future_row is not None and future_row.id != row.id:
                    future_due_before = outstanding_value(future_row)
                    future_row.balance_amount = round(future_due_before + due_after, 2)
                    future_amount_before = float(future_row.amount or 0)
                    future_row.amount = round(future_amount_before + due_after, 2)
                    if future_row.due_date is None:
                        base_due = row.due_date or payload.paid_on
                        future_row.due_date = self._date_with_month_delta(base_due, 1)
                    if future_row.due_date and future_row.due_date < today_local:
                        future_row.status = "overdue"
                    else:
                        future_row.status = "pending"
                    future_row.reminder_enabled = True
                    future_row.next_installment_date = future_row.due_date

                    reduced_amount = round(float(row.amount or 0) - due_after, 2)
                    row.amount = max(reduced_amount, round(apply_amount, 2))
                    row.status = "paid"
                    row.balance_amount = 0
                    row.paid_at = paid_at
                    row.reminder_enabled = False
                    row.next_installment_date = None
                else:
                    row.status = "partial"
                    row.balance_amount = due_after
                    row.paid_at = paid_at
                    row.reminder_enabled = True
                    row.next_installment_date = row.due_date
                    if row.due_date and row.due_date < today_local:
                        row.status = "overdue"

            allocated_items.append(
                {
                    "invoice_id": row.id,
                    "invoice_no": row.invoice_no,
                    "installment_no": row.installment_no,
                    "allocated_amount": round(apply_amount, 2),
                    "remaining_balance": max(due_after, 0.0),
                }
            )

        if remaining > 0.0001 or primary_invoice is None:
            raise ForbiddenException("Unable to allocate payment into installments. Please verify fee structure setup.")

        # Recompute upcoming due dates from current payment date for all unpaid installments.
        unpaid_rows = [
            row
            for row in sorted(
                schedule_rows,
                key=lambda item: (int(item.installment_no or 999), item.created_at),
            )
            if outstanding_value(row) > 0.0001
        ]
        for idx, row in enumerate(unpaid_rows, start=1):
            row.due_date = self._date_with_month_delta(payload.paid_on, idx)
            row.next_installment_date = row.due_date
            if row.due_date and row.due_date < today_local:
                row.status = "overdue"
            else:
                row.status = "pending"
            row.reminder_enabled = True

        normalized_reference = (payload.reference_no or "").strip() or primary_invoice.invoice_no
        unique_reference = await self._build_unique_payment_external_ref(
            provider="admin_manual",
            external_ref=normalized_reference,
        )

        transaction = PaymentTransaction(
            invoice_id=primary_invoice.id,
            student_id=student_id,
            student_fee_account_id=assignment.id,
            provider="admin_manual",
            payment_mode=payload.payment_mode,
            external_ref=unique_reference,
            amount=payment_amount,
            status="success",
            paid_at=paid_at,
            note=payload.note,
            receipt_generated=False,
            metadata_json={
                "source": "admin_fee_update",
                "actor_user_id": actor_user_id,
                "period_label": payload.period_label.strip() if payload.period_label else None,
                "selected_installment_no": selected_installment_no,
                "allocations": allocated_items,
            },
        )
        self.session.add(transaction)
        await self.session.flush()

        updated_paid, updated_pending, is_fully_paid = self._compute_fee_progress(
            fee_amount=fee_amount,
            paid_amount=current_paid_amount + payment_amount,
        )

        paid_installments_count = 0
        next_due_date = None
        for row in schedule_rows:
            due = outstanding_value(row)
            if due <= 0.0001 or row.status == "paid":
                paid_installments_count += 1
                row.status = "paid"
                row.balance_amount = 0
                row.reminder_enabled = False
                row.next_installment_date = None
                continue

            if row.due_date and row.due_date < today_local and row.status in {"pending", "partial"}:
                row.status = "overdue"
            if next_due_date is None and row.due_date is not None:
                next_due_date = row.due_date
            row.reminder_enabled = True
            row.next_installment_date = row.due_date

        receipt, _, _ = await self._ensure_latest_fee_receipt(student_id=student_id, regenerate=True)

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.student_fee_payment.record",
            entity_type="payment_transaction",
            entity_id=transaction.id,
            before_state={
                "student_id": student_id,
                "fee_amount": fee_amount,
                "paid_amount": current_paid_amount,
                "pending_amount": current_pending_amount,
            },
            after_state={
                "student_id": student_id,
                "student_name": user.full_name,
                "invoice_id": primary_invoice.id,
                "invoice_no": primary_invoice.invoice_no,
                "installment_no": primary_invoice.installment_no,
                "payment_mode": transaction.payment_mode,
                "reference_no": transaction.external_ref,
                "payment_amount": payment_amount,
                "paid_amount": updated_paid,
                "pending_amount": updated_pending,
                "is_fully_paid": is_fully_paid,
                "next_due_date": next_due_date.isoformat() if next_due_date else None,
                "selected_installment_no": selected_installment_no,
                "allocations": allocated_items,
                "receipt_file": receipt["file_name"] if receipt else None,
            },
            ip_address=ip_address,
        )

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            message = str(getattr(exc, "orig", exc)).lower()
            if "uq_payment_provider_ref" in message or "payment_transactions.provider, payment_transactions.external_ref" in message:
                raise HTTPException(
                    status_code=http_status.HTTP_409_CONFLICT,
                    detail="Payment reference already exists. Please retry with a different reference number.",
                ) from exc
            raise

        await self.session.refresh(transaction)
        await self.session.refresh(primary_invoice)

        return {
            "student_id": student_id,
            "payment": {
                "payment_id": transaction.id,
                "invoice_id": primary_invoice.id,
                "invoice_no": primary_invoice.invoice_no,
                "installment_no": primary_invoice.installment_no,
                "period_label": payload.period_label.strip() if payload.period_label else (primary_invoice.period_label or ""),
                "amount": float(transaction.amount),
                "payment_mode": transaction.payment_mode,
                "reference_no": transaction.external_ref,
                "note": transaction.note,
                "paid_at": transaction.paid_at,
                "created_at": transaction.created_at,
            },
            "billing": {
                "fee_amount": fee_amount,
                "paid_amount": updated_paid,
                "pending_amount": updated_pending,
                "installments_paid_count": paid_installments_count,
                "installment_target_count": int(structure.installment_count),
                "last_paid_at": transaction.paid_at,
                "is_fully_paid": is_fully_paid,
            },
            "receipt": receipt,
        }

    async def fee_summary(self) -> dict:
        payment_rollup = self._student_payment_rollup_subquery()

        rows = (
            await self.session.execute(
                select(
                    StudentProfile.id,
                    StudentFeeStructureAssignment.id,
                    FeeStructure.total_amount,
                    func.coalesce(payment_rollup.c.paid_amount, 0),
                )
                .select_from(StudentProfile)
                .outerjoin(
                    StudentFeeStructureAssignment,
                    and_(
                        StudentFeeStructureAssignment.student_id == StudentProfile.id,
                        StudentFeeStructureAssignment.is_active.is_(True),
                    ),
                )
                .outerjoin(FeeStructure, FeeStructure.id == StudentFeeStructureAssignment.fee_structure_id)
                .outerjoin(payment_rollup, payment_rollup.c.student_id == StudentProfile.id)
            )
        ).all()

        total_students = len(rows)
        paid_students = 0
        pending_students = 0
        assigned_students = 0
        total_fee_amount = 0.0
        total_paid_amount = 0.0
        total_pending_amount = 0.0

        for _student_id, assignment_id, fee_structure_amount, paid_amount_raw in rows:
            fee_amount = float(fee_structure_amount) if fee_structure_amount is not None else None
            paid_amount = float(paid_amount_raw or 0)

            if assignment_id is None or fee_amount is None:
                continue

            assigned_students += 1
            normalized_paid, pending_amount, is_fully_paid = self._compute_fee_progress(
                fee_amount=fee_amount,
                paid_amount=paid_amount,
            )

            total_fee_amount += fee_amount
            total_paid_amount += normalized_paid
            total_pending_amount += pending_amount

            if is_fully_paid:
                paid_students += 1
            else:
                pending_students += 1

        today_local = datetime.now(app_timezone()).date()
        overdue_rows = (
            await self.session.execute(
                select(
                    FeeInvoice.student_id,
                    FeeInvoice.amount,
                    FeeInvoice.balance_amount,
                ).where(
                    FeeInvoice.installment_no.is_not(None),
                    FeeInvoice.status != "paid",
                    FeeInvoice.due_date < today_local,
                )
            )
        ).all()

        overdue_students = set()
        overdue_installments = 0
        overdue_amount = 0.0
        for student_id, amount, balance_amount in overdue_rows:
            outstanding = float(balance_amount if balance_amount is not None else (amount or 0))
            if outstanding <= 0.0001:
                continue
            overdue_students.add(student_id)
            overdue_installments += 1
            overdue_amount += outstanding

        return {
            "total_students": total_students,
            "paid_students": paid_students,
            "pending_students": pending_students,
            "students_without_fee": max(total_students - assigned_students, 0),
            "total_invoiced_amount": total_fee_amount,
            "total_paid_amount": total_paid_amount,
            "total_pending_amount": total_pending_amount,
            "overdue_students": len(overdue_students),
            "overdue_installments": overdue_installments,
            "overdue_amount": round(overdue_amount, 2),
        }

    @staticmethod
    def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
        index = (year * 12 + (month - 1)) + delta
        next_year = index // 12
        next_month = (index % 12) + 1
        return next_year, next_month

    @classmethod
    def _date_with_month_delta(cls, base_date: date, delta_months: int) -> date:
        next_year, next_month = cls._add_months(base_date.year, base_date.month, delta_months)
        max_day = monthrange(next_year, next_month)[1]
        return date(next_year, next_month, min(base_date.day, max_day))

    @staticmethod
    def _split_installment_amounts(*, total_amount: float, installment_count: int) -> list[float]:
        safe_count = max(1, int(installment_count or 1))
        safe_total = max(float(total_amount or 0), 0.0)
        if safe_count == 1:
            return [round(safe_total, 2)]

        per = round(safe_total / safe_count, 2)
        values = [per for _ in range(safe_count)]
        values[-1] = round(safe_total - sum(values[:-1]), 2)
        return values

    @classmethod
    def _build_installment_schedule_amounts(
        cls,
        *,
        total_amount: float,
        installment_count: int,
        first_paid_amount: float,
    ) -> list[float]:
        safe_total = max(float(total_amount or 0), 0.0)
        safe_count = max(1, int(installment_count or 1))
        paid = max(min(float(first_paid_amount or 0), safe_total), 0.0)

        if safe_count == 1:
            return [round(safe_total, 2)]

        remaining_count = safe_count - 1
        remaining_amount = max(safe_total - paid, 0.0)
        remaining = cls._split_installment_amounts(total_amount=remaining_amount, installment_count=remaining_count)
        return [round(paid, 2), *remaining]


    @staticmethod
    def _month_key_local(value: datetime, *, tz) -> str:
        return value.astimezone(tz).strftime("%Y-%m")

    @staticmethod
    def _parse_month_key(month: str | None, *, fallback: datetime) -> tuple[int, int]:
        if not month:
            return fallback.year, fallback.month
        parts = month.strip().split("-")
        if len(parts) != 2:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="month must be in YYYY-MM format")
        try:
            year = int(parts[0])
            month_value = int(parts[1])
        except ValueError as exc:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="month must be in YYYY-MM format",
            ) from exc
        if year < 2020 or year > 2100 or month_value < 1 or month_value > 12:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="month must be in YYYY-MM format")
        return year, month_value

    async def fee_monthly_analytics(self, *, months: int, month: str | None) -> dict:
        months_count = max(3, min(int(months), 24))
        now_local = datetime.now(app_timezone())
        end_year, end_month = self._parse_month_key(month, fallback=now_local)
        start_year, start_month = self._add_months(end_year, end_month, -(months_count - 1))
        start_key = f"{start_year:04d}-{start_month:02d}"

        month_keys: list[str] = []
        month_labels: dict[str, str] = {}
        cursor_year, cursor_month = start_year, start_month
        for _ in range(months_count):
            key = f"{cursor_year:04d}-{cursor_month:02d}"
            month_keys.append(key)
            month_labels[key] = datetime(cursor_year, cursor_month, 1).strftime("%b %Y")
            cursor_year, cursor_month = self._add_months(cursor_year, cursor_month, 1)

        assignment_rows = (
            await self.session.execute(
                select(StudentFeeStructureAssignment.created_at, FeeStructure.total_amount)
                .join(FeeStructure, FeeStructure.id == StudentFeeStructureAssignment.fee_structure_id)
                .where(StudentFeeStructureAssignment.is_active.is_(True))
            )
        ).all()

        payment_rows = (
            await self.session.execute(
                select(PaymentTransaction.amount, PaymentTransaction.paid_at, PaymentTransaction.created_at)
                .where(PaymentTransaction.status == "success")
            )
        ).all()

        monthly_assigned: dict[str, float] = {key: 0.0 for key in month_keys}
        monthly_collected: dict[str, float] = {key: 0.0 for key in month_keys}
        assigned_before_range = 0.0
        collected_before_range = 0.0
        local_tz = app_timezone()

        for created_at, total_amount in assignment_rows:
            if created_at is None or total_amount is None:
                continue
            key = self._month_key_local(created_at, tz=local_tz)
            amount = float(total_amount or 0)
            if key < start_key:
                assigned_before_range += amount
            elif key in monthly_assigned:
                monthly_assigned[key] += amount

        for amount_raw, paid_at, created_at in payment_rows:
            effective_dt = paid_at or created_at
            if effective_dt is None:
                continue
            key = self._month_key_local(effective_dt, tz=local_tz)
            amount = float(amount_raw or 0)
            if key < start_key:
                collected_before_range += amount
            elif key in monthly_collected:
                monthly_collected[key] += amount

        cumulative_assigned = assigned_before_range
        cumulative_collected = collected_before_range
        items: list[dict] = []

        for key in month_keys:
            month_assigned = round(monthly_assigned.get(key, 0.0), 2)
            month_collected = round(monthly_collected.get(key, 0.0), 2)
            cumulative_assigned = round(cumulative_assigned + month_assigned, 2)
            cumulative_collected = round(cumulative_collected + month_collected, 2)
            month_pending = round(max(cumulative_assigned - cumulative_collected, 0.0), 2)
            items.append(
                {
                    "month": key,
                    "label": month_labels[key],
                    "collected_amount": month_collected,
                    "pending_amount": month_pending,
                    "assigned_amount": cumulative_assigned,
                    "cumulative_collected_amount": cumulative_collected,
                }
            )

        selected_month = f"{end_year:04d}-{end_month:02d}"
        selected_item = next((item for item in items if item["month"] == selected_month), None)
        if selected_item is None and items:
            selected_item = items[-1]

        return {
            "months": items,
            "selected_month": selected_item["month"] if selected_item else selected_month,
            "selected": selected_item,
            "totals": {
                "assigned_amount": round(cumulative_assigned, 2),
                "collected_amount": round(cumulative_collected, 2),
                "pending_amount": round(max(cumulative_assigned - cumulative_collected, 0.0), 2),
            },
        }

    async def list_fee_students(
        self,
        *,
        view: str,
        search: str | None,
        class_level: int | None,
        stream: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        payment_rollup = self._student_payment_rollup_subquery()

        query = (
            select(
                StudentProfile,
                User,
                Batch,
                Standard,
                StudentFeeStructureAssignment.id.label("assignment_id"),
                FeeStructure.id.label("fee_structure_id"),
                FeeStructure.name.label("fee_structure_name"),
                FeeStructure.total_amount.label("fee_structure_amount"),
                FeeStructure.installment_count.label("fee_structure_installment_count"),
                func.coalesce(payment_rollup.c.paid_amount, 0).label("paid_amount"),
                func.coalesce(payment_rollup.c.installments_paid_count, 0).label("installments_paid_count"),
                payment_rollup.c.last_paid_at.label("last_paid_at"),
            )
            .join(User, User.id == StudentProfile.user_id)
            .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
            .outerjoin(Standard, Standard.id == Batch.standard_id)
            .outerjoin(
                StudentFeeStructureAssignment,
                and_(
                    StudentFeeStructureAssignment.student_id == StudentProfile.id,
                    StudentFeeStructureAssignment.is_active.is_(True),
                ),
            )
            .outerjoin(FeeStructure, FeeStructure.id == StudentFeeStructureAssignment.fee_structure_id)
            .outerjoin(payment_rollup, payment_rollup.c.student_id == StudentProfile.id)
        )

        filters = []
        if search:
            filters.append(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                    User.phone.ilike(f"%{search}%"),
                    StudentProfile.admission_no.ilike(f"%{search}%"),
                    StudentProfile.parent_contact_number.ilike(f"%{search}%"),
                )
            )

        if class_level is not None:
            filters.append(
                or_(
                    StudentProfile.class_name.ilike(f"%{class_level}%"),
                    Standard.name.ilike(f"%{class_level}%"),
                )
            )

        normalized_stream = self._normalize_fee_stream(stream)
        if normalized_stream:
            filters.append(StudentProfile.stream.ilike(f"%{normalized_stream}%"))

        if filters:
            query = query.where(and_(*filters))

        rows = (
            await self.session.execute(query.order_by(User.full_name.asc()))
        ).all()

        student_ids = [row[0].id for row in rows]
        overdue_tracker: dict[str, dict] = {}
        if student_ids:
            invoice_rows = (
                await self.session.execute(
                    select(
                        FeeInvoice.student_id,
                        FeeInvoice.due_date,
                        FeeInvoice.amount,
                        FeeInvoice.balance_amount,
                        FeeInvoice.status,
                    ).where(
                        FeeInvoice.student_id.in_(student_ids),
                        FeeInvoice.installment_no.is_not(None),
                    )
                )
            ).all()

            today_local = datetime.now(app_timezone()).date()
            for student_id_key, due_date, amount, balance_amount, status_value in invoice_rows:
                outstanding = float(balance_amount if balance_amount is not None else (amount or 0))
                tracker = overdue_tracker.setdefault(
                    student_id_key,
                    {
                        "next_due_date": None,
                        "missed_payment_count": 0,
                        "missed_payment_amount": 0.0,
                        "installments_paid_count": 0,
                    },
                )
                if outstanding <= 0.0001 or status_value == "paid":
                    tracker["installments_paid_count"] += 1
                    continue

                if due_date and (tracker["next_due_date"] is None or due_date < tracker["next_due_date"]):
                    tracker["next_due_date"] = due_date

                if due_date and due_date < today_local:
                    tracker["missed_payment_count"] += 1
                    tracker["missed_payment_amount"] = round(float(tracker["missed_payment_amount"]) + outstanding, 2)

        all_items = []
        for (
            profile,
            user,
            _,
            standard,
            assignment_id,
            fee_structure_id,
            fee_structure_name,
            fee_structure_amount,
            fee_structure_installment_count,
            paid_amount_raw,
            installments_paid_count_raw,
            last_paid_at,
        ) in rows:
            fee_amount = float(fee_structure_amount) if fee_structure_amount is not None else None
            paid_amount_raw_float = float(paid_amount_raw or 0)
            paid_amount, pending_amount, is_fully_paid = self._compute_fee_progress(
                fee_amount=fee_amount,
                paid_amount=paid_amount_raw_float,
            )

            payment_status = "not_assigned"
            if fee_amount is not None:
                payment_status = "paid" if is_fully_paid else "pending"

            class_name = profile.class_name or (standard.name if standard else None)
            grade = self._extract_grade(profile.class_name, standard.name if standard else None)
            class_level_value = int(grade) if grade is not None else None
            installment_target_count = int(fee_structure_installment_count) if fee_structure_installment_count else None
            tracker = overdue_tracker.get(profile.id, {})
            installments_paid_count = int(tracker.get("installments_paid_count", 0) or 0)
            next_due_date = tracker.get("next_due_date")
            missed_payment_count = int(tracker.get("missed_payment_count", 0) or 0)
            missed_payment_amount = float(tracker.get("missed_payment_amount", 0) or 0)

            item = {
                "student_id": profile.id,
                "user_id": user.id,
                "full_name": user.full_name,
                "phone": user.phone,
                "parent_contact_number": profile.parent_contact_number,
                "class_name": class_name,
                "class_level": class_level_value,
                "stream": self._stream_for_display(class_level_value, profile.stream),
                "invoice_count": installments_paid_count,
                "installments_paid_count": installments_paid_count,
                "installment_target_count": installment_target_count,
                "total_amount": float(fee_amount or 0),
                "paid_amount": paid_amount,
                "pending_amount": pending_amount,
                "next_due_date": next_due_date.isoformat() if next_due_date else None,
                "missed_payment_count": missed_payment_count,
                "missed_payment_amount": round(missed_payment_amount, 2),
                "is_overdue": missed_payment_count > 0,
                "last_paid_at": last_paid_at.isoformat() if last_paid_at else None,
                "payment_status": payment_status,
                "is_fully_paid": is_fully_paid,
                "account_status": user.status.value if hasattr(user.status, "value") else str(user.status),
                "fee_structure_assigned": assignment_id is not None,
                "fee_structure_id": fee_structure_id,
                "fee_structure_name": fee_structure_name,
                "fee_amount": fee_amount,
            }

            if view == "pending" and payment_status != "pending":
                continue
            if view == "paid" and payment_status != "paid":
                continue

            all_items.append(item)

        total = len(all_items)
        paginated_items = all_items[offset : offset + limit]
        return paginated_items, total

    async def list_fee_overdue_students(
        self,
        *,
        search: str | None,
        class_level: int | None,
        stream: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        today_local = datetime.now(app_timezone()).date()

        query = (
            select(FeeInvoice, StudentProfile, User, Standard)
            .join(StudentProfile, StudentProfile.id == FeeInvoice.student_id)
            .join(User, User.id == StudentProfile.user_id)
            .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
            .outerjoin(Standard, Standard.id == Batch.standard_id)
            .where(
                FeeInvoice.installment_no.is_not(None),
                FeeInvoice.status != "paid",
                FeeInvoice.due_date < today_local,
            )
            .order_by(FeeInvoice.due_date.asc(), User.full_name.asc())
        )

        filters = []
        if search:
            filters.append(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                    User.phone.ilike(f"%{search}%"),
                    StudentProfile.admission_no.ilike(f"%{search}%"),
                    StudentProfile.parent_contact_number.ilike(f"%{search}%"),
                )
            )

        if class_level is not None:
            filters.append(
                or_(
                    StudentProfile.class_name.ilike(f"%{class_level}%"),
                    Standard.name.ilike(f"%{class_level}%"),
                )
            )

        normalized_stream = self._normalize_fee_stream(stream)
        if normalized_stream:
            filters.append(StudentProfile.stream.ilike(f"%{normalized_stream}%"))

        if filters:
            query = query.where(and_(*filters))

        rows = (await self.session.execute(query)).all()

        grouped: dict[str, dict] = {}
        for invoice, profile, user, standard in rows:
            outstanding = float(invoice.balance_amount if invoice.balance_amount is not None else (invoice.amount or 0))
            if outstanding <= 0.0001:
                continue

            class_name = profile.class_name or (standard.name if standard else None)
            grade = self._extract_grade(profile.class_name, standard.name if standard else None)
            class_level_value = int(grade) if grade is not None else None

            bucket = grouped.setdefault(
                profile.id,
                {
                    "student_id": profile.id,
                    "user_id": user.id,
                    "full_name": user.full_name,
                    "phone": user.phone,
                    "parent_contact_number": profile.parent_contact_number,
                    "class_name": class_name,
                    "class_level": class_level_value,
                    "stream": self._stream_for_display(class_level_value, profile.stream),
                    "overdue_amount": 0.0,
                    "overdue_installments": 0,
                    "earliest_due_date": None,
                    "latest_due_date": None,
                    "last_reminder_sent_at": None,
                    "invoices": [],
                },
            )

            bucket["overdue_amount"] = round(float(bucket["overdue_amount"]) + outstanding, 2)
            bucket["overdue_installments"] = int(bucket["overdue_installments"]) + 1

            if invoice.due_date and (bucket["earliest_due_date"] is None or invoice.due_date < bucket["earliest_due_date"]):
                bucket["earliest_due_date"] = invoice.due_date
            if invoice.due_date and (bucket["latest_due_date"] is None or invoice.due_date > bucket["latest_due_date"]):
                bucket["latest_due_date"] = invoice.due_date

            if invoice.last_reminder_sent_at and (
                bucket["last_reminder_sent_at"] is None or invoice.last_reminder_sent_at > bucket["last_reminder_sent_at"]
            ):
                bucket["last_reminder_sent_at"] = invoice.last_reminder_sent_at

            days_overdue = (today_local - invoice.due_date).days if invoice.due_date else 0
            bucket["invoices"].append(
                {
                    "invoice_id": invoice.id,
                    "invoice_no": invoice.invoice_no,
                    "installment_no": invoice.installment_no,
                    "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                    "days_overdue": max(days_overdue, 0),
                    "status": invoice.status,
                    "amount": float(invoice.amount or 0),
                    "balance_amount": outstanding,
                    "reminder_enabled": bool(invoice.reminder_enabled),
                    "last_reminder_sent_at": invoice.last_reminder_sent_at.isoformat() if invoice.last_reminder_sent_at else None,
                }
            )

        items: list[dict] = []
        for bucket in grouped.values():
            earliest_due = bucket["earliest_due_date"]
            latest_due = bucket["latest_due_date"]
            days_overdue = (today_local - earliest_due).days if earliest_due else 0
            items.append(
                {
                    "student_id": bucket["student_id"],
                    "user_id": bucket["user_id"],
                    "full_name": bucket["full_name"],
                    "phone": bucket["phone"],
                    "parent_contact_number": bucket["parent_contact_number"],
                    "class_name": bucket["class_name"],
                    "class_level": bucket["class_level"],
                    "stream": bucket["stream"],
                    "overdue_amount": round(float(bucket["overdue_amount"]), 2),
                    "overdue_installments": int(bucket["overdue_installments"]),
                    "earliest_due_date": earliest_due.isoformat() if earliest_due else None,
                    "latest_due_date": latest_due.isoformat() if latest_due else None,
                    "days_overdue": max(days_overdue, 0),
                    "last_reminder_sent_at": bucket["last_reminder_sent_at"].isoformat() if bucket["last_reminder_sent_at"] else None,
                    "invoices": sorted(
                        bucket["invoices"],
                        key=lambda row: ((row.get("due_date") or "9999-12-31"), str(row.get("invoice_no") or "")),
                    ),
                }
            )

        items.sort(key=lambda row: (-int(row["days_overdue"] or 0), -float(row["overdue_amount"] or 0), str(row["full_name"] or "")))

        total = len(items)
        paginated_items = items[offset : offset + limit]
        return paginated_items, total


    async def send_fee_overdue_reminders(
        self,
        *,
        payload: AdminFeeOverdueReminderDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        requested_student_ids = {sid.strip() for sid in (payload.student_ids or []) if sid and sid.strip()}
        today_local = datetime.now(app_timezone()).date()

        query = (
            select(FeeInvoice, StudentProfile, User)
            .join(StudentProfile, StudentProfile.id == FeeInvoice.student_id)
            .join(User, User.id == StudentProfile.user_id)
            .where(
                FeeInvoice.installment_no.is_not(None),
                FeeInvoice.status != "paid",
                FeeInvoice.due_date < today_local,
            )
            .order_by(FeeInvoice.due_date.asc(), FeeInvoice.created_at.asc())
        )
        if requested_student_ids:
            query = query.where(StudentProfile.id.in_(requested_student_ids))

        rows = (await self.session.execute(query)).all()
        if not rows:
            return {
                "recipients_count": 0,
                "sent_count": 0,
                "students": [],
            }

        grouped: dict[str, dict] = {}
        invoice_ids_to_touch: set[str] = set()

        for invoice, profile, user in rows:
            outstanding = float(invoice.balance_amount if invoice.balance_amount is not None else (invoice.amount or 0))
            if outstanding <= 0.0001:
                continue

            invoice_ids_to_touch.add(invoice.id)
            student_bucket = grouped.setdefault(
                profile.id,
                {
                    "student_id": profile.id,
                    "user_id": user.id,
                    "student_name": user.full_name,
                    "class_name": profile.class_name,
                    "stream": profile.stream,
                    "phone": user.phone,
                    "parent_contact_number": profile.parent_contact_number,
                    "overdue_amount": 0.0,
                    "earliest_due_date": invoice.due_date,
                    "invoice_nos": [],
                },
            )

            student_bucket["overdue_amount"] = round(float(student_bucket["overdue_amount"]) + outstanding, 2)
            if invoice.due_date and (
                student_bucket["earliest_due_date"] is None or invoice.due_date < student_bucket["earliest_due_date"]
            ):
                student_bucket["earliest_due_date"] = invoice.due_date
            student_bucket["invoice_nos"].append(invoice.invoice_no)

        if not grouped:
            return {
                "recipients_count": 0,
                "sent_count": 0,
                "students": [],
            }

        custom_message = (payload.message or "").strip()
        now_utc = datetime.now(UTC)
        deliveries: list[NotificationDelivery] = []
        notifications: list[Notification] = []

        for entry in grouped.values():
            if custom_message:
                body = custom_message
            else:
                due_text = entry["earliest_due_date"].strftime("%d/%m/%Y") if entry["earliest_due_date"] else "today"
                body = (
                    f"You missed a fee installment due on {due_text}. "
                    f"Pending amount: {self._format_inr(float(entry['overdue_amount'] or 0))}. "
                    "Please pay soon or contact admin."
                )

            notification = Notification(
                recipient_user_id=entry["user_id"],
                notification_type=NotificationType.SYSTEM,
                title="Fee Payment Overdue",
                body=body,
                metadata_json={
                    "source": "fee_reminder",
                    "student_id": entry["student_id"],
                    "overdue_amount": float(entry["overdue_amount"] or 0),
                    "earliest_due_date": entry["earliest_due_date"].isoformat() if entry["earliest_due_date"] else None,
                    "invoice_nos": entry["invoice_nos"][:10],
                },
                is_read=False,
            )
            self.session.add(notification)
            notifications.append(notification)

        await self.session.flush()

        for notification in notifications:
            delivery = NotificationDelivery(
                notification_id=notification.id,
                channel=DeliveryChannel.IN_APP,
                status="delivered",
                attempt_no=1,
                provider_response=json.dumps({"delivered_at": now_utc.isoformat()}),
            )
            self.session.add(delivery)
            deliveries.append(delivery)

        if invoice_ids_to_touch:
            await self.session.execute(
                update(FeeInvoice)
                .where(FeeInvoice.id.in_(invoice_ids_to_touch))
                .values(last_reminder_sent_at=now_utc, reminder_enabled=True)
            )

        students_payload = [
            {
                "student_id": entry["student_id"],
                "student_name": entry["student_name"],
                "class_name": entry["class_name"],
                "stream": entry["stream"],
                "parent_contact_number": entry["parent_contact_number"],
                "overdue_amount": float(entry["overdue_amount"] or 0),
                "earliest_due_date": entry["earliest_due_date"].isoformat() if entry["earliest_due_date"] else None,
                "invoice_count": len(entry["invoice_nos"]),
            }
            for entry in grouped.values()
        ]

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.fee.overdue_reminder.send",
            entity_type="fee_invoice",
            entity_id="bulk",
            before_state=None,
            after_state={
                "recipients_count": len(students_payload),
                "students": students_payload,
                "custom_message": custom_message or None,
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "recipients_count": len(students_payload),
            "sent_count": len(notifications),
            "students": students_payload,
        }

    async def get_daily_activity_tracker(
        self,
        *,
        day: date,
        search: str | None,
    ) -> dict:
        tz = app_timezone()
        day_start_local = datetime.combine(day, time.min, tzinfo=tz)
        day_end_local = day_start_local + timedelta(days=1)
        day_start_utc = day_start_local.astimezone(UTC)
        day_end_utc = day_end_local.astimezone(UTC)

        now_local = datetime.now(tz)
        day_is_past = day < now_local.date()

        lecture_query = (
            select(LectureSchedule, Subject, TeacherProfile, User)
            .join(Subject, Subject.id == LectureSchedule.subject_id)
            .join(TeacherProfile, TeacherProfile.id == LectureSchedule.teacher_id)
            .join(User, User.id == TeacherProfile.user_id)
            .where(
                LectureSchedule.scheduled_at >= day_start_utc,
                LectureSchedule.scheduled_at < day_end_utc,
            )
        )
        if search:
            lecture_query = lecture_query.where(
                or_(
                    LectureSchedule.topic.ilike(f"%{search}%"),
                    Subject.name.ilike(f"%{search}%"),
                    User.full_name.ilike(f"%{search}%"),
                )
            )

        lecture_rows = (
            await self.session.execute(
                lecture_query.order_by(LectureSchedule.scheduled_at.asc(), LectureSchedule.created_at.desc())
            )
        ).all()

        lectures: list[dict] = []
        lecture_class_map: dict[tuple[int, str], dict] = {}
        lecture_scheduled_count = 0
        lecture_completed_count = 0
        delayed_teacher_count = 0

        for schedule, subject, _teacher, teacher_user in lecture_rows:
            status_value = schedule.status.value if hasattr(schedule.status, "value") else str(schedule.status)
            schedule_local = to_app_timezone(schedule.scheduled_at)
            completed_local = to_app_timezone(schedule.completed_at)
            stream_value = self._normalize_stream(schedule.stream)
            class_key = (int(schedule.class_level), stream_value)
            bucket = lecture_class_map.setdefault(
                class_key,
                {
                    "class_level": int(schedule.class_level),
                    "stream": stream_value,
                    "scheduled": 0,
                    "completed": 0,
                    "pending": 0,
                    "canceled": 0,
                },
            )

            bucket["scheduled"] += 1
            lecture_scheduled_count += 1

            delayed = False
            if status_value == LectureScheduleStatus.DONE.value:
                lecture_completed_count += 1
                bucket["completed"] += 1
            elif status_value == LectureScheduleStatus.CANCELED.value:
                bucket["canceled"] += 1
            else:
                bucket["pending"] += 1
                if schedule_local:
                    if day_is_past and status_value == LectureScheduleStatus.SCHEDULED.value:
                        delayed = True
                    elif day == now_local.date() and schedule_local < now_local and status_value == LectureScheduleStatus.SCHEDULED.value:
                        delayed = True

            if delayed:
                delayed_teacher_count += 1

            lectures.append(
                {
                    "id": schedule.id,
                    "class_level": int(schedule.class_level),
                    "stream": stream_value,
                    "subject_name": subject.name,
                    "teacher_name": teacher_user.full_name,
                    "topic": schedule.topic,
                    "status": status_value,
                    "scheduled_at": schedule_local.isoformat() if schedule_local else None,
                    "completed_at": completed_local.isoformat() if completed_local else None,
                    "is_delayed": delayed,
                }
            )

        attendance_rows = (
            await self.session.execute(
                select(AttendanceRecord, StudentProfile, User, Batch, Standard)
                .join(StudentProfile, StudentProfile.id == AttendanceRecord.student_id)
                .join(User, User.id == StudentProfile.user_id)
                .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
                .outerjoin(Standard, Standard.id == Batch.standard_id)
                .where(AttendanceRecord.attendance_date == day)
                .order_by(User.full_name.asc())
            )
        ).all()

        attendance_summary = {
            "total_marked": 0,
            "present": 0,
            "absent": 0,
            "late": 0,
            "leave": 0,
            "attended": 0,
            "missed": 0,
        }
        attendance_class_map: dict[tuple[int, str], dict] = {}

        for record, profile, user, _batch, standard in attendance_rows:
            grade = self._extract_grade(profile.class_name, standard.name if standard else None)
            class_level_value = int(grade) if grade is not None else 0
            stream_value = self._normalize_stream(profile.stream)
            class_key = (class_level_value, stream_value)

            status_value = record.status.value if hasattr(record.status, "value") else str(record.status)

            bucket = attendance_class_map.setdefault(
                class_key,
                {
                    "class_level": class_level_value,
                    "stream": stream_value,
                    "total_marked": 0,
                    "present": 0,
                    "absent": 0,
                    "late": 0,
                    "leave": 0,
                    "attended": 0,
                    "missed": 0,
                    "missed_students": [],
                },
            )

            attendance_summary["total_marked"] += 1
            bucket["total_marked"] += 1

            if status_value == AttendanceStatus.PRESENT.value:
                attendance_summary["present"] += 1
                bucket["present"] += 1
                attendance_summary["attended"] += 1
                bucket["attended"] += 1
            elif status_value == AttendanceStatus.LATE.value:
                attendance_summary["late"] += 1
                bucket["late"] += 1
                attendance_summary["attended"] += 1
                bucket["attended"] += 1
            elif status_value == AttendanceStatus.ABSENT.value:
                attendance_summary["absent"] += 1
                bucket["absent"] += 1
                attendance_summary["missed"] += 1
                bucket["missed"] += 1
                bucket["missed_students"].append(
                    {
                        "student_id": profile.id,
                        "full_name": user.full_name,
                        "admission_no": profile.admission_no,
                        "roll_no": profile.roll_no,
                        "status": status_value,
                    }
                )
            elif status_value == AttendanceStatus.LEAVE.value:
                attendance_summary["leave"] += 1
                bucket["leave"] += 1
                attendance_summary["missed"] += 1
                bucket["missed"] += 1
                bucket["missed_students"].append(
                    {
                        "student_id": profile.id,
                        "full_name": user.full_name,
                        "admission_no": profile.admission_no,
                        "roll_no": profile.roll_no,
                        "status": status_value,
                    }
                )

        test_query = (
            select(Assessment, Subject)
            .join(Subject, Subject.id == Assessment.subject_id)
            .where(
                Assessment.starts_at.is_not(None),
                Assessment.starts_at >= day_start_utc,
                Assessment.starts_at < day_end_utc,
            )
        )
        if search:
            test_query = test_query.where(
                or_(
                    Assessment.title.ilike(f"%{search}%"),
                    Assessment.topic.ilike(f"%{search}%"),
                    Subject.name.ilike(f"%{search}%"),
                )
            )

        test_rows = (await self.session.execute(test_query.order_by(Assessment.starts_at.asc()))).all()

        tests: list[dict] = []
        test_class_map: dict[tuple[int, str], dict] = {}
        test_scheduled_count = 0
        test_done_count = 0
        test_pending_count = 0

        for assessment, subject in test_rows:
            class_level_value = int(assessment.class_level or 0)
            stream_value = self._normalize_stream(assessment.stream)
            class_key = (class_level_value, stream_value)
            status_value = assessment.status.value if hasattr(assessment.status, "value") else str(assessment.status)
            starts_local = to_app_timezone(assessment.starts_at)
            ends_local = to_app_timezone(assessment.ends_at)
            type_value = assessment.assessment_type.value if hasattr(assessment.assessment_type, "value") else str(assessment.assessment_type)

            bucket = test_class_map.setdefault(
                class_key,
                {
                    "class_level": class_level_value,
                    "stream": stream_value,
                    "scheduled": 0,
                    "done": 0,
                    "pending": 0,
                },
            )
            bucket["scheduled"] += 1
            test_scheduled_count += 1
            if status_value == AssessmentStatus.COMPLETED.value:
                bucket["done"] += 1
                test_done_count += 1
            else:
                bucket["pending"] += 1
                test_pending_count += 1

            tests.append(
                {
                    "assessment_id": assessment.id,
                    "title": assessment.title,
                    "topic": assessment.topic,
                    "class_level": class_level_value,
                    "stream": stream_value,
                    "subject_name": subject.name,
                    "assessment_type": type_value,
                    "status": status_value,
                    "starts_at": starts_local.isoformat() if starts_local else None,
                    "ends_at": ends_local.isoformat() if ends_local else None,
                    "total_marks": float(assessment.total_marks or 0),
                    "passing_marks": float(assessment.passing_marks or 0),
                }
            )

        student_role_id = (
            await self.session.execute(select(Role.id).where(Role.code == RoleCode.STUDENT))
        ).scalar_one_or_none()

        admissions: list[dict] = []
        if student_role_id:
            admission_rows = (
                await self.session.execute(
                    select(StudentProfile, User, Batch, Standard)
                    .join(User, User.id == StudentProfile.user_id)
                    .join(UserRole, and_(UserRole.user_id == User.id, UserRole.role_id == student_role_id))
                    .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
                    .outerjoin(Standard, Standard.id == Batch.standard_id)
                    .where(
                        User.created_at >= day_start_utc,
                        User.created_at < day_end_utc,
                    )
                    .order_by(User.created_at.desc())
                )
            ).all()

            for profile, user, _batch, standard in admission_rows:
                grade = self._extract_grade(profile.class_name, standard.name if standard else None)
                class_level_value = int(grade) if grade is not None else None
                admissions.append(
                    {
                        "student_id": profile.id,
                        "full_name": user.full_name,
                        "phone": user.phone,
                        "admission_no": profile.admission_no,
                        "roll_no": profile.roll_no,
                        "class_level": class_level_value,
                        "stream": self._normalize_stream(profile.stream),
                        "created_at": to_app_timezone(user.created_at).isoformat() if user.created_at else None,
                    }
                )

        payment_time_clause = or_(
            and_(
                PaymentTransaction.paid_at.is_not(None),
                PaymentTransaction.paid_at >= day_start_utc,
                PaymentTransaction.paid_at < day_end_utc,
            ),
            and_(
                PaymentTransaction.paid_at.is_(None),
                PaymentTransaction.created_at >= day_start_utc,
                PaymentTransaction.created_at < day_end_utc,
            ),
        )

        payment_rows = (
            await self.session.execute(
                select(PaymentTransaction, StudentProfile, User)
                .join(StudentProfile, StudentProfile.id == PaymentTransaction.student_id)
                .join(User, User.id == StudentProfile.user_id)
                .where(
                    PaymentTransaction.status == "success",
                    payment_time_clause,
                )
                .order_by(PaymentTransaction.paid_at.desc(), PaymentTransaction.created_at.desc())
            )
        ).all()

        fee_payments: list[dict] = []
        fee_paid_students = set()
        fee_paid_total = 0.0
        for tx, profile, user in payment_rows:
            paid_at = to_app_timezone(tx.paid_at or tx.created_at)
            amount = float(tx.amount or 0)
            fee_paid_total += amount
            fee_paid_students.add(profile.id)
            fee_payments.append(
                {
                    "transaction_id": tx.id,
                    "student_id": profile.id,
                    "full_name": user.full_name,
                    "admission_no": profile.admission_no,
                    "amount": amount,
                    "payment_mode": tx.payment_mode,
                    "reference_no": tx.external_ref,
                    "paid_at": paid_at.isoformat() if paid_at else None,
                }
            )

        overdue_rows = (
            await self.session.execute(
                select(FeeInvoice, StudentProfile, User)
                .join(StudentProfile, StudentProfile.id == FeeInvoice.student_id)
                .join(User, User.id == StudentProfile.user_id)
                .where(
                    FeeInvoice.status != "paid",
                    FeeInvoice.due_date < day,
                )
                .order_by(FeeInvoice.due_date.asc())
                .limit(200)
            )
        ).all()

        overdue_items: list[dict] = []
        overdue_students = set()
        for invoice, profile, user in overdue_rows:
            overdue_students.add(profile.id)
            overdue_items.append(
                {
                    "invoice_id": invoice.id,
                    "invoice_no": invoice.invoice_no,
                    "student_id": profile.id,
                    "full_name": user.full_name,
                    "admission_no": profile.admission_no,
                    "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                    "amount": float(invoice.amount or 0),
                    "balance_amount": float(invoice.balance_amount or invoice.amount or 0),
                    "status": invoice.status,
                }
            )

        # quick recent-days summary (last 7 days up to selected day)
        recent_days: list[dict] = []
        recent_from_local = day_start_local - timedelta(days=6)
        recent_to_local = day_end_local
        recent_from_utc = recent_from_local.astimezone(UTC)
        recent_to_utc = recent_to_local.astimezone(UTC)

        recent_lecture_ts = (
            await self.session.execute(
                select(LectureSchedule.scheduled_at, LectureSchedule.status)
                .where(
                    LectureSchedule.scheduled_at >= recent_from_utc,
                    LectureSchedule.scheduled_at < recent_to_utc,
                )
            )
        ).all()
        recent_test_ts = (
            await self.session.execute(
                select(Assessment.starts_at)
                .where(
                    Assessment.starts_at.is_not(None),
                    Assessment.starts_at >= recent_from_utc,
                    Assessment.starts_at < recent_to_utc,
                )
            )
        ).all()

        recent_admission_ts = []
        if student_role_id:
            recent_admission_ts = (
                await self.session.execute(
                    select(User.created_at)
                    .join(UserRole, and_(UserRole.user_id == User.id, UserRole.role_id == student_role_id))
                    .where(
                        User.created_at >= recent_from_utc,
                        User.created_at < recent_to_utc,
                    )
                )
            ).all()

        recent_payment_ts = (
            await self.session.execute(
                select(PaymentTransaction.paid_at, PaymentTransaction.created_at)
                .where(
                    PaymentTransaction.status == "success",
                    or_(
                        and_(
                            PaymentTransaction.paid_at.is_not(None),
                            PaymentTransaction.paid_at >= recent_from_utc,
                            PaymentTransaction.paid_at < recent_to_utc,
                        ),
                        and_(
                            PaymentTransaction.paid_at.is_(None),
                            PaymentTransaction.created_at >= recent_from_utc,
                            PaymentTransaction.created_at < recent_to_utc,
                        ),
                    ),
                )
            )
        ).all()

        day_index: dict[date, dict] = {}
        for offset in range(6, -1, -1):
            current_day = day - timedelta(days=offset)
            day_index[current_day] = {
                "date": current_day.isoformat(),
                "label": current_day.strftime("%d %b"),
                "lectures_scheduled": 0,
                "lectures_completed": 0,
                "tests_scheduled": 0,
                "new_admissions": 0,
                "fee_payments": 0,
            }

        for scheduled_at, status in recent_lecture_ts:
            local_dt = to_app_timezone(scheduled_at)
            if not local_dt:
                continue
            d = local_dt.date()
            if d not in day_index:
                continue
            day_index[d]["lectures_scheduled"] += 1
            status_value = status.value if hasattr(status, "value") else str(status)
            if status_value == LectureScheduleStatus.DONE.value:
                day_index[d]["lectures_completed"] += 1

        for (starts_at,) in recent_test_ts:
            local_dt = to_app_timezone(starts_at)
            if not local_dt:
                continue
            d = local_dt.date()
            if d in day_index:
                day_index[d]["tests_scheduled"] += 1

        for (created_at,) in recent_admission_ts:
            local_dt = to_app_timezone(created_at)
            if not local_dt:
                continue
            d = local_dt.date()
            if d in day_index:
                day_index[d]["new_admissions"] += 1

        for paid_at, created_at in recent_payment_ts:
            local_dt = to_app_timezone(paid_at or created_at)
            if not local_dt:
                continue
            d = local_dt.date()
            if d in day_index:
                day_index[d]["fee_payments"] += 1

        recent_days = [day_index[key] for key in sorted(day_index.keys())]

        return {
            "date": day.isoformat(),
            "timezone": str(tz),
            "summary": {
                "lectures_scheduled": lecture_scheduled_count,
                "lectures_completed": lecture_completed_count,
                "teachers_delayed_start": delayed_teacher_count,
                "attendance_marked_students": attendance_summary["total_marked"],
                "attendance_attended": attendance_summary["attended"],
                "attendance_missed": attendance_summary["missed"],
                "attendance_present": attendance_summary["present"],
                "attendance_absent": attendance_summary["absent"],
                "attendance_late": attendance_summary["late"],
                "attendance_leave": attendance_summary["leave"],
                "tests_scheduled": test_scheduled_count,
                "tests_done": test_done_count,
                "tests_pending": test_pending_count,
                "new_admissions": len(admissions),
                "fee_payments_count": len(fee_payments),
                "fee_payments_students": len(fee_paid_students),
                "fee_paid_amount": round(fee_paid_total, 2),
                "overdue_students": len(overdue_students),
                "overdue_invoices": len(overdue_items),
            },
            "recent_days": recent_days,
            "lectures": lectures,
            "attendance": {
                "summary": attendance_summary,
                "class_wise": sorted(
                    attendance_class_map.values(),
                    key=lambda item: (int(item["class_level"] or 0), str(item["stream"] or "common")),
                ),
            },
            "tests": {
                "items": tests,
                "class_wise": sorted(
                    test_class_map.values(),
                    key=lambda item: (int(item["class_level"] or 0), str(item["stream"] or "common")),
                ),
            },
            "admissions": admissions,
            "fee": {
                "payments": fee_payments,
                "overdue": overdue_items,
            },
            "class_wise": {
                "lectures": sorted(
                    lecture_class_map.values(),
                    key=lambda item: (int(item["class_level"] or 0), str(item["stream"] or "common")),
                ),
            },
        }


    async def get_student_fee_receipt(self, *, student_id: str, regenerate: bool = False) -> dict:
        receipt, generated, context = await self._ensure_latest_fee_receipt(
            student_id=student_id,
            regenerate=regenerate,
        )
        if generated:
            await self.session.commit()

        return {
            "student_id": context["student_id"],
            "student_name": context["student_name"],
            "is_fully_paid": context["is_fully_paid"],
            "receipt": receipt,
            "generated": generated,
        }

    async def send_student_fee_receipt_whatsapp(
        self,
        *,
        student_id: str,
        actor_user_id: str,
        ip_address: str | None,
        phone_override: str | None,
        custom_message: str | None,
    ) -> dict:
        receipt, generated, context = await self._ensure_latest_fee_receipt(
            student_id=student_id,
            regenerate=False,
        )

        target_phone = phone_override.strip() if phone_override else (context["parent_contact_number"] or "").strip()
        if not target_phone:
            raise ForbiddenException("Parent contact number is missing for WhatsApp delivery")

        message = self._build_fee_receipt_whatsapp_message(
            context=context,
            receipt=receipt,
            custom_message=custom_message,
        )
        delivery = await self._send_whatsapp_text_message(to_phone=target_phone, message=message)

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.student_fee_receipt.whatsapp",
            entity_type="student_fee_receipt",
            entity_id=context["student_id"],
            before_state=None,
            after_state={
                "student_id": context["student_id"],
                "student_name": context["student_name"],
                "to_phone": delivery.get("to_phone"),
                "delivery_status": delivery.get("status"),
                "provider": delivery.get("provider"),
                "provider_message_id": delivery.get("provider_message_id"),
                "receipt_file": receipt.get("file_name"),
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "student_id": context["student_id"],
            "student_name": context["student_name"],
            "receipt": receipt,
            "delivery": delivery,
            "message": message,
            "receipt_regenerated": generated,
        }
