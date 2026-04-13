from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import and_, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.content import Notice, NoticeAttachment, NoticeRead, NoticeTarget
from app.db.models.enums import NoticeStatus


class NoticeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _grade_target_ids(*, class_level: int | None, stream: str | None) -> list[str]:
        if class_level not in {10, 11, 12}:
            return []

        target_ids = [str(class_level)]
        normalized_stream = (stream or "").strip().lower()
        if class_level in {11, 12} and normalized_stream in {"science", "commerce"}:
            target_ids.append(f"{class_level}:{normalized_stream}")
        return target_ids

    async def list_for_student(
        self,
        *,
        user_id: str,
        student_id: str,
        batch_id: str | None,
        class_level: int | None = None,
        stream: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[Notice, bool]], int]:
        now = datetime.now(UTC)
        target_clauses = [
            and_(NoticeTarget.target_type == "all", NoticeTarget.target_id == "all"),
            and_(NoticeTarget.target_type == "all_students", NoticeTarget.target_id == "all"),
            and_(NoticeTarget.target_type == "student", NoticeTarget.target_id == student_id),
        ]

        if batch_id:
            target_clauses.append(and_(NoticeTarget.target_type == "batch", NoticeTarget.target_id == batch_id))

        grade_targets = self._grade_target_ids(class_level=class_level, stream=stream)
        if grade_targets:
            target_clauses.append(
                and_(
                    NoticeTarget.target_type == "grade",
                    NoticeTarget.target_id.in_(grade_targets),
                )
            )

        base_stmt = (
            select(Notice)
            .join(NoticeTarget, NoticeTarget.notice_id == Notice.id)
            .where(
                Notice.status == NoticeStatus.PUBLISHED,
                or_(Notice.publish_at.is_(None), Notice.publish_at <= now),
                or_(*target_clauses),
            )
            .distinct()
        )

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        read_exists = (
            select(literal(True))
            .where(NoticeRead.notice_id == Notice.id, NoticeRead.user_id == user_id)
            .exists()
        )

        stmt = (
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
        rows = (await self.session.execute(stmt)).all()
        return rows, total

    async def get_notice_for_student(
        self,
        *,
        notice_id: str,
        user_id: str,
        student_id: str,
        batch_id: str | None,
        class_level: int | None = None,
        stream: str | None = None,
    ) -> tuple[Notice | None, bool]:
        target_clauses = [
            and_(NoticeTarget.target_type == "all", NoticeTarget.target_id == "all"),
            and_(NoticeTarget.target_type == "all_students", NoticeTarget.target_id == "all"),
            and_(NoticeTarget.target_type == "student", NoticeTarget.target_id == student_id),
        ]
        if batch_id:
            target_clauses.append(and_(NoticeTarget.target_type == "batch", NoticeTarget.target_id == batch_id))

        grade_targets = self._grade_target_ids(class_level=class_level, stream=stream)
        if grade_targets:
            target_clauses.append(
                and_(
                    NoticeTarget.target_type == "grade",
                    NoticeTarget.target_id.in_(grade_targets),
                )
            )

        read_exists = (
            select(literal(True))
            .where(NoticeRead.notice_id == Notice.id, NoticeRead.user_id == user_id)
            .exists()
        )

        stmt = (
            select(Notice, read_exists)
            .join(NoticeTarget, NoticeTarget.notice_id == Notice.id)
            .where(Notice.id == notice_id, or_(*target_clauses), Notice.status == NoticeStatus.PUBLISHED)
        )
        row = (await self.session.execute(stmt)).first()
        if not row:
            return None, False
        return row[0], bool(row[1])

    async def list_attachments_for_notice_ids(self, *, notice_ids: list[str]) -> dict[str, list[NoticeAttachment]]:
        if not notice_ids:
            return {}

        rows = (
            await self.session.execute(
                select(NoticeAttachment)
                .where(NoticeAttachment.notice_id.in_(notice_ids))
                .order_by(NoticeAttachment.created_at.desc())
            )
        ).scalars().all()

        mapping: dict[str, list[NoticeAttachment]] = defaultdict(list)
        for attachment in rows:
            mapping[attachment.notice_id].append(attachment)
        return dict(mapping)

    async def list_attachments_for_notice(self, *, notice_id: str) -> list[NoticeAttachment]:
        return (
            await self.session.execute(
                select(NoticeAttachment)
                .where(NoticeAttachment.notice_id == notice_id)
                .order_by(NoticeAttachment.created_at.desc())
            )
        ).scalars().all()

    async def mark_read(self, *, notice_id: str, user_id: str) -> None:
        existing = await self.session.execute(
            select(NoticeRead).where(NoticeRead.notice_id == notice_id, NoticeRead.user_id == user_id)
        )
        if existing.scalar_one_or_none():
            return
        self.session.add(NoticeRead(notice_id=notice_id, user_id=user_id, read_at=datetime.now(UTC)))
