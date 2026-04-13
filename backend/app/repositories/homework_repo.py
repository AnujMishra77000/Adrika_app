from datetime import UTC, date, datetime, time

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import HomeworkStatus, HomeworkSubmissionStatus
from app.db.models.homework import (
    Homework,
    HomeworkAttachment,
    HomeworkRead,
    HomeworkSubmission,
    HomeworkSubmissionAttachment,
    HomeworkTarget,
)


class HomeworkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _normalize_stream(stream: str | None) -> str | None:
        value = (stream or "").strip().lower()
        if value in {"science", "sci"}:
            return "science"
        if value in {"commerce", "comm"}:
            return "commerce"
        return None

    @classmethod
    def _grade_target_ids(cls, *, class_level: str | int | None, stream: str | None) -> list[str]:
        if class_level is None:
            return []

        class_text = str(class_level).strip()
        if class_text not in {"10", "11", "12"}:
            return []

        ids = [class_text]
        normalized_stream = cls._normalize_stream(stream)
        if class_text in {"11", "12"} and normalized_stream:
            ids.append(f"{class_text}:{normalized_stream}")
        return ids

    @staticmethod
    def _visibility_filters(now: datetime) -> list:
        return [
            Homework.status == HomeworkStatus.PUBLISHED,
            or_(Homework.publish_at.is_(None), Homework.publish_at <= now),
            or_(Homework.expires_at.is_(None), Homework.expires_at >= now),
        ]

    @staticmethod
    def _due_window_filters(due_from: date | None, due_to: date | None) -> list:
        filters: list = []

        if due_from:
            due_from_dt = datetime.combine(due_from, time.min, tzinfo=UTC)
            filters.append(
                or_(
                    and_(Homework.due_at.is_not(None), Homework.due_at >= due_from_dt),
                    and_(Homework.due_at.is_(None), Homework.due_date >= due_from),
                )
            )

        if due_to:
            due_to_dt = datetime.combine(due_to, time.max, tzinfo=UTC)
            filters.append(
                or_(
                    and_(Homework.due_at.is_not(None), Homework.due_at <= due_to_dt),
                    and_(Homework.due_at.is_(None), Homework.due_date <= due_to),
                )
            )

        return filters

    @classmethod
    def _target_filters(
        cls,
        *,
        student_id: str,
        batch_id: str | None,
        class_level: str | int | None,
        stream: str | None,
    ) -> list:
        filters = [
            and_(HomeworkTarget.target_type == "all", HomeworkTarget.target_id == "all"),
            and_(HomeworkTarget.target_type == "all_students", HomeworkTarget.target_id == "all"),
            and_(HomeworkTarget.target_type == "student", HomeworkTarget.target_id == student_id),
        ]

        if batch_id:
            filters.append(and_(HomeworkTarget.target_type == "batch", HomeworkTarget.target_id == batch_id))

        grade_ids = cls._grade_target_ids(class_level=class_level, stream=stream)
        if grade_ids:
            filters.append(and_(HomeworkTarget.target_type == "grade", HomeworkTarget.target_id.in_(grade_ids)))

        return filters

    async def list_for_student(
        self,
        *,
        student_id: str,
        batch_id: str | None,
        class_level: str | int | None,
        stream: str | None,
        subject_id: str | None,
        due_from: date | None,
        due_to: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Homework], int]:
        now = datetime.now(UTC)
        filters = [
            *self._visibility_filters(now),
            or_(
                *self._target_filters(
                    student_id=student_id,
                    batch_id=batch_id,
                    class_level=class_level,
                    stream=stream,
                )
            ),
            *self._due_window_filters(due_from, due_to),
        ]

        if subject_id:
            filters.append(Homework.subject_id == subject_id)

        base = (
            select(Homework)
            .join(HomeworkTarget, HomeworkTarget.homework_id == Homework.id)
            .where(*filters)
            .distinct()
        )

        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

        rows = (
            await self.session.execute(
                base.order_by(Homework.due_at.asc(), Homework.due_date.asc(), Homework.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()
        return rows, total

    async def list_for_student_with_read(
        self,
        *,
        user_id: str,
        student_id: str,
        batch_id: str | None,
        class_level: str | int | None,
        stream: str | None,
        subject_id: str | None,
        due_from: date | None,
        due_to: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[Homework, bool]], int]:
        now = datetime.now(UTC)
        filters = [
            *self._visibility_filters(now),
            or_(
                *self._target_filters(
                    student_id=student_id,
                    batch_id=batch_id,
                    class_level=class_level,
                    stream=stream,
                )
            ),
            *self._due_window_filters(due_from, due_to),
        ]

        if subject_id:
            filters.append(Homework.subject_id == subject_id)

        base = (
            select(Homework, HomeworkRead.id.is_not(None).label("is_read"))
            .join(HomeworkTarget, HomeworkTarget.homework_id == Homework.id)
            .outerjoin(
                HomeworkRead,
                and_(
                    HomeworkRead.homework_id == Homework.id,
                    HomeworkRead.user_id == user_id,
                ),
            )
            .where(*filters)
            .distinct()
        )

        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

        rows = (
            await self.session.execute(
                base.order_by(Homework.due_at.asc(), Homework.due_date.asc(), Homework.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return [(row[0], bool(row[1])) for row in rows], total

    async def get_for_student_with_read(
        self,
        *,
        homework_id: str,
        user_id: str,
        student_id: str,
        batch_id: str | None,
        class_level: str | int | None,
        stream: str | None,
    ) -> tuple[Homework | None, bool]:
        now = datetime.now(UTC)
        filters = [
            Homework.id == homework_id,
            *self._visibility_filters(now),
            or_(
                *self._target_filters(
                    student_id=student_id,
                    batch_id=batch_id,
                    class_level=class_level,
                    stream=stream,
                )
            ),
        ]

        row = (
            await self.session.execute(
                select(Homework, HomeworkRead.id.is_not(None).label("is_read"))
                .join(HomeworkTarget, HomeworkTarget.homework_id == Homework.id)
                .outerjoin(
                    HomeworkRead,
                    and_(
                        HomeworkRead.homework_id == Homework.id,
                        HomeworkRead.user_id == user_id,
                    ),
                )
                .where(*filters)
                .limit(1)
            )
        ).first()

        if not row:
            return None, False
        return row[0], bool(row[1])

    async def list_attachments_for_homework_ids(self, *, homework_ids: list[str]) -> dict[str, list[HomeworkAttachment]]:
        if not homework_ids:
            return {}

        rows = (
            await self.session.execute(
                select(HomeworkAttachment)
                .where(HomeworkAttachment.homework_id.in_(homework_ids))
                .order_by(HomeworkAttachment.created_at.asc())
            )
        ).scalars().all()

        mapped: dict[str, list[HomeworkAttachment]] = {homework_id: [] for homework_id in homework_ids}
        for row in rows:
            mapped.setdefault(row.homework_id, []).append(row)
        return mapped

    async def list_attachments_for_homework(self, *, homework_id: str) -> list[HomeworkAttachment]:
        return (
            await self.session.execute(
                select(HomeworkAttachment)
                .where(HomeworkAttachment.homework_id == homework_id)
                .order_by(HomeworkAttachment.created_at.asc())
            )
        ).scalars().all()

    async def list_submissions_for_student_homework_ids(
        self,
        *,
        student_id: str,
        homework_ids: list[str],
    ) -> dict[str, HomeworkSubmission]:
        if not homework_ids:
            return {}

        rows = (
            await self.session.execute(
                select(HomeworkSubmission)
                .where(
                    HomeworkSubmission.student_id == student_id,
                    HomeworkSubmission.homework_id.in_(homework_ids),
                )
                .order_by(HomeworkSubmission.submitted_at.desc())
            )
        ).scalars().all()

        mapped: dict[str, HomeworkSubmission] = {}
        for row in rows:
            mapped[row.homework_id] = row
        return mapped

    async def list_submission_attachments_for_submission_ids(
        self,
        *,
        submission_ids: list[str],
    ) -> dict[str, list[HomeworkSubmissionAttachment]]:
        if not submission_ids:
            return {}

        rows = (
            await self.session.execute(
                select(HomeworkSubmissionAttachment)
                .where(HomeworkSubmissionAttachment.submission_id.in_(submission_ids))
                .order_by(HomeworkSubmissionAttachment.created_at.asc())
            )
        ).scalars().all()

        mapped: dict[str, list[HomeworkSubmissionAttachment]] = {
            submission_id: [] for submission_id in submission_ids
        }
        for row in rows:
            mapped.setdefault(row.submission_id, []).append(row)
        return mapped

    async def get_submission_for_student(
        self,
        *,
        homework_id: str,
        student_id: str,
    ) -> HomeworkSubmission | None:
        return (
            await self.session.execute(
                select(HomeworkSubmission).where(
                    HomeworkSubmission.homework_id == homework_id,
                    HomeworkSubmission.student_id == student_id,
                )
            )
        ).scalars().first()

    async def list_submission_attachments(
        self,
        *,
        submission_id: str,
    ) -> list[HomeworkSubmissionAttachment]:
        return (
            await self.session.execute(
                select(HomeworkSubmissionAttachment)
                .where(HomeworkSubmissionAttachment.submission_id == submission_id)
                .order_by(HomeworkSubmissionAttachment.created_at.asc())
            )
        ).scalars().all()

    async def upsert_submission(
        self,
        *,
        homework_id: str,
        student_id: str,
        submitted_by_user_id: str,
        submitted_at: datetime,
        status: HomeworkSubmissionStatus,
        notes: str | None,
    ) -> HomeworkSubmission:
        submission = await self.get_submission_for_student(
            homework_id=homework_id,
            student_id=student_id,
        )

        if submission is None:
            submission = HomeworkSubmission(
                homework_id=homework_id,
                student_id=student_id,
                submitted_by_user_id=submitted_by_user_id,
                submitted_at=submitted_at,
                status=status,
                notes=notes,
            )
            self.session.add(submission)
            await self.session.flush()
            return submission

        submission.submitted_by_user_id = submitted_by_user_id
        submission.submitted_at = submitted_at
        submission.status = status
        submission.notes = notes
        await self.session.flush()
        return submission

    async def clear_submission_attachments(self, *, submission_id: str) -> None:
        rows = (
            await self.session.execute(
                select(HomeworkSubmissionAttachment).where(
                    HomeworkSubmissionAttachment.submission_id == submission_id
                )
            )
        ).scalars().all()

        for row in rows:
            await self.session.delete(row)

    async def add_submission_attachment(
        self,
        *,
        submission_id: str,
        file_name: str,
        storage_path: str,
        file_url: str,
        content_type: str,
        file_size_bytes: int,
    ) -> HomeworkSubmissionAttachment:
        attachment = HomeworkSubmissionAttachment(
            submission_id=submission_id,
            file_name=file_name,
            storage_path=storage_path,
            file_url=file_url,
            content_type=content_type,
            file_size_bytes=file_size_bytes,
        )
        self.session.add(attachment)
        await self.session.flush()
        return attachment

    async def mark_visible_read_for_student(
        self,
        *,
        user_id: str,
        student_id: str,
        batch_id: str | None,
        class_level: str | int | None,
        stream: str | None,
    ) -> int:
        now = datetime.now(UTC)
        filters = [
            *self._visibility_filters(now),
            or_(
                *self._target_filters(
                    student_id=student_id,
                    batch_id=batch_id,
                    class_level=class_level,
                    stream=stream,
                )
            ),
            HomeworkRead.id.is_(None),
        ]

        homework_ids = [
            row[0]
            for row in (
                await self.session.execute(
                    select(Homework.id)
                    .join(HomeworkTarget, HomeworkTarget.homework_id == Homework.id)
                    .outerjoin(
                        HomeworkRead,
                        and_(HomeworkRead.homework_id == Homework.id, HomeworkRead.user_id == user_id),
                    )
                    .where(*filters)
                    .distinct()
                )
            ).all()
        ]

        if not homework_ids:
            return 0

        for homework_id in homework_ids:
            self.session.add(
                HomeworkRead(
                    homework_id=homework_id,
                    user_id=user_id,
                    read_at=now,
                )
            )

        return len(homework_ids)

    async def pending_count_for_student(
        self,
        *,
        student_id: str,
        batch_id: str | None,
        class_level: str | int | None = None,
        stream: str | None = None,
    ) -> int:
        now = datetime.now(UTC)
        stmt = (
            select(func.count())
            .select_from(Homework)
            .join(HomeworkTarget, HomeworkTarget.homework_id == Homework.id)
            .where(
                *self._visibility_filters(now),
                or_(
                    *self._target_filters(
                        student_id=student_id,
                        batch_id=batch_id,
                        class_level=class_level,
                        stream=stream,
                    )
                ),
            )
            .distinct()
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def unseen_count_for_student(
        self,
        *,
        user_id: str,
        student_id: str,
        batch_id: str | None,
        class_level: str | int | None,
        stream: str | None,
    ) -> int:
        now = datetime.now(UTC)
        stmt = (
            select(func.count())
            .select_from(Homework)
            .join(HomeworkTarget, HomeworkTarget.homework_id == Homework.id)
            .outerjoin(
                HomeworkRead,
                and_(HomeworkRead.homework_id == Homework.id, HomeworkRead.user_id == user_id),
            )
            .where(
                *self._visibility_filters(now),
                or_(
                    *self._target_filters(
                        student_id=student_id,
                        batch_id=batch_id,
                        class_level=class_level,
                        stream=stream,
                    )
                ),
                HomeworkRead.id.is_(None),
            )
            .distinct()
        )
        return (await self.session.execute(stmt)).scalar_one()
