from datetime import UTC, datetime

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.academic import StudentProfile
from app.db.models.suggestion import SuggestionMessage, SuggestionThread
from app.db.models.user import Role, User, UserRole
from app.db.models.enums import RoleCode, UserStatus


class SuggestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_thread_for_student(self, *, student_id: str) -> SuggestionThread | None:
        return (
            await self.session.execute(
                select(SuggestionThread).where(SuggestionThread.student_id == student_id)
            )
        ).scalar_one_or_none()

    async def get_thread_by_id(self, *, thread_id: str) -> SuggestionThread | None:
        return (
            await self.session.execute(
                select(SuggestionThread).where(SuggestionThread.id == thread_id)
            )
        ).scalar_one_or_none()

    async def create_thread(self, *, student_id: str, student_user_id: str) -> SuggestionThread:
        row = SuggestionThread(
            student_id=student_id,
            student_user_id=student_user_id,
            status="open",
            last_message_at=None,
            admin_last_read_at=None,
            student_last_read_at=datetime.now(UTC),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_messages(self, *, thread_id: str, limit: int, offset: int) -> tuple[list[SuggestionMessage], int]:
        base = select(SuggestionMessage).where(SuggestionMessage.thread_id == thread_id)
        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                base.order_by(SuggestionMessage.created_at.asc()).limit(limit).offset(offset)
            )
        ).scalars().all()
        return rows, total

    async def add_message(self, *, thread_id: str, sender_user_id: str, message: str) -> SuggestionMessage:
        row = SuggestionMessage(
            thread_id=thread_id,
            sender_user_id=sender_user_id,
            message=message,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_admin_threads(self, *, search: str | None, limit: int, offset: int) -> tuple[list[tuple], int]:
        unread_expr = case(
            (
                and_(
                    SuggestionThread.last_sender_user_id == SuggestionThread.student_user_id,
                    or_(
                        SuggestionThread.admin_last_read_at.is_(None),
                        SuggestionThread.admin_last_read_at < SuggestionThread.last_message_at,
                    ),
                ),
                1,
            ),
            else_=0,
        )

        query = (
            select(
                SuggestionThread,
                StudentProfile,
                User,
                unread_expr.label("unread_for_admin"),
            )
            .join(StudentProfile, StudentProfile.id == SuggestionThread.student_id)
            .join(User, User.id == SuggestionThread.student_user_id)
            .order_by(
                SuggestionThread.last_message_at.desc().nullslast(),
                SuggestionThread.updated_at.desc(),
            )
        )

        if search:
            q = f"%{search.strip()}%"
            query = query.where(
                or_(
                    User.full_name.ilike(q),
                    User.phone.ilike(q),
                    StudentProfile.admission_no.ilike(q),
                )
            )

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (await self.session.execute(query.limit(limit).offset(offset))).all()
        return rows, total

    async def admin_unread_threads_count(self) -> int:
        stmt = select(func.count()).where(
            SuggestionThread.last_sender_user_id == SuggestionThread.student_user_id,
            or_(
                SuggestionThread.admin_last_read_at.is_(None),
                SuggestionThread.admin_last_read_at < SuggestionThread.last_message_at,
            ),
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def list_active_admin_user_ids(self) -> list[str]:
        rows = (
            await self.session.execute(
                select(User.id)
                .join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id)
                .where(Role.code == RoleCode.ADMIN, User.status == UserStatus.ACTIVE)
            )
        ).all()
        return [row[0] for row in rows]
