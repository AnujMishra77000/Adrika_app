from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundException
from app.core.security import get_password_hash
from app.db.models.academic import StudentProfile, TeacherProfile
from app.db.models.enums import NotificationType, RoleCode, UserStatus
from app.db.models.notification import Notification
from app.db.models.user import Role, User, UserRole
from app.repositories.registration_repo import RegistrationRepository
from app.repositories.user_repo import UserRepository
from app.schemas.registration import (
    RegistrationResponseDTO,
    StudentRegistrationDTO,
    TeacherRegistrationDTO,
)


class RegistrationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self.user_repo = UserRepository(session)
        self.registration_repo = RegistrationRepository(session)

    async def register_student(
        self,
        *,
        payload: StudentRegistrationDTO,
        photo: UploadFile | None,
    ) -> RegistrationResponseDTO:
        await self._assert_phone_available(phone=payload.contact_number)
        student_role = await self._get_role(RoleCode.STUDENT)

        photo_url = await self._store_photo(photo=photo, role_folder="students")

        user = User(
            full_name=payload.name.strip(),
            phone=payload.contact_number,
            password_hash=get_password_hash(payload.password),
            status=UserStatus.INACTIVE,
        )
        self.session.add(user)
        await self.session.flush()

        self.session.add(UserRole(user_id=user.id, role_id=student_role.id))

        suffix = uuid4().hex[:8].upper()
        self.session.add(
            StudentProfile(
                user_id=user.id,
                admission_no=f"REG-{suffix}",
                roll_no="PENDING",
                current_batch_id=None,
                class_name=payload.class_name.strip(),
                stream=payload.stream,
                parent_contact_number=payload.parent_contact_number,
                address=payload.address.strip(),
                school_details=payload.school_details.strip(),
                photo_url=photo_url,
            )
        )

        request = await self.registration_repo.create(
            user_id=user.id,
            requested_role=RoleCode.STUDENT,
        )

        await self._notify_admins(
            title="New student registration pending approval",
            body=f"{payload.name.strip()} ({payload.contact_number}) requested student access.",
            metadata={
                "request_id": request.id,
                "requested_role": "student",
                "contact_number": payload.contact_number,
            },
        )

        await self.session.commit()

        return RegistrationResponseDTO(
            request_id=request.id,
            user_id=user.id,
            status=request.status.value,
            message="Registration submitted. Admin approval is required before login.",
        )

    async def register_teacher(
        self,
        *,
        payload: TeacherRegistrationDTO,
        photo: UploadFile | None,
    ) -> RegistrationResponseDTO:
        await self._assert_phone_available(phone=payload.contact_number)
        teacher_role = await self._get_role(RoleCode.TEACHER)

        photo_url = await self._store_photo(photo=photo, role_folder="teachers")

        user = User(
            full_name=payload.name.strip(),
            phone=payload.contact_number,
            password_hash=get_password_hash(payload.password),
            status=UserStatus.INACTIVE,
        )
        self.session.add(user)
        await self.session.flush()

        self.session.add(UserRole(user_id=user.id, role_id=teacher_role.id))

        suffix = uuid4().hex[:8].upper()
        self.session.add(
            TeacherProfile(
                user_id=user.id,
                employee_code=f"TREG-{suffix}",
                designation="Pending Approval",
                age=payload.age,
                gender=payload.gender,
                qualification=payload.qualification.strip(),
                specialization=payload.specialization.strip(),
                school_college=payload.school_college.strip() if payload.school_college else None,
                address=payload.address.strip(),
                photo_url=photo_url,
            )
        )

        request = await self.registration_repo.create(
            user_id=user.id,
            requested_role=RoleCode.TEACHER,
        )

        await self._notify_admins(
            title="New teacher registration pending approval",
            body=f"{payload.name.strip()} ({payload.contact_number}) requested teacher access.",
            metadata={
                "request_id": request.id,
                "requested_role": "teacher",
                "contact_number": payload.contact_number,
            },
        )

        await self.session.commit()

        return RegistrationResponseDTO(
            request_id=request.id,
            user_id=user.id,
            status=request.status.value,
            message="Registration submitted. Admin approval is required before login.",
        )

    async def _assert_phone_available(self, *, phone: str) -> None:
        existing = await self.user_repo.get_by_identifier(phone)
        if existing:
            raise ValueError("A user with this contact number already exists")

    async def _get_role(self, role: RoleCode) -> Role:
        stmt: Select[tuple[Role]] = select(Role).where(Role.code == role)
        role_row = (await self.session.execute(stmt)).scalar_one_or_none()
        if not role_row:
            raise NotFoundException(f"Role not configured: {role.value}")
        return role_row

    async def _notify_admins(self, *, title: str, body: str, metadata: dict) -> None:
        rows = (
            await self.session.execute(
                select(User.id)
                .join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id)
                .where(Role.code == RoleCode.ADMIN, User.status == UserStatus.ACTIVE)
                .distinct()
            )
        ).scalars().all()

        for user_id in rows:
            self.session.add(
                Notification(
                    recipient_user_id=user_id,
                    notification_type=NotificationType.SYSTEM,
                    title=title,
                    body=body,
                    metadata_json=metadata,
                    is_read=False,
                )
            )

    async def _store_photo(self, *, photo: UploadFile | None, role_folder: str) -> str | None:
        if photo is None:
            return None

        allowed_types = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }
        content_type = (photo.content_type or "").lower().strip()
        if content_type not in allowed_types:
            raise ValueError("Only JPG, PNG, or WEBP images are allowed")

        content = await photo.read()
        if not content:
            raise ValueError("Uploaded photo is empty")

        max_bytes = 5 * 1024 * 1024
        if len(content) > max_bytes:
            raise ValueError("Uploaded photo must be 5MB or smaller")

        media_root = Path(self.settings.media_base_dir).expanduser().resolve()
        destination_dir = media_root / "registrations" / role_folder
        destination_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid4().hex}{allowed_types[content_type]}"
        destination_path = destination_dir / filename
        destination_path.write_bytes(content)

        base_url = self.settings.media_base_url.strip() or "/media"
        if not base_url.startswith("/"):
            base_url = f"/{base_url}"

        return f"{base_url}/registrations/{role_folder}/{filename}"
