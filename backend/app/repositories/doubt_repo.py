from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.academic import (
    CompletedLecture,
    LectureSchedule,
    LectureScheduleStudent,
    StudentProfile,
    Subject,
    TeacherProfile,
)
from app.db.models.doubt import Doubt, DoubtMessage
from app.db.models.user import User


class DoubtRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_student(
        self,
        *,
        student_id: str,
        status: str | None,
        subject_id: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Doubt], int]:
        filters = [Doubt.student_id == student_id]
        if status:
            filters.append(Doubt.status == status)
        if subject_id:
            filters.append(Doubt.subject_id == subject_id)
        if query:
            filters.append(Doubt.topic.ilike(f"%{query}%"))

        base = select(Doubt).where(*filters)
        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (
            await self.session.execute(base.order_by(Doubt.created_at.desc()).limit(limit).offset(offset))
        ).scalars().all()
        return rows, total

    async def create_doubt(
        self,
        *,
        student_id: str,
        subject_id: str,
        topic: str,
        description: str,
        lecture_id: str | None = None,
        teacher_id: str | None = None,
    ) -> Doubt:
        doubt = Doubt(
            student_id=student_id,
            subject_id=subject_id,
            topic=topic,
            description=description,
            lecture_id=lecture_id,
            teacher_id=teacher_id,
        )
        self.session.add(doubt)
        await self.session.flush()
        return doubt

    async def get_doubt_for_student(self, *, doubt_id: str, student_id: str) -> Doubt | None:
        result = await self.session.execute(
            select(Doubt).where(Doubt.id == doubt_id, Doubt.student_id == student_id)
        )
        return result.scalar_one_or_none()

    async def get_doubt_for_teacher(
        self,
        *,
        doubt_id: str,
        teacher_id: str,
        subject_ids: list[str],
    ) -> Doubt | None:
        ownership_filters = [Doubt.teacher_id == teacher_id]
        if subject_ids:
            ownership_filters.append(and_(Doubt.teacher_id.is_(None), Doubt.subject_id.in_(subject_ids)))

        result = await self.session.execute(
            select(Doubt).where(
                Doubt.id == doubt_id,
                or_(*ownership_filters),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_teacher(
        self,
        *,
        teacher_id: str,
        subject_ids: list[str],
        status: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Doubt], int]:
        ownership_filters = [Doubt.teacher_id == teacher_id]
        if subject_ids:
            ownership_filters.append(and_(Doubt.teacher_id.is_(None), Doubt.subject_id.in_(subject_ids)))

        filters = [or_(*ownership_filters)]
        if status:
            filters.append(Doubt.status == status)
        if query:
            filters.append(or_(Doubt.topic.ilike(f"%{query}%"), Doubt.description.ilike(f"%{query}%")))

        base = select(Doubt).where(*filters)
        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (
            await self.session.execute(base.order_by(Doubt.updated_at.desc()).limit(limit).offset(offset))
        ).scalars().all()
        return rows, total

    async def open_count_for_teacher(self, *, teacher_id: str, subject_ids: list[str]) -> int:
        ownership_filters = [Doubt.teacher_id == teacher_id]
        if subject_ids:
            ownership_filters.append(and_(Doubt.teacher_id.is_(None), Doubt.subject_id.in_(subject_ids)))

        stmt = select(func.count()).where(
            or_(*ownership_filters),
            Doubt.status.in_(["open", "in_progress"]),
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def add_message(self, *, doubt_id: str, sender_user_id: str, message: str) -> DoubtMessage:
        doubt_message = DoubtMessage(doubt_id=doubt_id, sender_user_id=sender_user_id, message=message)
        self.session.add(doubt_message)
        await self.session.flush()
        return doubt_message

    async def update_doubt_status(self, *, doubt: Doubt, status: str) -> Doubt:
        doubt.status = status
        await self.session.flush()
        return doubt

    async def list_messages(self, *, doubt_id: str, since: datetime | None = None) -> list[DoubtMessage]:
        stmt = select(DoubtMessage).where(DoubtMessage.doubt_id == doubt_id)
        if since is not None:
            stmt = stmt.where(DoubtMessage.created_at > since)

        rows = (
            await self.session.execute(
                stmt.order_by(DoubtMessage.created_at.asc(), DoubtMessage.id.asc())
            )
        ).scalars().all()
        return rows

    @staticmethod
    def _scope_condition_for_completed_lecture(
        *,
        batch_id: str | None,
        class_level: int | None,
        stream: str,
    ):
        if batch_id and class_level is not None:
            return or_(
                CompletedLecture.batch_id == batch_id,
                and_(
                    CompletedLecture.batch_id.is_(None),
                    CompletedLecture.class_level == class_level,
                    CompletedLecture.stream == stream,
                ),
            )
        if batch_id:
            return CompletedLecture.batch_id == batch_id
        if class_level is not None:
            return and_(
                CompletedLecture.batch_id.is_(None),
                CompletedLecture.class_level == class_level,
                CompletedLecture.stream == stream,
            )
        return None

    @staticmethod
    def _scope_condition_for_schedule(
        *,
        batch_id: str | None,
        class_level: int | None,
        stream: str,
    ):
        if batch_id and class_level is not None:
            return or_(
                LectureSchedule.batch_id == batch_id,
                and_(
                    LectureSchedule.batch_id.is_(None),
                    LectureSchedule.class_level == class_level,
                    LectureSchedule.stream == stream,
                ),
            )
        if batch_id:
            return LectureSchedule.batch_id == batch_id
        if class_level is not None:
            return and_(
                LectureSchedule.batch_id.is_(None),
                LectureSchedule.class_level == class_level,
                LectureSchedule.stream == stream,
            )
        return None

    async def list_done_lectures_for_student(
        self,
        *,
        student_id: str,
        batch_id: str | None,
        class_level: int | None,
        stream: str,
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[CompletedLecture, Subject, TeacherProfile, User]], int]:
        completed_scope = self._scope_condition_for_completed_lecture(
            batch_id=batch_id,
            class_level=class_level,
            stream=stream,
        )
        schedule_scope = self._scope_condition_for_schedule(
            batch_id=batch_id,
            class_level=class_level,
            stream=stream,
        )

        selected_join = and_(
            LectureScheduleStudent.lecture_schedule_id == CompletedLecture.schedule_id,
            LectureScheduleStudent.student_id == student_id,
        )

        visibility_filters = [
            and_(
                CompletedLecture.schedule_id.is_not(None),
                LectureSchedule.all_students_in_scope.is_(False),
                LectureScheduleStudent.id.is_not(None),
            )
        ]

        if completed_scope is not None:
            visibility_filters.append(
                and_(
                    CompletedLecture.schedule_id.is_(None),
                    completed_scope,
                )
            )

        if schedule_scope is not None:
            visibility_filters.append(
                and_(
                    CompletedLecture.schedule_id.is_not(None),
                    LectureSchedule.all_students_in_scope.is_(True),
                    schedule_scope,
                )
            )

        base = (
            select(CompletedLecture, Subject, TeacherProfile, User)
            .join(Subject, Subject.id == CompletedLecture.subject_id)
            .join(TeacherProfile, TeacherProfile.id == CompletedLecture.teacher_id)
            .join(User, User.id == TeacherProfile.user_id)
            .outerjoin(LectureSchedule, LectureSchedule.id == CompletedLecture.schedule_id)
            .outerjoin(LectureScheduleStudent, selected_join)
            .where(or_(*visibility_filters))
        )

        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

        rows = (
            await self.session.execute(
                base.order_by(CompletedLecture.completed_at.desc(), CompletedLecture.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return rows, total

    async def get_done_lecture_for_student(
        self,
        *,
        student_id: str,
        lecture_id: str,
        batch_id: str | None,
        class_level: int | None,
        stream: str,
    ) -> tuple[CompletedLecture, Subject, TeacherProfile, User] | None:
        completed_scope = self._scope_condition_for_completed_lecture(
            batch_id=batch_id,
            class_level=class_level,
            stream=stream,
        )
        schedule_scope = self._scope_condition_for_schedule(
            batch_id=batch_id,
            class_level=class_level,
            stream=stream,
        )

        selected_join = and_(
            LectureScheduleStudent.lecture_schedule_id == CompletedLecture.schedule_id,
            LectureScheduleStudent.student_id == student_id,
        )

        visibility_filters = [
            and_(
                CompletedLecture.schedule_id.is_not(None),
                LectureSchedule.all_students_in_scope.is_(False),
                LectureScheduleStudent.id.is_not(None),
            )
        ]

        if completed_scope is not None:
            visibility_filters.append(
                and_(
                    CompletedLecture.schedule_id.is_(None),
                    completed_scope,
                )
            )

        if schedule_scope is not None:
            visibility_filters.append(
                and_(
                    CompletedLecture.schedule_id.is_not(None),
                    LectureSchedule.all_students_in_scope.is_(True),
                    schedule_scope,
                )
            )

        row = (
            await self.session.execute(
                select(CompletedLecture, Subject, TeacherProfile, User)
                .join(Subject, Subject.id == CompletedLecture.subject_id)
                .join(TeacherProfile, TeacherProfile.id == CompletedLecture.teacher_id)
                .join(User, User.id == TeacherProfile.user_id)
                .outerjoin(LectureSchedule, LectureSchedule.id == CompletedLecture.schedule_id)
                .outerjoin(LectureScheduleStudent, selected_join)
                .where(
                    CompletedLecture.id == lecture_id,
                    or_(*visibility_filters),
                )
            )
        ).first()
        return row

    async def get_student_user_id(self, *, student_id: str) -> str | None:
        row = (
            await self.session.execute(
                select(StudentProfile.user_id).where(StudentProfile.id == student_id)
            )
        ).first()
        return row[0] if row else None

    async def get_teacher_user_id(self, *, teacher_id: str) -> str | None:
        row = (
            await self.session.execute(
                select(TeacherProfile.user_id).where(TeacherProfile.id == teacher_id)
            )
        ).first()
        return row[0] if row else None

    async def get_lecture_by_id(self, *, lecture_id: str) -> CompletedLecture | None:
        return await self.session.get(CompletedLecture, lecture_id)
