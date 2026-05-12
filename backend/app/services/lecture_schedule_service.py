from __future__ import annotations

import re
from uuid import uuid4
from datetime import UTC, date, datetime

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.admin import AdminTeacherCreateDTO
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.security import get_password_hash
from app.db.models.academic import (
    Batch,
    CompletedLecture,
    LectureSchedule,
    LectureScheduleStudent,
    Standard,
    StudentProfile,
    Subject,
    SubjectAcademicScope,
    TeacherBatchAssignment,
    TeacherProfile,
    TeacherSalaryLedger,
    TeacherSalaryProfile,
)
from app.db.models.audit import AuditLog
from app.db.models.enums import LectureScheduleStatus, RoleCode, UserStatus
from app.db.models.user import DeviceRegistration, RefreshSession, Role, TeacherCredential, User, UserRole


class LectureScheduleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _extract_class_level(class_name: str | None, standard_name: str | None = None) -> int | None:
        source = f"{class_name or ''} {standard_name or ''}".lower()
        match = re.search(r"(6|7|8|9|10|11|12)", source)
        if not match:
            return None
        value = int(match.group(1))
        if value in {6, 7, 8, 9, 10, 11, 12}:
            return value
        return None

    @staticmethod
    def _extract_stream(
        stream: str | None,
        class_name: str | None = None,
        standard_name: str | None = None,
    ) -> str | None:
        value = (stream or "").strip().lower()
        if value in {"science", "sci"}:
            return "science"
        if value in {"commerce", "comm"}:
            return "commerce"

        source = f"{class_name or ''} {standard_name or ''}".lower()
        if "science" in source:
            return "science"
        if "commerce" in source:
            return "commerce"
        return None

    
    @staticmethod
    def _normalize_stream(class_level: int, stream: str | None) -> str:
        if class_level <= 10:
            return "common"

        value = (stream or "").strip().lower()
        if value in {"science", "sci"}:
            return "science"
        if value in {"commerce", "comm"}:
            return "commerce"
        raise ValueError("stream is required for class 11 and 12")


    @staticmethod
    def _scope_token(class_level: int, stream: str | None) -> str:
        normalized_stream = "common" if class_level <= 10 else (stream or "science").strip().lower()
        return f"{class_level}-{normalized_stream}"

    @classmethod
    def _normalize_teaching_scopes(cls, scopes: list[str]) -> list[str]:
        normalized: list[str] = []
        for raw in scopes:
            token = (raw or "").strip().lower()
            if not token:
                continue
            match = re.match(r"^(6|7|8|9|10)-common$", token)
            senior_match = re.match(r"^(11|12)-(science|commerce)$", token)
            if match or senior_match:
                if token not in normalized:
                    normalized.append(token)
        if not normalized:
            raise ValueError("at least one valid teaching scope is required")
        return normalized

    @staticmethod
    def _is_valid_login_password(value: str) -> bool:
        if len(value) < 6 or len(value) > 8:
            return False
        has_alpha = any(ch.isalpha() for ch in value)
        has_digit = any(ch.isdigit() for ch in value)
        return has_alpha and has_digit

    @staticmethod
    def _generate_login_password() -> str:
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits
        while True:
            candidate = "".join(secrets.choice(alphabet) for _ in range(8))
            if any(ch.isalpha() for ch in candidate) and any(ch.isdigit() for ch in candidate):
                return candidate

    async def _upsert_teacher_credential_snapshot(
        self,
        *,
        user_id: str,
        login_id: str,
        password_plain: str,
        actor_user_id: str | None,
    ) -> None:
        existing = (
            await self.session.execute(
                select(TeacherCredential).where(TeacherCredential.user_id == user_id)
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
            TeacherCredential(
                user_id=user_id,
                login_id=login_id,
                password_plain=password_plain,
                password_updated_at=now,
                updated_by_user_id=actor_user_id,
            )
        )

    async def _upsert_teacher_salary_profile(self, *, teacher_id: str, hourly_rate: float) -> TeacherSalaryProfile:
        existing = (
            await self.session.execute(
                select(TeacherSalaryProfile).where(TeacherSalaryProfile.teacher_id == teacher_id)
            )
        ).scalar_one_or_none()
        if existing:
            existing.hourly_rate = float(hourly_rate or 0)
            existing.is_active = True
            return existing

        profile = TeacherSalaryProfile(
            teacher_id=teacher_id,
            hourly_rate=float(hourly_rate or 0),
            currency="INR",
            is_active=True,
        )
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def _record_teacher_salary_for_schedule(
        self,
        *,
        schedule: LectureSchedule,
        completed_lecture_id: str | None,
    ) -> dict | None:
        existing = (
            await self.session.execute(
                select(TeacherSalaryLedger).where(TeacherSalaryLedger.schedule_id == schedule.id)
            )
        ).scalar_one_or_none()
        if existing:
            return None

        salary_profile = (
            await self.session.execute(
                select(TeacherSalaryProfile).where(TeacherSalaryProfile.teacher_id == schedule.teacher_id)
            )
        ).scalar_one_or_none()
        hourly_rate = float(salary_profile.hourly_rate) if salary_profile else 0.0
        minutes = int(schedule.duration_minutes or 60)
        amount = round((hourly_rate * minutes) / 60, 2)
        completed_at = schedule.completed_at or datetime.now(UTC)

        ledger = TeacherSalaryLedger(
            teacher_id=schedule.teacher_id,
            schedule_id=schedule.id,
            completed_lecture_id=completed_lecture_id,
            class_level=int(schedule.class_level),
            stream=(schedule.stream or "common"),
            subject_id=schedule.subject_id,
            topic=schedule.topic,
            lecture_duration_minutes=minutes,
            hourly_rate=hourly_rate,
            amount=amount,
            attendance_date=completed_at.date(),
            completed_at=completed_at,
        )
        self.session.add(ledger)
        await self.session.flush()
        return {"ledger_id": ledger.id, "amount": amount}


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
                before_state=str(before_state) if before_state is not None else None,
                after_state=str(after_state) if after_state is not None else None,
                ip_address=ip_address,
                created_at=datetime.now(UTC),
            )
        )

    async def list_admin_teachers(
        self,
        *,
        search: str | None,
        class_level: int | None,
        stream: str | None,
        subject_id: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        assignment_filters = []
        if subject_id:
            assignment_filters.append(TeacherBatchAssignment.subject_id == subject_id)
        if class_level is not None:
            assignment_filters.append(Standard.name.ilike(f"%{class_level}%"))
        if stream and class_level not in {None, 10, 9, 8, 7, 6}:
            assignment_filters.append(Standard.name.ilike(f"%{stream}%"))

        query = (
            select(
                TeacherProfile,
                User,
                TeacherSalaryProfile,
                TeacherCredential,
                func.count(func.distinct(TeacherBatchAssignment.id)).label("assignment_count"),
            )
            .join(User, User.id == TeacherProfile.user_id)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .outerjoin(TeacherBatchAssignment, TeacherBatchAssignment.teacher_id == TeacherProfile.id)
            .outerjoin(Batch, Batch.id == TeacherBatchAssignment.batch_id)
            .outerjoin(Standard, Standard.id == Batch.standard_id)
            .outerjoin(TeacherSalaryProfile, TeacherSalaryProfile.teacher_id == TeacherProfile.id)
            .outerjoin(TeacherCredential, TeacherCredential.user_id == User.id)
            .where(Role.code == RoleCode.TEACHER)
        )

        if assignment_filters:
            query = query.where(and_(*assignment_filters))

        if search:
            query = query.where(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.phone.ilike(f"%{search}%"),
                    TeacherProfile.employee_code.ilike(f"%{search}%"),
                )
            )

        if class_level is not None:
            if class_level <= 10:
                token = f"{class_level}-common"
                query = query.where(
                    or_(
                        Standard.name.ilike(f"%{class_level}%"),
                        TeacherProfile.teaching_scope.ilike(f"%{token}%"),
                    )
                )
            else:
                base = [
                    Standard.name.ilike(f"%{class_level}%"),
                    TeacherProfile.teaching_scope.ilike(f"%{class_level}-%"),
                ]
                if stream:
                    token = f"{class_level}-{stream.strip().lower()}"
                    base = [
                        and_(Standard.name.ilike(f"%{class_level}%"), Standard.name.ilike(f"%{stream}%")),
                        TeacherProfile.teaching_scope.ilike(f"%{token}%"),
                    ]
                query = query.where(or_(*base))

        if stream and class_level is None:
            query = query.where(TeacherProfile.teaching_scope.ilike(f"%{stream.strip().lower()}%"))

        if status:
            query = query.where(User.status == UserStatus(status))

        query = query.group_by(TeacherProfile.id, User.id, TeacherSalaryProfile.id, TeacherCredential.id)

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(User.full_name.asc()).limit(limit).offset(offset)
            )
        ).all()

        items = [
            {
                "teacher_id": profile.id,
                "user_id": user.id,
                "full_name": user.full_name,
                "phone": user.phone,
                "designation": profile.designation,
                "employee_code": profile.employee_code,
                "qualification": profile.qualification,
                "specialization": profile.specialization,
                "gender": profile.gender,
                "age": profile.age,
                "school_college": profile.school_college,
                "teaching_scope": profile.teaching_scope,
                "status": user.status.value if hasattr(user.status, "value") else str(user.status),
                "created_at": user.created_at,
                "assignment_count": int(assignment_count or 0),
                "hourly_salary_rate": float(salary_profile.hourly_rate) if salary_profile else 0.0,
                "login_id": user.phone,
                "current_password": credential.password_plain if credential else None,
                "password_last_updated_at": credential.password_updated_at if credential else None,
            }
            for profile, user, salary_profile, credential, assignment_count in rows
        ]
        return items, total

    async def create_admin_teacher(
        self,
        *,
        payload: AdminTeacherCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        normalized_phone = "".join(ch for ch in payload.phone if ch.isdigit())
        existing_user = (
            await self.session.execute(
                select(User).where(User.phone == normalized_phone)
            )
        ).scalar_one_or_none()
        if existing_user:
            raise ValueError("A user with this contact number already exists")

        if payload.email:
            existing_email = (
                await self.session.execute(select(User).where(User.email == str(payload.email).strip().lower()))
            ).scalar_one_or_none()
            if existing_email:
                raise ValueError("A user with this email already exists")

        teacher_role = (
            await self.session.execute(
                select(Role).where(Role.code == RoleCode.TEACHER)
            )
        ).scalar_one_or_none()
        if not teacher_role:
            raise NotFoundException("Teacher role is not configured")

        password_value = (payload.password or "").strip()
        generated_password = None
        if not password_value:
            generated_password = self._generate_login_password()
            password_value = generated_password
        if not self._is_valid_login_password(password_value):
            raise ValueError("Password must be 6-8 characters and include both letters and numbers")

        scopes = self._normalize_teaching_scopes(payload.teaching_scopes)
        employee_code = (payload.employee_code or "").strip()
        if not employee_code:
            employee_code = f"TCHR-{uuid4().hex[:6].upper()}"

        existing_code = (
            await self.session.execute(
                select(TeacherProfile.id).where(TeacherProfile.employee_code == employee_code)
            )
        ).scalar_one_or_none()
        if existing_code:
            raise ValueError("Employee code already exists")

        user = User(
            full_name=payload.full_name.strip(),
            phone=normalized_phone,
            email=str(payload.email).strip().lower() if payload.email else None,
            password_hash=get_password_hash(password_value),
            status=UserStatus.ACTIVE,
        )
        self.session.add(user)
        await self.session.flush()

        self.session.add(UserRole(user_id=user.id, role_id=teacher_role.id))

        profile = TeacherProfile(
            user_id=user.id,
            employee_code=employee_code,
            designation=(payload.designation or "Teacher").strip(),
            age=payload.age,
            gender=(payload.gender or "").strip() or None,
            qualification=(payload.qualification or "").strip() or None,
            specialization=(payload.specialization or "").strip() or None,
            school_college=(payload.school_college or "").strip() or None,
            teaching_scope=",".join(scopes),
            address=(payload.address or "").strip() or None,
            photo_url=None,
        )
        self.session.add(profile)
        await self.session.flush()

        await self._upsert_teacher_credential_snapshot(
            user_id=user.id,
            login_id=normalized_phone,
            password_plain=password_value,
            actor_user_id=actor_user_id,
        )
        await self._upsert_teacher_salary_profile(
            teacher_id=profile.id,
            hourly_rate=float(payload.hourly_salary_rate or 0),
        )

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.teacher.create",
            entity_type="teacher_profile",
            entity_id=profile.id,
            before_state=None,
            after_state={
                "teacher_id": profile.id,
                "user_id": user.id,
                "employee_code": employee_code,
                "teaching_scope": profile.teaching_scope,
                "hourly_salary_rate": float(payload.hourly_salary_rate or 0),
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "teacher_id": profile.id,
            "user_id": user.id,
            "full_name": user.full_name,
            "login_id": normalized_phone,
            "employee_code": profile.employee_code,
            "status": user.status.value,
            "teaching_scope": profile.teaching_scope,
            "hourly_salary_rate": float(payload.hourly_salary_rate or 0),
            "generated_password": generated_password,
            "issued_password": password_value,
        }

    async def list_teacher_credentials(
        self,
        *,
        search: str | None,
        class_level: int | None,
        stream: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = (
            select(TeacherProfile, User, TeacherCredential, TeacherSalaryProfile)
            .join(User, User.id == TeacherProfile.user_id)
            .outerjoin(TeacherCredential, TeacherCredential.user_id == User.id)
            .outerjoin(TeacherSalaryProfile, TeacherSalaryProfile.teacher_id == TeacherProfile.id)
        )

        filters = []
        if search:
            filters.append(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.phone.ilike(f"%{search}%"),
                    TeacherProfile.employee_code.ilike(f"%{search}%"),
                )
            )
        if status:
            filters.append(User.status == UserStatus(status))
        if class_level is not None:
            if class_level <= 10:
                filters.append(TeacherProfile.teaching_scope.ilike(f"%{class_level}-common%"))
            else:
                if stream:
                    filters.append(TeacherProfile.teaching_scope.ilike(f"%{class_level}-{stream.strip().lower()}%"))
                else:
                    filters.append(TeacherProfile.teaching_scope.ilike(f"%{class_level}-%"))
        elif stream:
            filters.append(TeacherProfile.teaching_scope.ilike(f"%{stream.strip().lower()}%"))

        if filters:
            query = query.where(and_(*filters))

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (await self.session.execute(query.order_by(User.created_at.desc()).limit(limit).offset(offset))).all()

        items = [
            {
                "teacher_id": profile.id,
                "user_id": user.id,
                "full_name": user.full_name,
                "employee_code": profile.employee_code,
                "login_id": user.phone,
                "status": user.status.value if hasattr(user.status, "value") else str(user.status),
                "teaching_scope": profile.teaching_scope,
                "hourly_salary_rate": float(salary.hourly_rate) if salary else 0.0,
                "current_password": credential.password_plain if credential else None,
                "password_last_updated_at": credential.password_updated_at if credential else None,
                "created_at": user.created_at,
            }
            for profile, user, credential, salary in rows
        ]
        return items, total

    async def reset_teacher_credentials(
        self,
        *,
        teacher_id: str,
        new_password: str | None,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        profile = await self.session.get(TeacherProfile, teacher_id)
        if not profile:
            raise NotFoundException("Teacher profile not found")

        user = await self.session.get(User, profile.user_id)
        if not user:
            raise NotFoundException("Teacher user account not found")

        login_id = (user.phone or "").strip()
        if not login_id:
            raise ForbiddenException("Teacher login ID is missing. Please set a primary contact number first.")

        generated = False
        password_value = (new_password or "").strip()
        if not password_value:
            password_value = self._generate_login_password()
            generated = True

        if not self._is_valid_login_password(password_value):
            raise ValueError("Password must be 6-8 characters and include both letters and numbers")

        user.password_hash = get_password_hash(password_value)
        await self._upsert_teacher_credential_snapshot(
            user_id=user.id,
            login_id=login_id,
            password_plain=password_value,
            actor_user_id=actor_user_id,
        )
        await self.session.execute(
            delete(RefreshSession).where(RefreshSession.user_id == user.id)
        )

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.teacher.credentials.reset",
            entity_type="teacher_profile",
            entity_id=profile.id,
            before_state={"login_id": login_id},
            after_state={"login_id": login_id, "password_reset": True, "generated": generated},
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "teacher_id": profile.id,
            "user_id": user.id,
            "login_id": login_id,
            "temporary_password": password_value,
            "generated": generated,
        }

    async def update_admin_teacher_status(
        self,
        *,
        teacher_id: str,
        status: str,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        profile = await self.session.get(TeacherProfile, teacher_id)
        if not profile:
            raise NotFoundException("Teacher profile not found")

        user = await self.session.get(User, profile.user_id)
        if not user:
            raise NotFoundException("Teacher user not found")

        next_status = UserStatus(status)
        before = {"status": user.status.value if hasattr(user.status, "value") else str(user.status)}
        user.status = next_status

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.teacher.status.update",
            entity_type="teacher_profile",
            entity_id=profile.id,
            before_state=before,
            after_state={"status": user.status.value},
            ip_address=ip_address,
        )

        await self.session.commit()
        return {
            "teacher_id": profile.id,
            "user_id": user.id,
            "status": user.status.value,
        }

    async def list_teacher_salary_ledger(
        self,
        *,
        teacher_id: str | None,
        class_level: int | None,
        stream: str | None,
        from_date: date | None,
        to_date: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int, dict]:
        query = (
            select(TeacherSalaryLedger, TeacherProfile, User)
            .join(TeacherProfile, TeacherProfile.id == TeacherSalaryLedger.teacher_id)
            .join(User, User.id == TeacherProfile.user_id)
        )

        filters = []
        if teacher_id:
            filters.append(TeacherSalaryLedger.teacher_id == teacher_id)
        if class_level is not None:
            filters.append(TeacherSalaryLedger.class_level == class_level)
        if stream:
            filters.append(TeacherSalaryLedger.stream == stream.strip().lower())
        if from_date:
            filters.append(TeacherSalaryLedger.attendance_date >= from_date)
        if to_date:
            filters.append(TeacherSalaryLedger.attendance_date <= to_date)
        if filters:
            query = query.where(and_(*filters))

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(TeacherSalaryLedger.attendance_date.desc(), TeacherSalaryLedger.created_at.desc()).limit(limit).offset(offset)
            )
        ).all()

        summary_row = (
            await self.session.execute(
                select(
                    func.coalesce(func.sum(TeacherSalaryLedger.amount), 0),
                    func.count(TeacherSalaryLedger.id),
                    func.count(func.distinct(TeacherSalaryLedger.teacher_id)),
                ).where(*filters) if filters else select(
                    func.coalesce(func.sum(TeacherSalaryLedger.amount), 0),
                    func.count(TeacherSalaryLedger.id),
                    func.count(func.distinct(TeacherSalaryLedger.teacher_id)),
                )
            )
        ).first()

        total_amount = float(summary_row[0] or 0) if summary_row else 0.0
        lecture_count = int(summary_row[1] or 0) if summary_row else 0
        teacher_count = int(summary_row[2] or 0) if summary_row else 0

        items = [
            {
                "ledger_id": ledger.id,
                "teacher_id": profile.id,
                "teacher_name": user.full_name,
                "employee_code": profile.employee_code,
                "class_level": ledger.class_level,
                "stream": ledger.stream,
                "topic": ledger.topic,
                "lecture_duration_minutes": ledger.lecture_duration_minutes,
                "hourly_rate": float(ledger.hourly_rate or 0),
                "amount": float(ledger.amount or 0),
                "attendance_date": ledger.attendance_date.isoformat() if ledger.attendance_date else None,
                "completed_at": ledger.completed_at,
            }
            for ledger, profile, user in rows
        ]

        summary = {
            "total_amount": round(total_amount, 2),
            "lecture_count": lecture_count,
            "teacher_count": teacher_count,
        }
        return items, total, summary

    async def get_teacher_salary_slip(
        self,
        *,
        teacher_id: str,
        from_date: date | None,
        to_date: date | None,
    ) -> dict:
        profile = await self.session.get(TeacherProfile, teacher_id)
        if not profile:
            raise NotFoundException("Teacher profile not found")
        user = await self.session.get(User, profile.user_id)
        if not user:
            raise NotFoundException("Teacher user not found")

        items, total, summary = await self.list_teacher_salary_ledger(
            teacher_id=teacher_id,
            class_level=None,
            stream=None,
            from_date=from_date,
            to_date=to_date,
            limit=500,
            offset=0,
        )

        return {
            "teacher": {
                "teacher_id": profile.id,
                "full_name": user.full_name,
                "employee_code": profile.employee_code,
                "phone": user.phone,
                "status": user.status.value if hasattr(user.status, "value") else str(user.status),
                "teaching_scope": profile.teaching_scope,
            },
            "period": {
                "from_date": from_date.isoformat() if from_date else None,
                "to_date": to_date.isoformat() if to_date else None,
            },
            "summary": summary,
            "entries_count": total,
            "entries": items,
        }

    async def delete_admin_teacher(
        self,
        *,
        teacher_id: str,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        teacher = await self.session.get(TeacherProfile, teacher_id)
        if not teacher:
            raise NotFoundException("Teacher not found")

        user = await self.session.get(User, teacher.user_id)
        if not user:
            raise NotFoundException("Teacher user not found")

        teacher_role_id = (
            await self.session.execute(
                select(Role.id).where(Role.code == RoleCode.TEACHER)
            )
        ).scalar_one_or_none()

        before_state = {
            "user_status": user.status.value if hasattr(user.status, "value") else str(user.status),
            "phone": user.phone,
            "email": user.email,
        }

        if teacher_role_id:
            await self.session.execute(
                delete(UserRole).where(
                    UserRole.user_id == user.id,
                    UserRole.role_id == teacher_role_id,
                )
            )

        await self.session.execute(
            delete(RefreshSession).where(RefreshSession.user_id == user.id)
        )
        await self.session.execute(
            delete(DeviceRegistration).where(DeviceRegistration.user_id == user.id)
        )

        remaining_roles = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(UserRole).where(UserRole.user_id == user.id)
                )
            ).scalar_one()
            or 0
        )

        login_blocked = remaining_roles == 0
        if login_blocked:
            user.status = UserStatus.INACTIVE
            user.phone = None
            user.email = None
            user.password_hash = get_password_hash(f"deleted-{uuid4().hex}")

        teacher.designation = "Account Deleted"

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.teacher.delete",
            entity_type="teacher_profile",
            entity_id=teacher.id,
            before_state=before_state,
            after_state={
                "user_status": user.status.value if hasattr(user.status, "value") else str(user.status),
                "phone": user.phone,
                "email": user.email,
                "remaining_roles": remaining_roles,
                "login_blocked": login_blocked,
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "deleted": True,
            "teacher_id": teacher.id,
            "user_id": user.id,
            "remaining_roles": remaining_roles,
            "login_blocked": login_blocked,
            "status": user.status.value if hasattr(user.status, "value") else str(user.status),
        }

    async def _validate_subject_scope(
        self,
        *,
        subject_id: str,
        class_level: int,
        stream: str,
    ) -> None:
        scope = (
            await self.session.execute(
                select(SubjectAcademicScope.id).where(
                    SubjectAcademicScope.subject_id == subject_id,
                    SubjectAcademicScope.class_level == class_level,
                    SubjectAcademicScope.stream == stream,
                )
            )
        ).scalar_one_or_none()

        if not scope:
            raise ValueError("Subject is not configured for selected class/stream")

    @staticmethod
    def _canonicalize_teaching_scope_token(token: str) -> str | None:
        value = token.strip().lower().replace("_", "-").replace(" ", "")
        mapping = {
            "6": "6-common",
            "6th": "6-common",
            "6common": "6-common",
            "6-common": "6-common",
            "7": "7-common",
            "7th": "7-common",
            "7common": "7-common",
            "7-common": "7-common",
            "8": "8-common",
            "8th": "8-common",
            "8common": "8-common",
            "8-common": "8-common",
            "9": "9-common",
            "9th": "9-common",
            "9common": "9-common",
            "9-common": "9-common",
            "10": "10-common",
            "10th": "10-common",
            "10common": "10-common",
            "10-common": "10-common",
            "11science": "11-science",
            "11-science": "11-science",
            "11sci": "11-science",
            "11commerce": "11-commerce",
            "11-commerce": "11-commerce",
            "11comm": "11-commerce",
            "12science": "12-science",
            "12-science": "12-science",
            "12sci": "12-science",
            "12commerce": "12-commerce",
            "12-commerce": "12-commerce",
            "12comm": "12-commerce",
        }
        return mapping.get(value)

    @classmethod
    def _parse_teaching_scopes(cls, teaching_scope: str | None) -> set[str]:
        if not teaching_scope:
            return set()

        scopes: set[str] = set()
        for token in re.split(r"[,|/;]+", teaching_scope):
            normalized = cls._canonicalize_teaching_scope_token(token)
            if normalized:
                scopes.add(normalized)
        return scopes

    @staticmethod
    def _target_scope(class_level: int, stream: str) -> str:
        if class_level <= 10:
            return f"{class_level}-common"
        return f"{class_level}-{stream}"

    async def _validate_teacher_scope(
        self,
        *,
        teacher: TeacherProfile,
        class_level: int,
        stream: str,
    ) -> None:
        allowed_scopes = self._parse_teaching_scopes(teacher.teaching_scope)
        if not allowed_scopes:
            return

        target_scope = self._target_scope(class_level, stream)
        if target_scope in allowed_scopes:
            return

        pretty = ", ".join(sorted(allowed_scopes))
        raise ValueError(
            f"Selected teacher is not registered for this class/stream. Allowed scope: {pretty}"
        )

    async def create_admin_schedule(
        self,
        *,
        payload,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        class_level = int(payload.class_level)
        stream = self._normalize_stream(class_level, payload.stream)

        subject = await self.session.get(Subject, payload.subject_id)
        if not subject:
            raise NotFoundException("Subject not found")

        teacher = await self.session.get(TeacherProfile, payload.teacher_id)
        if not teacher:
            raise NotFoundException("Teacher not found")

        teacher_user = await self.session.get(User, teacher.user_id)
        if not teacher_user or teacher_user.status != UserStatus.ACTIVE:
            raise ValueError("Teacher account is inactive")

        await self._validate_subject_scope(
            subject_id=payload.subject_id,
            class_level=class_level,
            stream=stream,
        )
        await self._validate_teacher_scope(
            teacher=teacher,
            class_level=class_level,
            stream=stream,
        )

        schedule = LectureSchedule(
            class_level=class_level,
            stream=stream,
            subject_id=payload.subject_id,
            teacher_id=payload.teacher_id,
            topic=payload.topic.strip(),
            lecture_notes=(payload.lecture_notes or "").strip() or None,
            duration_minutes=int(payload.duration_minutes),
            scheduled_at=payload.scheduled_at,
            status=LectureScheduleStatus.SCHEDULED,
            all_students_in_scope=bool(payload.all_students_in_scope),
            created_by_user_id=actor_user_id,
            completed_at=None,
            completed_by_user_id=None,
        )
        self.session.add(schedule)
        await self.session.flush()

        selected_student_ids: list[str] = []
        if not schedule.all_students_in_scope:
            requested_ids = list(dict.fromkeys(payload.student_ids or []))

            rows = (
                await self.session.execute(
                    select(StudentProfile.id, StudentProfile.class_name, StudentProfile.stream, Batch.id, Standard.name)
                    .join(User, User.id == StudentProfile.user_id)
                    .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
                    .outerjoin(Standard, Standard.id == Batch.standard_id)
                    .where(StudentProfile.id.in_(requested_ids), User.status == UserStatus.ACTIVE)
                )
            ).all()

            found_ids = {row[0] for row in rows}
            missing = [student_id for student_id in requested_ids if student_id not in found_ids]
            if missing:
                raise ValueError("One or more selected students are invalid or inactive")

            invalid_scope = []
            for student_id, class_name, student_stream, _batch_id, standard_name in rows:
                student_class = self._extract_class_level(class_name, standard_name)
                normalized_student_stream = self._normalize_stream(
                    student_class,
                    student_stream,
                ) if student_class is not None else "common"

                if student_class != class_level:
                    invalid_scope.append(student_id)
                    continue
                if class_level in {11, 12} and normalized_student_stream != stream:
                    invalid_scope.append(student_id)

            if invalid_scope:
                raise ValueError("Selected students must belong to selected class/stream")

            for student_id in requested_ids:
                self.session.add(
                    LectureScheduleStudent(
                        lecture_schedule_id=schedule.id,
                        student_id=student_id,
                    )
                )
            selected_student_ids = requested_ids

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.lecture_schedule.create",
            entity_type="lecture_schedule",
            entity_id=schedule.id,
            before_state=None,
            after_state={
                "class_level": schedule.class_level,
                "stream": schedule.stream,
                "subject_id": schedule.subject_id,
                "teacher_id": schedule.teacher_id,
                "topic": schedule.topic,
                "scheduled_at": schedule.scheduled_at.isoformat() if schedule.scheduled_at else None,
                "duration_minutes": schedule.duration_minutes,
                "all_students_in_scope": schedule.all_students_in_scope,
                "student_ids": selected_student_ids,
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "id": schedule.id,
            "class_level": schedule.class_level,
            "stream": schedule.stream,
            "subject_id": schedule.subject_id,
            "subject_name": subject.name,
            "teacher_id": schedule.teacher_id,
            "teacher_name": teacher_user.full_name,
            "topic": schedule.topic,
            "lecture_notes": schedule.lecture_notes,
            "duration_minutes": schedule.duration_minutes,
            "scheduled_at": schedule.scheduled_at,
            "status": schedule.status.value if hasattr(schedule.status, "value") else str(schedule.status),
            "all_students_in_scope": schedule.all_students_in_scope,
            "selected_students_count": len(selected_student_ids),
            "created_at": schedule.created_at,
        }

    async def list_admin_schedules(
        self,
        *,
        class_level: int | None,
        stream: str | None,
        subject_id: str | None,
        teacher_id: str | None,
        status: str | None,
        search: str | None,
        scheduled_from: date | None,
        scheduled_to: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        student_count_subquery = (
            select(
                LectureScheduleStudent.lecture_schedule_id.label("schedule_id"),
                func.count(LectureScheduleStudent.id).label("selected_students_count"),
            )
            .group_by(LectureScheduleStudent.lecture_schedule_id)
            .subquery()
        )

        query = (
            select(
                LectureSchedule,
                Subject,
                TeacherProfile,
                User,
                func.coalesce(student_count_subquery.c.selected_students_count, 0),
            )
            .join(Subject, Subject.id == LectureSchedule.subject_id)
            .join(TeacherProfile, TeacherProfile.id == LectureSchedule.teacher_id)
            .join(User, User.id == TeacherProfile.user_id)
            .outerjoin(
                student_count_subquery,
                student_count_subquery.c.schedule_id == LectureSchedule.id,
            )
        )

        if class_level is not None:
            query = query.where(LectureSchedule.class_level == class_level)
        if stream and class_level in {11, 12}:
            query = query.where(LectureSchedule.stream == self._normalize_stream(class_level, stream))
        if subject_id:
            query = query.where(LectureSchedule.subject_id == subject_id)
        if teacher_id:
            query = query.where(LectureSchedule.teacher_id == teacher_id)
        if status:
            query = query.where(LectureSchedule.status == LectureScheduleStatus(status))
        if search:
            query = query.where(
                or_(
                    LectureSchedule.topic.ilike(f"%{search}%"),
                    Subject.name.ilike(f"%{search}%"),
                    User.full_name.ilike(f"%{search}%"),
                )
            )

        if scheduled_from:
            query = query.where(func.date(LectureSchedule.scheduled_at) >= scheduled_from.isoformat())
        if scheduled_to:
            query = query.where(func.date(LectureSchedule.scheduled_at) <= scheduled_to.isoformat())

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

        rows = (
            await self.session.execute(
                query.order_by(LectureSchedule.scheduled_at.asc(), LectureSchedule.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()

        items = [
            {
                "id": schedule.id,
                "class_level": schedule.class_level,
                "stream": schedule.stream,
                "subject_id": schedule.subject_id,
                "subject_name": subject.name,
                "teacher_id": schedule.teacher_id,
                "teacher_name": teacher_user.full_name,
                "batch_id": schedule.batch_id,
                "topic": schedule.topic,
                "lecture_notes": schedule.lecture_notes,
                "duration_minutes": schedule.duration_minutes,
                "scheduled_at": schedule.scheduled_at,
                "status": schedule.status.value if hasattr(schedule.status, "value") else str(schedule.status),
                "all_students_in_scope": schedule.all_students_in_scope,
                "selected_students_count": int(selected_students_count or 0),
                "completed_at": schedule.completed_at,
                "created_at": schedule.created_at,
            }
            for schedule, subject, _teacher, teacher_user, selected_students_count in rows
        ]
        return items, total

    async def update_admin_schedule_status(
        self,
        *,
        schedule_id: str,
        status: str,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        schedule = await self.session.get(LectureSchedule, schedule_id)
        if not schedule:
            raise NotFoundException("Lecture schedule not found")

        next_status = LectureScheduleStatus(status)
        current_status = schedule.status

        before = {
            "status": current_status.value if hasattr(current_status, "value") else str(current_status),
            "completed_at": schedule.completed_at.isoformat() if schedule.completed_at else None,
        }

        if current_status == LectureScheduleStatus.DONE and next_status != LectureScheduleStatus.DONE:
            raise ValueError("Completed lecture cannot be reverted")

        created_completed_lecture_id: str | None = None
        salary_ledger: dict | None = None

        if next_status == LectureScheduleStatus.DONE:
            existing = (
                await self.session.execute(
                    select(CompletedLecture).where(CompletedLecture.schedule_id == schedule.id)
                )
            ).scalar_one_or_none()

            if existing is None:
                completed = CompletedLecture(
                    teacher_id=schedule.teacher_id,
                    subject_id=schedule.subject_id,
                    batch_id=schedule.batch_id,
                    schedule_id=schedule.id,
                    class_level=schedule.class_level,
                    stream=schedule.stream,
                    topic=schedule.topic,
                    summary=schedule.lecture_notes,
                    completed_at=datetime.now(UTC),
                )
                self.session.add(completed)
                await self.session.flush()
                created_completed_lecture_id = completed.id
            else:
                created_completed_lecture_id = existing.id

            schedule.status = LectureScheduleStatus.DONE
            schedule.completed_at = datetime.now(UTC)
            schedule.completed_by_user_id = actor_user_id
            salary_ledger = await self._record_teacher_salary_for_schedule(
                schedule=schedule,
                completed_lecture_id=created_completed_lecture_id,
            )

        elif next_status == LectureScheduleStatus.CANCELED:
            schedule.status = LectureScheduleStatus.CANCELED
            schedule.completed_at = None
            schedule.completed_by_user_id = None

        else:
            schedule.status = LectureScheduleStatus.SCHEDULED
            schedule.completed_at = None
            schedule.completed_by_user_id = None

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.lecture_schedule.update_status",
            entity_type="lecture_schedule",
            entity_id=schedule.id,
            before_state=before,
            after_state={
                "status": schedule.status.value,
                "completed_at": schedule.completed_at.isoformat() if schedule.completed_at else None,
                "completed_lecture_id": created_completed_lecture_id,
                "salary_ledger": salary_ledger,
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "id": schedule.id,
            "status": schedule.status.value,
            "completed_at": schedule.completed_at,
            "completed_lecture_id": created_completed_lecture_id,
            "salary_ledger": salary_ledger,
            "updated_at": schedule.updated_at,
        }

    async def list_for_teacher(
        self,
        *,
        teacher_id: str,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = (
            select(LectureSchedule, Subject)
            .join(Subject, Subject.id == LectureSchedule.subject_id)
            .where(LectureSchedule.teacher_id == teacher_id)
        )

        if status:
            query = query.where(LectureSchedule.status == LectureScheduleStatus(status))

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(LectureSchedule.scheduled_at.asc(), LectureSchedule.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()

        items = [
            {
                "id": schedule.id,
                "class_level": schedule.class_level,
                "stream": schedule.stream,
                "subject_id": schedule.subject_id,
                "subject_name": subject.name,
                "topic": schedule.topic,
                "lecture_notes": schedule.lecture_notes,
                "duration_minutes": schedule.duration_minutes,
                "scheduled_at": schedule.scheduled_at,
                "status": schedule.status.value if hasattr(schedule.status, "value") else str(schedule.status),
                "completed_at": schedule.completed_at,
                "all_students_in_scope": schedule.all_students_in_scope,
            }
            for schedule, subject in rows
        ]
        return items, total

    async def list_for_student(
        self,
        *,
        student_profile,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        class_level = self._extract_class_level(student_profile.class_name)
        standard_name: str | None = None
        if student_profile.current_batch_id:
            standard_row = (
                await self.session.execute(
                    select(Standard.name)
                    .join(Batch, Batch.standard_id == Standard.id)
                    .where(Batch.id == student_profile.current_batch_id)
                )
            ).first()
            standard_name = standard_row[0] if standard_row else None

        if class_level is None:
            class_level = self._extract_class_level(None, standard_name)

        if class_level is None:
            # Conservative fallback: no class mapped means no schedule scope.
            return [], 0

        resolved_stream = self._extract_stream(
            student_profile.stream,
            student_profile.class_name,
            standard_name,
        )
        if class_level in {11, 12} and resolved_stream is None:
            return [], 0

        stream = self._normalize_stream(class_level, resolved_stream)

        selected_join = and_(
            LectureScheduleStudent.lecture_schedule_id == LectureSchedule.id,
            LectureScheduleStudent.student_id == student_profile.id,
        )

        all_scope_clause = and_(
            LectureSchedule.all_students_in_scope.is_(True),
            LectureSchedule.class_level == class_level,
            LectureSchedule.stream == stream,
            or_(
                LectureSchedule.batch_id.is_(None),
                LectureSchedule.batch_id == student_profile.current_batch_id,
            ),
        )
        selected_scope_clause = LectureScheduleStudent.student_id.is_not(None)

        query = (
            select(LectureSchedule, Subject, TeacherProfile, User)
            .join(Subject, Subject.id == LectureSchedule.subject_id)
            .join(TeacherProfile, TeacherProfile.id == LectureSchedule.teacher_id)
            .join(User, User.id == TeacherProfile.user_id)
            .outerjoin(LectureScheduleStudent, selected_join)
            .where(or_(all_scope_clause, selected_scope_clause))
        )

        if status:
            query = query.where(LectureSchedule.status == LectureScheduleStatus(status))

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(LectureSchedule.scheduled_at.asc(), LectureSchedule.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()

        items = [
            {
                "id": schedule.id,
                "class_level": schedule.class_level,
                "stream": schedule.stream,
                "subject_id": schedule.subject_id,
                "subject_name": subject.name,
                "teacher_id": schedule.teacher_id,
                "teacher_name": teacher_user.full_name,
                "topic": schedule.topic,
                "lecture_notes": schedule.lecture_notes,
                "duration_minutes": schedule.duration_minutes,
                "scheduled_at": schedule.scheduled_at,
                "status": schedule.status.value if hasattr(schedule.status, "value") else str(schedule.status),
                "completed_at": schedule.completed_at,
            }
            for schedule, subject, _teacher, teacher_user in rows
        ]
        return items, total
