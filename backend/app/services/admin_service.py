import json
import re
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.config import get_settings
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.security import get_password_hash
from app.db.models.academic import (
    Batch,
    Branch,
    CompletedLecture,
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
from app.db.models.enums import (
    AssessmentStatus,
    AssessmentType,
    AttendanceStatus,
    DoubtStatus,
    HomeworkStatus,
    NoticeStatus,
    NotificationType,
    RoleCode,
    UserStatus,
)
from app.db.models.homework import Homework, HomeworkTarget
from app.db.models.notification import Notification
from app.db.models.results import Result
from app.db.models.user import Role, User, UserRole
from app.schemas.admin import (
    AdminAssessmentCreateDTO,
    AdminAttendanceCorrectionApproveDTO,
    AdminAttendanceCorrectionCreateDTO,
    AdminBannerCreateDTO,
    AdminBannerUpdateDTO,
    AdminBatchCreateDTO,
    AdminDailyThoughtUpsertDTO,
    AdminDoubtUpdateDTO,
    AdminFeeStructureCreateDTO,
    AdminFeeStructureUpdateDTO,
    AdminStudentFeePaymentCreateDTO,
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
)


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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
        if "10" in source:
            return "10"
        if "11" in source:
            return "11"
        if "12" in source:
            return "12"
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

        role_stmt = select(Role).where(Role.code == RoleCode.STUDENT)
        student_role = (await self.session.execute(role_stmt)).scalar_one_or_none()
        if not student_role:
            raise NotFoundException("Student role not configured")

        user = User(
            full_name=payload.full_name,
            email=payload.email,
            phone=payload.phone,
            password_hash=get_password_hash(payload.password),
            status=UserStatus.ACTIVE,
        )
        self.session.add(user)
        await self.session.flush()

        self.session.add(UserRole(user_id=user.id, role_id=student_role.id))

        student_profile = StudentProfile(
            user_id=user.id,
            admission_no=payload.admission_no,
            roll_no=payload.roll_no,
            current_batch_id=payload.batch_id,
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

        await self.session.commit()

        return {
            "student_id": student_profile.id,
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "status": user.status.value,
            "admission_no": student_profile.admission_no,
            "roll_no": student_profile.roll_no,
            "batch_id": student_profile.current_batch_id,
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
            query = query.where(Assessment.assessment_type == AssessmentType(assessment_type))

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
                "starts_at": row.starts_at,
                "ends_at": row.ends_at,
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
        assessment = Assessment(
            title=payload.title,
            description=payload.description,
            subject_id=payload.subject_id,
            assessment_type=AssessmentType(payload.assessment_type),
            status=AssessmentStatus.DRAFT,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
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
        if existing_scope is None:
            self.session.add(
                SubjectAcademicScope(
                    subject_id=subject.id,
                    class_level=payload.class_level,
                    stream=scope_stream,
                )
            )
            scope_added = True

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
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = select(Banner)
        if active_on:
            query = query.where(func.date(Banner.active_from) <= active_on, func.date(Banner.active_to) >= active_on)

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(Banner.priority.desc(), Banner.active_from.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()

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
                "created_at": row.created_at,
            }
            for row in rows
        ], total

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
        if class_level == 10 and stream is not None:
            raise ForbiddenException("Stream is not allowed for class 10 fee structure")
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
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return f"FEE-{timestamp}-{student_id[:4].upper()}-{uuid4().hex[:6].upper()}"

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

    def _persist_fee_receipt_pdf(self, *, context: dict) -> dict:
        payment_rows = context["payment_rows"]
        if not payment_rows:
            raise ForbiddenException("No successful fee payments found for receipt")

        latest_tx, latest_invoice = payment_rows[-1]
        generated_at = datetime.now(UTC)
        media_dir, media_url = self._media_config()
        receipt_dir = media_dir / "receipts"
        receipt_dir.mkdir(parents=True, exist_ok=True)

        file_name = f"FEE-RECEIPT-{context['student_id'][:6].upper()}-{generated_at.strftime('%Y%m%d%H%M%S')}.pdf"
        file_path = receipt_dir / file_name
        download_url = f"{media_url}/receipts/{file_name}"

        settings = get_settings()
        lines: list[str] = [
            settings.institute_display_name,
            "Student Fee Receipt",
            "",
            f"Student: {context['student_name']}",
            f"Class/Stream: {context['class_name']} / {context['stream']}",
            f"Contact: {context['student_phone'] or '-'}",
            f"Parent WhatsApp: {context['parent_contact_number'] or '-'}",
            f"Fee Structure: {context['fee_structure_name']}",
            f"Generated At (UTC): {generated_at.isoformat()}",
            "",
            f"Total Fee: {self._format_inr(context['fee_amount'])}",
            f"Total Paid: {self._format_inr(context['paid_amount'])}",
            f"Pending: {self._format_inr(context['pending_amount'])}",
            f"Installments Paid: {len(payment_rows)}/{context['installment_target_count']}",
            "",
            "Installment Ledger:",
        ]

        for idx, (tx, invoice) in enumerate(payment_rows, start=1):
            paid_at = tx.paid_at.isoformat() if tx.paid_at else tx.created_at.isoformat()
            mode = (tx.payment_mode or "manual").replace("_", " ").title()
            ref = tx.external_ref or "-"
            inst_no = invoice.installment_no if invoice.installment_no is not None else "-"
            lines.append(
                f"{idx}. Inst #{inst_no} | Invoice {invoice.invoice_no} | {self._format_inr(float(tx.amount))} | {mode} | Ref {ref} | {paid_at}"
            )

        lines.extend(["", f"Receipt Download: {download_url}"])
        file_path.write_bytes(self._build_text_pdf(lines))

        receipt = {
            "file_name": file_name,
            "download_url": download_url,
            "generated_at": generated_at.isoformat(),
            "invoice_no": latest_invoice.invoice_no,
            "payment_id": latest_tx.id,
        }

        metadata = dict(latest_tx.metadata_json or {})
        metadata["receipt"] = receipt
        latest_tx.metadata_json = metadata
        latest_tx.receipt_generated = True
        return receipt

    async def _ensure_latest_fee_receipt(self, *, student_id: str, regenerate: bool = False) -> tuple[dict, bool, dict]:
        context = await self._load_fee_receipt_context(student_id=student_id)
        if not context["is_fully_paid"]:
            raise ForbiddenException("Receipt is available only after full fee payment")

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
                "is_fully_paid": is_fully_paid,
            },
            "payments": payments,
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
                    func.coalesce(
                        func.sum(case((PaymentTransaction.status == "success", 1), else_=0)),
                        0,
                    ).label("installments_paid_count"),
                ).where(PaymentTransaction.student_id == student_id)
            )
        ).mappings().one()

        current_paid_amount = float(rollup_row["paid_amount"] or 0)
        installments_paid_count = int(rollup_row["installments_paid_count"] or 0)

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

        installment_no = installments_paid_count + 1
        paid_at = datetime(
            year=payload.paid_on.year,
            month=payload.paid_on.month,
            day=payload.paid_on.day,
            tzinfo=UTC,
        )
        invoice_no = self._build_fee_invoice_no(student_id)

        invoice = FeeInvoice(
            student_id=student_id,
            student_fee_account_id=assignment.id,
            installment_no=installment_no,
            invoice_no=invoice_no,
            period_label=payload.period_label.strip() if payload.period_label else f"Installment {installment_no}",
            due_date=payload.paid_on,
            amount=payment_amount,
            balance_amount=max(current_pending_amount - payment_amount, 0),
            status="paid",
            paid_at=paid_at,
            reminder_enabled=False,
            next_installment_date=None,
        )
        self.session.add(invoice)
        await self.session.flush()

        transaction = PaymentTransaction(
            invoice_id=invoice.id,
            student_id=student_id,
            student_fee_account_id=assignment.id,
            provider="admin_manual",
            payment_mode=payload.payment_mode,
            external_ref=payload.reference_no,
            amount=payment_amount,
            status="success",
            paid_at=paid_at,
            note=payload.note,
            receipt_generated=False,
            metadata_json={
                "source": "admin_fee_update",
                "actor_user_id": actor_user_id,
            },
        )
        self.session.add(transaction)
        await self.session.flush()

        updated_paid, updated_pending, is_fully_paid = self._compute_fee_progress(
            fee_amount=fee_amount,
            paid_amount=current_paid_amount + payment_amount,
        )

        receipt = None
        if is_fully_paid:
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
                "invoice_id": invoice.id,
                "invoice_no": invoice.invoice_no,
                "installment_no": installment_no,
                "payment_mode": transaction.payment_mode,
                "reference_no": transaction.external_ref,
                "payment_amount": payment_amount,
                "paid_amount": updated_paid,
                "pending_amount": updated_pending,
                "is_fully_paid": is_fully_paid,
                "receipt_file": receipt["file_name"] if receipt else None,
            },
            ip_address=ip_address,
        )

        await self.session.commit()
        await self.session.refresh(transaction)
        await self.session.refresh(invoice)

        return {
            "student_id": student_id,
            "payment": {
                "payment_id": transaction.id,
                "invoice_id": invoice.id,
                "invoice_no": invoice.invoice_no,
                "installment_no": invoice.installment_no,
                "period_label": invoice.period_label,
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
                "installments_paid_count": installment_no,
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

        return {
            "total_students": total_students,
            "paid_students": paid_students,
            "pending_students": pending_students,
            "students_without_fee": max(total_students - assigned_students, 0),
            "total_invoiced_amount": total_fee_amount,
            "total_paid_amount": total_paid_amount,
            "total_pending_amount": total_pending_amount,
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
            installments_paid_count = int(installments_paid_count_raw or 0)
            installment_target_count = int(fee_structure_installment_count) if fee_structure_installment_count else None

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
                "next_due_date": None,
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
