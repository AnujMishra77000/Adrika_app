from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.schemas.auth import LoginRequestDTO, LoginResponseDTO, RefreshRequestDTO, TokenPairDTO
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponseDTO)
async def login(payload: LoginRequestDTO, session: AsyncSession = Depends(get_db_session)) -> LoginResponseDTO:
    service = AuthService(session)
    return await service.login(
        identifier=payload.identifier,
        password=payload.password,
        device_id=payload.device.device_id,
    )


@router.post("/refresh", response_model=TokenPairDTO)
async def refresh(payload: RefreshRequestDTO, session: AsyncSession = Depends(get_db_session)) -> TokenPairDTO:
    return await AuthService(session).refresh(refresh_token=payload.refresh_token)


@router.post("/logout")
async def logout(payload: RefreshRequestDTO, session: AsyncSession = Depends(get_db_session)) -> dict:
    await AuthService(session).logout(refresh_token=payload.refresh_token)
    return {"message": "Logged out"}


@router.post("/logout-all")
async def logout_all(
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    await AuthService(session).logout_all(user_id=current_user.id)
    return {"message": "All sessions revoked"}


@router.get("/me")
async def me(current_user=Depends(get_current_user)) -> dict:
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "roles": [role.code.value if hasattr(role.code, "value") else str(role.code) for role in current_user.roles],
    }
