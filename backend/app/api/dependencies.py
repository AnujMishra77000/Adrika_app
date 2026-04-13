from collections.abc import Callable

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.db.models.user import User
from app.db.session import get_db_session
from app.repositories.parent_repo import ParentRepository
from app.repositories.student_repo import StudentRepository
from app.repositories.teacher_repo import TeacherRepository
from app.repositories.user_repo import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise UnauthorizedException("Invalid access token") from exc

    if payload.get("typ") != "access":
        raise UnauthorizedException("Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token payload")

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        raise UnauthorizedException("User not found")

    user_status = user.status.value if hasattr(user.status, "value") else str(user.status)
    if user_status != "active":
        raise UnauthorizedException("Account is inactive. Please contact admin")

    return user


def require_roles(*allowed: str) -> Callable:
    async def _inner(user: User = Depends(get_current_user)) -> User:
        role_codes = {role.code.value if hasattr(role.code, "value") else str(role.code) for role in user.roles}
        if not role_codes.intersection(set(allowed)):
            raise ForbiddenException("Insufficient role permissions")
        return user

    return _inner


async def get_current_student_profile(
    user: User = Depends(require_roles("student")),
    session: AsyncSession = Depends(get_db_session),
):
    profile = await StudentRepository(session).get_profile_by_user_id(user.id)
    if not profile:
        raise ForbiddenException("Student profile not found")
    return profile


async def get_current_teacher_profile(
    user: User = Depends(require_roles("teacher")),
    session: AsyncSession = Depends(get_db_session),
):
    profile = await TeacherRepository(session).get_profile_by_user_id(user_id=user.id)
    if not profile:
        raise ForbiddenException("Teacher profile not found")
    return profile


async def get_current_parent_profile(
    user: User = Depends(require_roles("parent")),
    session: AsyncSession = Depends(get_db_session),
):
    profile = await ParentRepository(session).get_profile_by_user_id(user_id=user.id)
    if not profile:
        raise ForbiddenException("Parent profile not found")
    return profile
