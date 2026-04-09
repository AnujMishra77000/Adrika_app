from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.schemas.auth import LoginRequestDTO, LoginResponseDTO, RefreshRequestDTO, TokenPairDTO
from app.schemas.registration import RegistrationResponseDTO, StudentRegistrationDTO, TeacherRegistrationDTO
from app.services.auth_service import AuthService
from app.services.registration_service import RegistrationService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponseDTO)
async def login(payload: LoginRequestDTO, session: AsyncSession = Depends(get_db_session)) -> LoginResponseDTO:
    service = AuthService(session)
    return await service.login(
        identifier=payload.identifier,
        password=payload.password,
        device_id=payload.device.device_id,
    )


@router.post("/register/student", response_model=RegistrationResponseDTO, status_code=status.HTTP_201_CREATED)
async def register_student(
    name: str = Form(...),
    class_name: str = Form(...),
    stream: str = Form(...),
    contact_number: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    parent_contact_number: str = Form(...),
    address: str = Form(...),
    school_details: str = Form(...),
    photo: UploadFile | None = File(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> RegistrationResponseDTO:
    payload = StudentRegistrationDTO(
        name=name,
        class_name=class_name,
        stream=stream,
        contact_number=contact_number,
        password=password,
        confirm_password=confirm_password,
        parent_contact_number=parent_contact_number,
        address=address,
        school_details=school_details,
    )
    return await RegistrationService(session).register_student(payload=payload, photo=photo)


@router.post("/register/teacher", response_model=RegistrationResponseDTO, status_code=status.HTTP_201_CREATED)
async def register_teacher(
    name: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
    qualification: str = Form(...),
    specialization: str = Form(...),
    school_college: str | None = Form(default=None),
    contact_number: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    address: str = Form(...),
    photo: UploadFile | None = File(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> RegistrationResponseDTO:
    payload = TeacherRegistrationDTO(
        name=name,
        age=age,
        gender=gender,
        qualification=qualification,
        specialization=specialization,
        school_college=school_college,
        contact_number=contact_number,
        password=password,
        confirm_password=confirm_password,
        address=address,
    )
    return await RegistrationService(session).register_teacher(payload=payload, photo=photo)


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
        "status": current_user.status.value if hasattr(current_user.status, "value") else str(current_user.status),
        "roles": [role.code.value if hasattr(role.code, "value") else str(role.code) for role in current_user.roles],
    }
