from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedException
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.db.models.enums import RegistrationRequestStatus, UserStatus
from app.repositories.registration_repo import RegistrationRepository
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginResponseDTO, TokenPairDTO


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.registration_repo = RegistrationRepository(session)
        self.settings = get_settings()

    async def login(self, *, identifier: str, password: str, device_id: str) -> LoginResponseDTO:
        user = await self.user_repo.get_by_identifier(identifier)
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedException("Invalid credentials")

        if user.status != UserStatus.ACTIVE:
            request = await self.registration_repo.get_by_user_id(user_id=user.id)
            if request and request.status == RegistrationRequestStatus.PENDING:
                raise UnauthorizedException("Your registration is pending admin approval")
            if request and request.status == RegistrationRequestStatus.REJECTED:
                raise UnauthorizedException("Your registration was rejected. Please contact admin")
            raise UnauthorizedException("Account is inactive. Please contact admin")

        role_codes = self.user_repo.user_role_codes(user)
        session_id = str(uuid4())
        refresh_token = create_refresh_token(subject=user.id, session_id=session_id)

        await self.user_repo.create_refresh_session(
            user_id=user.id,
            device_id=device_id,
            refresh_token=refresh_token,
            expires_at=datetime.now(UTC) + timedelta(days=self.settings.refresh_token_expire_days),
            session_id=session_id,
        )

        access_token = create_access_token(subject=user.id, roles=role_codes)
        user.last_login_at = datetime.now(UTC)
        await self.session.commit()

        return LoginResponseDTO(
            tokens=TokenPairDTO(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=self.settings.access_token_expire_minutes * 60,
            ),
            user={
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "status": user.status.value if hasattr(user.status, "value") else str(user.status),
                "roles": role_codes,
            },
        )

    async def refresh(self, *, refresh_token: str) -> TokenPairDTO:
        payload = decode_token(refresh_token)
        if payload.get("typ") != "refresh":
            raise UnauthorizedException("Invalid refresh token type")

        user_id = payload.get("sub")
        session_id = payload.get("sid")
        if not user_id or not session_id:
            raise UnauthorizedException("Invalid refresh token payload")

        session = await self.user_repo.get_valid_refresh_session(session_id=session_id, refresh_token=refresh_token)
        if not session:
            raise UnauthorizedException("Refresh session expired or revoked")

        user = await self.user_repo.get_by_id(user_id)
        if not user or user.status != UserStatus.ACTIVE:
            raise UnauthorizedException("User not found or inactive")

        role_codes = self.user_repo.user_role_codes(user)
        await self.user_repo.revoke_session(session_id)

        new_session_id = str(uuid4())
        new_refresh_token = create_refresh_token(subject=user.id, session_id=new_session_id)
        await self.user_repo.create_refresh_session(
            user_id=user.id,
            device_id=session.device_id,
            refresh_token=new_refresh_token,
            expires_at=datetime.now(UTC) + timedelta(days=self.settings.refresh_token_expire_days),
            session_id=new_session_id,
        )

        access_token = create_access_token(subject=user.id, roles=role_codes)
        await self.session.commit()

        return TokenPairDTO(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=self.settings.access_token_expire_minutes * 60,
        )

    async def logout(self, *, refresh_token: str) -> None:
        payload = decode_token(refresh_token)
        session_id = payload.get("sid")
        if session_id:
            await self.user_repo.revoke_session(session_id)
            await self.session.commit()

    async def logout_all(self, *, user_id: str) -> None:
        await self.user_repo.revoke_all_sessions_for_user(user_id)
        await self.session.commit()
