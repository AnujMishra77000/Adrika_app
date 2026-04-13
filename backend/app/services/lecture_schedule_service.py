from __future__ import annotations

import re
from datetime import UTC, date, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
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
)
from app.db.models.audit import AuditLog
from app.db.models.enums import LectureScheduleStatus, UserStatus
from app.db.models.user import User


class LectureScheduleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _extract_class_level(class_name: str | None, standard_name: str | None = None) -> int | None:
        source = f"{class_name or ''} {standard_name or ''}".lower()
        match = re.search(r"(10|11|12)", source)
        if not match:
            return None
        value = int(match.group(1))
        if value in {10, 11, 12}:
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
        if class_level == 10:
            return "common"

        value = (stream or "").strip().lower()
        if value in {"science", "sci"}:
            return "science"
        if value in {"commerce", "comm"}:
            return "commerce"
        raise ValueError("stream is required for class 11 and 12")

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
        if stream and class_level != 10:
            assignment_filters.append(Standard.name.ilike(f"%{stream}%"))

        query = (
            select(
                TeacherProfile,
                User,
                func.count(func.distinct(TeacherBatchAssignment.id)).label("assignment_count"),
            )
            .join(User, User.id == TeacherProfile.user_id)
            .outerjoin(TeacherBatchAssignment, TeacherBatchAssignment.teacher_id == TeacherProfile.id)
            .outerjoin(Batch, Batch.id == TeacherBatchAssignment.batch_id)
            .outerjoin(Standard, Standard.id == Batch.standard_id)
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

        if status:
            query = query.where(User.status == UserStatus(status))

        query = query.group_by(TeacherProfile.id, User.id)

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
                "status": user.status.value if hasattr(user.status, "value") else str(user.status),
                "created_at": user.created_at,
                "assignment_count": int(assignment_count or 0),
            }
            for profile, user, assignment_count in rows
        ]
        return items, total

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

    async def _validate_teacher_assignment(
        self,
        *,
        teacher_id: str,
        subject_id: str,
    ) -> None:
        assignment_count = (
            await self.session.execute(
                select(func.count()).select_from(TeacherBatchAssignment).where(
                    TeacherBatchAssignment.teacher_id == teacher_id,
                    TeacherBatchAssignment.subject_id == subject_id,
                )
            )
        ).scalar_one()

        if int(assignment_count or 0) <= 0:
            raise ValueError("Teacher is not assigned to this subject")

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
        await self._validate_teacher_assignment(
            teacher_id=payload.teacher_id,
            subject_id=payload.subject_id,
        )

        schedule = LectureSchedule(
            class_level=class_level,
            stream=stream,
            subject_id=payload.subject_id,
            teacher_id=payload.teacher_id,
            topic=payload.topic.strip(),
            lecture_notes=(payload.lecture_notes or "").strip() or None,
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
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "id": schedule.id,
            "status": schedule.status.value,
            "completed_at": schedule.completed_at,
            "completed_lecture_id": created_completed_lecture_id,
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
                "scheduled_at": schedule.scheduled_at,
                "status": schedule.status.value if hasattr(schedule.status, "value") else str(schedule.status),
                "completed_at": schedule.completed_at,
            }
            for schedule, subject, _teacher, teacher_user in rows
        ]
        return items, total
