from datetime import UTC, datetime

from sqlalchemy import and_, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.content import Notice, NoticeRead, NoticeTarget
from app.db.models.enums import NoticeStatus


class NoticeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_student(
        self,
        *,
        user_id: str,
        student_id: str,
        batch_id: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[Notice, bool]], int]:
        now = datetime.now(UTC)
        target_clauses = [
            and_(NoticeTarget.target_type == "all", NoticeTarget.target_id == "all"),
            and_(NoticeTarget.target_type == "student", NoticeTarget.target_id == student_id),
        ]
        if batch_id:
            target_clauses.append(and_(NoticeTarget.target_type == "batch", NoticeTarget.target_id == batch_id))

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
    ) -> tuple[Notice | None, bool]:
        target_clauses = [
            and_(NoticeTarget.target_type == "all", NoticeTarget.target_id == "all"),
            and_(NoticeTarget.target_type == "student", NoticeTarget.target_id == student_id),
        ]
        if batch_id:
            target_clauses.append(and_(NoticeTarget.target_type == "batch", NoticeTarget.target_id == batch_id))

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

    async def mark_read(self, *, notice_id: str, user_id: str) -> None:
        existing = await self.session.execute(
            select(NoticeRead).where(NoticeRead.notice_id == notice_id, NoticeRead.user_id == user_id)
        )
        if existing.scalar_one_or_none():
            return
        self.session.add(NoticeRead(notice_id=notice_id, user_id=user_id, read_at=datetime.now(UTC)))
