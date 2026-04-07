from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import RefreshSession, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_identifier(self, identifier: str) -> User | None:
        stmt: Select[tuple[User]] = select(User).where((User.email == identifier) | (User.phone == identifier))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create_refresh_session(
        self,
        *,
        user_id: str,
        device_id: str,
        refresh_token: str,
        expires_at: datetime,
        session_id: str,
    ) -> RefreshSession:
        refresh = RefreshSession(
            id=session_id,
            user_id=user_id,
            device_id=device_id,
            refresh_token_hash=sha256(refresh_token.encode("utf-8")).hexdigest(),
            expires_at=expires_at,
        )
        self.session.add(refresh)
        await self.session.flush()
        return refresh

    async def get_valid_refresh_session(self, *, session_id: str, refresh_token: str) -> RefreshSession | None:
        token_hash = sha256(refresh_token.encode("utf-8")).hexdigest()
        stmt = select(RefreshSession).where(
            RefreshSession.id == session_id,
            RefreshSession.revoked_at.is_(None),
            RefreshSession.expires_at > datetime.now(UTC),
            RefreshSession.refresh_token_hash == token_hash,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_session(self, session_id: str) -> None:
        await self.session.execute(
            update(RefreshSession)
            .where(RefreshSession.id == session_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )

    async def revoke_all_sessions_for_user(self, user_id: str) -> None:
        await self.session.execute(
            update(RefreshSession)
            .where(RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )

    @staticmethod
    def user_role_codes(user: User) -> list[str]:
        return [role.code.value if hasattr(role.code, "value") else str(role.code) for role in user.roles]
