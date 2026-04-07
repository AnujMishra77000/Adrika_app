import json
from datetime import UTC, date, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.security import get_password_hash
from app.db.models.academic import Batch, Branch, Standard, StudentBatchEnrollment, StudentProfile, Subject, TeacherProfile
from app.db.models.billing import FeeInvoice, PaymentTransaction
from app.db.models.parent import ParentProfile, ParentStudentLink
from app.db.models.assessment import Assessment, AssessmentAssignment
from app.db.models.attendance import AttendanceCorrection, AttendanceRecord
from app.db.models.audit import AuditLog
from app.db.models.content import Banner, DailyThought, Notice, NoticeTarget
from app.db.models.doubt import Doubt
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
    AdminHomeworkCreateDTO,
    AdminNoticeCreateDTO,
    AdminNotificationCreateDTO,
    AdminResultPublishDTO,
    AdminStudentCreateDTO,
    AdminStudentUpdateDTO,
    AdminParentLinkCreateDTO,
    AdminFeeInvoiceCreateDTO,
    AdminPaymentReconcileDTO,
)


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _audit(
        self,
        *,
        actor_user_id: str,
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
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = (
            select(StudentProfile, User, Batch)
            .join(User, User.id == StudentProfile.user_id)
            .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
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
                "batch": {
                    "id": batch.id,
                    "name": batch.name,
                    "academic_year": batch.academic_year,
                }
                if batch
                else None,
                "created_at": user.created_at,
            }
            for profile, user, batch in rows
        ]
        return items, total

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
        stmt = (
            select(Doubt, StudentProfile, User)
            .join(StudentProfile, StudentProfile.id == Doubt.student_id)
            .join(User, User.id == StudentProfile.user_id)
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
                "student_name": user.full_name,
                "subject_id": doubt.subject_id,
                "topic": doubt.topic,
                "status": doubt.status.value if hasattr(doubt.status, "value") else str(doubt.status),
                "priority": doubt.priority,
                "created_at": doubt.created_at,
            }
            for doubt, _, user in rows
        ], total

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

            elif target_type == "batch":
                rows = (
                    await self.session.execute(
                        select(StudentProfile.user_id).where(StudentProfile.current_batch_id == target_id)
                    )
                ).all()
                user_ids.update([row[0] for row in rows])

            elif target_type == "student":
                student = await self.session.get(StudentProfile, target_id)
                if student:
                    user_ids.add(student.user_id)

            elif target_type == "teacher":
                teacher = await self.session.get(TeacherProfile, target_id)
                if teacher:
                    user_ids.add(teacher.user_id)

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
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = select(Subject)
        if search:
            query = query.where(or_(Subject.name.ilike(f"%{search}%"), Subject.code.ilike(f"%{search}%")))

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(Subject.name.asc(), Subject.code.asc()).limit(limit).offset(offset)
            )
        ).scalars().all()

        return [
            {
                "id": row.id,
                "code": row.code,
                "name": row.name,
            }
            for row in rows
        ], total

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

    async def list_results(
        self,
        *,
        assessment_id: str | None,
        batch_id: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = (
            select(Result, Assessment, StudentProfile, User)
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
                "id": row.id,
                "assessment": {
                    "id": assessment.id,
                    "title": assessment.title,
                },
                "student": {
                    "id": profile.id,
                    "name": user.full_name,
                    "admission_no": profile.admission_no,
                    "roll_no": profile.roll_no,
                    "batch_id": profile.current_batch_id,
                },
                "score": float(row.score),
                "total_marks": float(row.total_marks),
                "rank": row.rank,
                "published_at": row.published_at,
            }
            for row, assessment, profile, user in rows
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

    async def list_fee_invoices_admin(
        self,
        *,
        student_id: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = (
            select(FeeInvoice, StudentProfile, User)
            .join(StudentProfile, StudentProfile.id == FeeInvoice.student_id)
            .join(User, User.id == StudentProfile.user_id)
        )

        filters = []
        if student_id:
            filters.append(FeeInvoice.student_id == student_id)
        if status:
            filters.append(FeeInvoice.status == status)
        if filters:
            query = query.where(and_(*filters))

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(FeeInvoice.due_date.desc()).limit(limit).offset(offset)
            )
        ).all()

        return [
            {
                "id": invoice.id,
                "student_id": student.id,
                "student_name": user.full_name,
                "invoice_no": invoice.invoice_no,
                "period_label": invoice.period_label,
                "due_date": invoice.due_date,
                "amount": float(invoice.amount),
                "status": invoice.status,
                "paid_at": invoice.paid_at,
                "created_at": invoice.created_at,
            }
            for invoice, student, user in rows
        ], total

    async def create_fee_invoice(
        self,
        *,
        payload: AdminFeeInvoiceCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        student = await self.session.get(StudentProfile, payload.student_id)
        if not student:
            raise NotFoundException("Student profile not found")

        existing = (
            await self.session.execute(select(FeeInvoice).where(FeeInvoice.invoice_no == payload.invoice_no))
        ).scalar_one_or_none()
        if existing:
            raise ForbiddenException("Invoice number already exists")

        invoice = FeeInvoice(
            student_id=payload.student_id,
            invoice_no=payload.invoice_no,
            period_label=payload.period_label,
            due_date=payload.due_date,
            amount=payload.amount,
            status=payload.status,
            paid_at=datetime.now(UTC) if payload.status == "paid" else None,
        )
        self.session.add(invoice)
        await self.session.flush()

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.fee_invoice.create",
            entity_type="fee_invoice",
            entity_id=invoice.id,
            before_state=None,
            after_state={
                "student_id": invoice.student_id,
                "invoice_no": invoice.invoice_no,
                "period_label": invoice.period_label,
                "due_date": invoice.due_date,
                "amount": float(invoice.amount),
                "status": invoice.status,
            },
            ip_address=ip_address,
        )

        await self.session.commit()
        await self.session.refresh(invoice)

        return {
            "id": invoice.id,
            "student_id": invoice.student_id,
            "invoice_no": invoice.invoice_no,
            "period_label": invoice.period_label,
            "due_date": invoice.due_date,
            "amount": float(invoice.amount),
            "status": invoice.status,
            "paid_at": invoice.paid_at,
        }

    async def list_payments_admin(
        self,
        *,
        student_id: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = (
            select(PaymentTransaction, FeeInvoice, StudentProfile, User)
            .join(FeeInvoice, FeeInvoice.id == PaymentTransaction.invoice_id)
            .join(StudentProfile, StudentProfile.id == PaymentTransaction.student_id)
            .join(User, User.id == StudentProfile.user_id)
        )

        filters = []
        if student_id:
            filters.append(PaymentTransaction.student_id == student_id)
        if status:
            filters.append(PaymentTransaction.status == status)
        if filters:
            query = query.where(and_(*filters))

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(PaymentTransaction.created_at.desc()).limit(limit).offset(offset)
            )
        ).all()

        return [
            {
                "id": payment.id,
                "invoice_id": payment.invoice_id,
                "invoice_no": invoice.invoice_no,
                "student_id": student.id,
                "student_name": user.full_name,
                "provider": payment.provider,
                "external_ref": payment.external_ref,
                "amount": float(payment.amount),
                "status": payment.status,
                "paid_at": payment.paid_at,
                "created_at": payment.created_at,
            }
            for payment, invoice, student, user in rows
        ], total

    async def reconcile_payment(
        self,
        *,
        payment_id: str,
        payload: AdminPaymentReconcileDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        payment = await self.session.get(PaymentTransaction, payment_id)
        if not payment:
            raise NotFoundException("Payment transaction not found")

        invoice = await self.session.get(FeeInvoice, payment.invoice_id)
        if not invoice:
            raise NotFoundException("Linked invoice not found")

        before = {
            "payment_status": payment.status,
            "payment_paid_at": payment.paid_at,
            "external_ref": payment.external_ref,
            "invoice_status": invoice.status,
            "invoice_paid_at": invoice.paid_at,
        }

        payment.status = payload.status
        if payload.paid_at is not None:
            payment.paid_at = payload.paid_at
        if payload.external_ref is not None:
            payment.external_ref = payload.external_ref

        metadata_json = dict(payment.metadata_json or {})
        if payload.note:
            metadata_json["admin_note"] = payload.note
        metadata_json["reconciled_at"] = datetime.now(UTC).isoformat()
        payment.metadata_json = metadata_json

        if payload.status == "success":
            effective_paid_at = payment.paid_at or datetime.now(UTC)
            payment.paid_at = effective_paid_at
            invoice.status = "paid"
            invoice.paid_at = effective_paid_at
        elif payload.status == "refunded":
            invoice.status = "pending"
            invoice.paid_at = None
        elif payload.status in {"failed", "pending"}:
            if invoice.status != "paid":
                invoice.status = "pending"

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.payment.reconcile",
            entity_type="payment_transaction",
            entity_id=payment.id,
            before_state=before,
            after_state={
                "payment_status": payment.status,
                "payment_paid_at": payment.paid_at,
                "external_ref": payment.external_ref,
                "invoice_status": invoice.status,
                "invoice_paid_at": invoice.paid_at,
            },
            ip_address=ip_address,
        )

        await self.session.commit()
        await self.session.refresh(payment)
        await self.session.refresh(invoice)

        return {
            "id": payment.id,
            "invoice_id": payment.invoice_id,
            "status": payment.status,
            "paid_at": payment.paid_at,
            "external_ref": payment.external_ref,
            "invoice_status": invoice.status,
            "invoice_paid_at": invoice.paid_at,
            "updated_at": payment.updated_at,
        }
