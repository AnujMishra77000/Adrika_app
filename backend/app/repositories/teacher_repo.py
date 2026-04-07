from datetime import UTC, datetime

from sqlalchemy import and_, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.academic import Batch, Standard, Subject, TeacherBatchAssignment, TeacherProfile
from app.db.models.assessment import Assessment, AssessmentAssignment
from app.db.models.content import Notice, NoticeRead, NoticeTarget
from app.db.models.doubt import Doubt, DoubtMessage
from app.db.models.enums import AssessmentStatus, HomeworkStatus, NoticeStatus
from app.db.models.homework import Homework, HomeworkTarget


class TeacherRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_profile_by_user_id(self, *, user_id: str) -> TeacherProfile | None:
        result = await self.session.execute(select(TeacherProfile).where(TeacherProfile.user_id == user_id))
        return result.scalar_one_or_none()

    async def list_assignments(self, *, teacher_id: str) -> list[tuple[TeacherBatchAssignment, Batch, Standard, Subject]]:
        rows = (
            await self.session.execute(
                select(TeacherBatchAssignment, Batch, Standard, Subject)
                .join(Batch, Batch.id == TeacherBatchAssignment.batch_id)
                .join(Standard, Standard.id == Batch.standard_id)
                .join(Subject, Subject.id == TeacherBatchAssignment.subject_id)
                .where(TeacherBatchAssignment.teacher_id == teacher_id)
                .order_by(Standard.name.asc(), Batch.name.asc(), Subject.name.asc())
            )
        ).all()
        return rows

    async def assigned_batch_ids(self, *, teacher_id: str) -> list[str]:
        rows = (
            await self.session.execute(
                select(TeacherBatchAssignment.batch_id)
                .where(TeacherBatchAssignment.teacher_id == teacher_id)
                .distinct()
            )
        ).scalars().all()
        return rows

    async def assigned_subject_ids(self, *, teacher_id: str) -> list[str]:
        rows = (
            await self.session.execute(
                select(TeacherBatchAssignment.subject_id)
                .where(TeacherBatchAssignment.teacher_id == teacher_id)
                .distinct()
            )
        ).scalars().all()
        return rows

    async def list_notices_for_teacher(
        self,
        *,
        user_id: str,
        teacher_id: str,
        batch_ids: list[str],
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[Notice, bool]], int]:
        now = datetime.now(UTC)
        target_clauses = [
            and_(NoticeTarget.target_type == "all", NoticeTarget.target_id == "all"),
            and_(NoticeTarget.target_type == "teacher", NoticeTarget.target_id == teacher_id),
        ]
        if batch_ids:
            target_clauses.append(and_(NoticeTarget.target_type == "batch", NoticeTarget.target_id.in_(batch_ids)))

        base = (
            select(Notice)
            .join(NoticeTarget, NoticeTarget.notice_id == Notice.id)
            .where(
                Notice.status == NoticeStatus.PUBLISHED,
                or_(Notice.publish_at.is_(None), Notice.publish_at <= now),
                or_(*target_clauses),
            )
            .distinct()
        )

        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

        read_exists = (
            select(literal(True))
            .where(NoticeRead.notice_id == Notice.id, NoticeRead.user_id == user_id)
            .exists()
        )

        rows = (
            await self.session.execute(
                select(Notice, read_exists)
                .join(NoticeTarget, NoticeTarget.notice_id == Notice.id)
                .where(
                    Notice.status == NoticeStatus.PUBLISHED,
                    or_(Notice.publish_at.is_(None), Notice.publish_at <= now),
                    or_(*target_clauses),
                )
                .distinct()
                .order_by(Notice.priority.desc(), Notice.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return rows, total

    async def get_notice_for_teacher(
        self,
        *,
        notice_id: str,
        user_id: str,
        teacher_id: str,
        batch_ids: list[str],
    ) -> tuple[Notice | None, bool]:
        target_clauses = [
            and_(NoticeTarget.target_type == "all", NoticeTarget.target_id == "all"),
            and_(NoticeTarget.target_type == "teacher", NoticeTarget.target_id == teacher_id),
        ]
        if batch_ids:
            target_clauses.append(and_(NoticeTarget.target_type == "batch", NoticeTarget.target_id.in_(batch_ids)))

        read_exists = (
            select(literal(True))
            .where(NoticeRead.notice_id == Notice.id, NoticeRead.user_id == user_id)
            .exists()
        )

        row = (
            await self.session.execute(
                select(Notice, read_exists)
                .join(NoticeTarget, NoticeTarget.notice_id == Notice.id)
                .where(
                    Notice.id == notice_id,
                    Notice.status == NoticeStatus.PUBLISHED,
                    or_(*target_clauses),
                )
                .distinct()
            )
        ).first()
        if not row:
            return None, False
        return row[0], bool(row[1])

    async def mark_notice_read(self, *, notice_id: str, user_id: str) -> None:
        existing = await self.session.execute(
            select(NoticeRead).where(NoticeRead.notice_id == notice_id, NoticeRead.user_id == user_id)
        )
        if existing.scalar_one_or_none():
            return

        self.session.add(NoticeRead(notice_id=notice_id, user_id=user_id, read_at=datetime.now(UTC)))

    async def list_homework_for_teacher(
        self,
        *,
        batch_ids: list[str],
        subject_ids: list[str],
        subject_id: str | None,
        due_from,
        due_to,
        limit: int,
        offset: int,
    ) -> tuple[list[Homework], int]:
        if not subject_ids:
            return [], 0
        target_clauses = [and_(HomeworkTarget.target_type == "all", HomeworkTarget.target_id == "all")]
        if batch_ids:
            target_clauses.append(and_(HomeworkTarget.target_type == "batch", HomeworkTarget.target_id.in_(batch_ids)))

        filters = [Homework.status == HomeworkStatus.PUBLISHED, or_(*target_clauses)]
        if subject_ids:
            filters.append(Homework.subject_id.in_(subject_ids))
        if subject_id:
            filters.append(Homework.subject_id == subject_id)
        if due_from:
            filters.append(Homework.due_date >= due_from)
        if due_to:
            filters.append(Homework.due_date <= due_to)

        base = (
            select(Homework)
            .join(HomeworkTarget, HomeworkTarget.homework_id == Homework.id)
            .where(*filters)
            .distinct()
        )

        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                base.order_by(Homework.due_date.asc(), Homework.created_at.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()
        return rows, total

    async def pending_homework_count_for_teacher(self, *, batch_ids: list[str], subject_ids: list[str]) -> int:
        if not subject_ids:
            return 0
        target_clauses = [and_(HomeworkTarget.target_type == "all", HomeworkTarget.target_id == "all")]
        if batch_ids:
            target_clauses.append(and_(HomeworkTarget.target_type == "batch", HomeworkTarget.target_id.in_(batch_ids)))

        filters = [Homework.status == HomeworkStatus.PUBLISHED, or_(*target_clauses)]
        if subject_ids:
            filters.append(Homework.subject_id.in_(subject_ids))

        stmt = select(func.count()).select_from(Homework).join(HomeworkTarget, HomeworkTarget.homework_id == Homework.id).where(*filters)
        return (await self.session.execute(stmt)).scalar_one()

    async def list_assessments_for_teacher(
        self,
        *,
        batch_ids: list[str],
        subject_ids: list[str],
        assessment_type: str | None,
        status: str | None,
        subject_id: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Assessment], int]:
        if not subject_ids:
            return [], 0
        target_clauses = [and_(AssessmentAssignment.target_type == "all", AssessmentAssignment.target_id == "all")]
        if batch_ids:
            target_clauses.append(
                and_(AssessmentAssignment.target_type == "batch", AssessmentAssignment.target_id.in_(batch_ids))
            )

        filters = [or_(*target_clauses)]
        if subject_ids:
            filters.append(Assessment.subject_id.in_(subject_ids))
        if assessment_type:
            filters.append(Assessment.assessment_type == assessment_type)
        if status:
            filters.append(Assessment.status == status)
        if subject_id:
            filters.append(Assessment.subject_id == subject_id)

        base = (
            select(Assessment)
            .join(AssessmentAssignment, AssessmentAssignment.assessment_id == Assessment.id)
            .where(*filters)
            .distinct()
        )

        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                base.order_by(Assessment.starts_at.desc().nulls_last()).limit(limit).offset(offset)
            )
        ).scalars().all()
        return rows, total

    async def upcoming_assessments_count_for_teacher(self, *, batch_ids: list[str], subject_ids: list[str]) -> int:
        if not subject_ids:
            return 0
        now = datetime.now(UTC)
        target_clauses = [and_(AssessmentAssignment.target_type == "all", AssessmentAssignment.target_id == "all")]
        if batch_ids:
            target_clauses.append(
                and_(AssessmentAssignment.target_type == "batch", AssessmentAssignment.target_id.in_(batch_ids))
            )

        filters = [
            Assessment.status == AssessmentStatus.PUBLISHED,
            Assessment.starts_at.is_not(None),
            Assessment.starts_at >= now,
            or_(*target_clauses),
        ]
        if subject_ids:
            filters.append(Assessment.subject_id.in_(subject_ids))

        stmt = (
            select(func.count())
            .select_from(Assessment)
            .join(AssessmentAssignment, AssessmentAssignment.assessment_id == Assessment.id)
            .where(*filters)
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def list_doubts_for_teacher(
        self,
        *,
        subject_ids: list[str],
        status: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Doubt], int]:
        if not subject_ids:
            return [], 0

        filters = [Doubt.subject_id.in_(subject_ids)]
        if status:
            filters.append(Doubt.status == status)
        if query:
            filters.append(or_(Doubt.topic.ilike(f"%{query}%"), Doubt.description.ilike(f"%{query}%")))

        base = select(Doubt).where(*filters)
        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (
            await self.session.execute(base.order_by(Doubt.created_at.desc()).limit(limit).offset(offset))
        ).scalars().all()
        return rows, total

    async def open_doubts_count_for_teacher(self, *, subject_ids: list[str]) -> int:
        if not subject_ids:
            return 0

        filters = [Doubt.status.in_(["open", "in_progress"]), Doubt.subject_id.in_(subject_ids)]
        stmt = select(func.count()).where(*filters)
        return (await self.session.execute(stmt)).scalar_one()

    async def get_doubt_for_teacher(self, *, doubt_id: str, subject_ids: list[str]) -> Doubt | None:
        if not subject_ids:
            return None

        filters = [Doubt.id == doubt_id, Doubt.subject_id.in_(subject_ids)]

        result = await self.session.execute(select(Doubt).where(*filters))
        return result.scalar_one_or_none()

    async def list_doubt_messages(self, *, doubt_id: str) -> list[DoubtMessage]:
        rows = (
            await self.session.execute(
                select(DoubtMessage).where(DoubtMessage.doubt_id == doubt_id).order_by(DoubtMessage.created_at.asc())
            )
        ).scalars().all()
        return rows

    async def add_doubt_message(self, *, doubt_id: str, sender_user_id: str, message: str) -> DoubtMessage:
        doubt_message = DoubtMessage(doubt_id=doubt_id, sender_user_id=sender_user_id, message=message)
        self.session.add(doubt_message)
        await self.session.flush()
        return doubt_message

    async def update_doubt_status(self, *, doubt: Doubt, status: str) -> Doubt:
        doubt.status = status
        await self.session.flush()
        return doubt
