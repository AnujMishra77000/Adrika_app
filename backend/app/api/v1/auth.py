from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.db.session import get_db_session
from app.schemas.auth import (
    ForgotPasswordResetRequestDTO,
    LoginRequestDTO,
    LoginResponseDTO,
    RefreshRequestDTO,
    TokenPairDTO,
)
from app.schemas.registration import RegistrationResponseDTO, TeacherRegistrationDTO
from app.services.auth_service import AuthService
from app.services.registration_service import RegistrationService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _set_access_token_cookie(response: Response, access_token: str) -> None:
    response.set_cookie(
        key=settings.access_token_cookie_name,
        value=access_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


def _clear_access_token_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.access_token_cookie_name,
        path="/",
        secure=settings.is_production,
        samesite="lax",
    )


@router.post("/login", response_model=LoginResponseDTO)
async def login(
    payload: LoginRequestDTO,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> LoginResponseDTO:
    service = AuthService(session)
    result = await service.login(
        identifier=payload.identifier,
        password=payload.password,
        device_id=payload.device.device_id,
    )
    _set_access_token_cookie(response, result.tokens.access_token)
    return result


@router.post("/register/student", response_model=RegistrationResponseDTO, status_code=status.HTTP_201_CREATED)
async def register_student() -> RegistrationResponseDTO:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Student self-registration is disabled. Please contact admin for your login credentials.",
    )


@router.post("/register/teacher", response_model=RegistrationResponseDTO, status_code=status.HTTP_201_CREATED)
async def register_teacher() -> RegistrationResponseDTO:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Teacher self-registration is disabled. Please contact admin for your login credentials.",
    )


@router.post("/forgot-password/reset")
async def forgot_password_reset(
    payload: ForgotPasswordResetRequestDTO,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    return await AuthService(session).reset_password_by_phone(
        phone=payload.phone,
        new_password=payload.new_password,
        role=payload.role,
    )


@router.post("/refresh", response_model=TokenPairDTO)
async def refresh(
    payload: RefreshRequestDTO,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> TokenPairDTO:
    result = await AuthService(session).refresh(refresh_token=payload.refresh_token)
    _set_access_token_cookie(response, result.access_token)
    return result


@router.post("/logout")
async def logout(
    payload: RefreshRequestDTO,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    await AuthService(session).logout(refresh_token=payload.refresh_token)
    _clear_access_token_cookie(response)
    return {"message": "Logged out"}


@router.post("/logout-all")
async def logout_all(
    response: Response,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    await AuthService(session).logout_all(user_id=current_user.id)
    _clear_access_token_cookie(response)
    return {"message": "All sessions revoked"}


@router.get("/me")
async def me(current_user=Depends(get_current_user)) -> dict:
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "status": current_user.status.value if hasattr(current_user.status, "value") else str(current_user.status),
        "roles": [role.code.value if hasattr(role.code, "value") else str(role.code) for role in current_user.roles],
    }
