import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.db.models.academic import StudentProfile, TeacherProfile
from app.db.models.audit import AuditLog
from app.db.models.enums import NotificationType, RegistrationRequestStatus, RoleCode, UserStatus
from app.db.models.notification import Notification
from app.db.models.user import User
from app.repositories.registration_repo import RegistrationRepository


class RegistrationReviewService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RegistrationRepository(session)

    async def list_requests(
        self,
        *,
        status: str,
        role: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        status_value = RegistrationRequestStatus(status)

        role_value: RoleCode | None = None
        if role != "all":
            role_value = RoleCode(role)

        rows, total = await self.repo.list_requests(
            status=status_value,
            role=role_value,
            limit=limit,
            offset=offset,
        )

        items: list[dict] = []
        for request, user, student_profile, teacher_profile in rows:
            item = {
                "request_id": request.id,
                "status": request.status.value,
                "requested_role": request.requested_role.value,
                "submitted_at": request.created_at,
                "reviewed_at": request.reviewed_at,
                "decision_note": request.decision_note,
                "user": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "phone": user.phone,
                    "email": user.email,
                    "status": user.status.value if hasattr(user.status, "value") else str(user.status),
                },
            }
            if request.requested_role == RoleCode.STUDENT and student_profile is not None:
                item["student_profile"] = {
                    "class_name": student_profile.class_name,
                    "stream": student_profile.stream,
                    "parent_contact_number": student_profile.parent_contact_number,
                    "address": student_profile.address,
                    "school_details": student_profile.school_details,
                    "photo_url": student_profile.photo_url,
                }
            if request.requested_role == RoleCode.TEACHER and teacher_profile is not None:
                item["teacher_profile"] = {
                    "age": teacher_profile.age,
                    "gender": teacher_profile.gender,
                    "qualification": teacher_profile.qualification,
                    "specialization": teacher_profile.specialization,
                    "school_college": teacher_profile.school_college,
                    "address": teacher_profile.address,
                    "photo_url": teacher_profile.photo_url,
                }
            items.append(item)

        return items, total

    async def decide_request(
        self,
        *,
        request_id: str,
        status: str,
        note: str | None,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        request = await self.repo.get_by_id(request_id=request_id)
        if not request:
            raise NotFoundException("Registration request not found")

        user = await self.session.get(User, request.user_id)
        if not user:
            raise NotFoundException("User not found")

        if request.status != RegistrationRequestStatus.PENDING:
            raise ValueError("Registration request is already processed")

        before = {
            "request_status": request.status.value,
            "user_status": user.status.value if hasattr(user.status, "value") else str(user.status),
        }

        if status == "approved":
            request_status = RegistrationRequestStatus.APPROVED
            user_status = UserStatus.ACTIVE
            notification_title = "Registration approved"
            notification_body = "Your account has been approved. You can now login using your contact number and password."
            audit_action = "admin.registration.approve"
        else:
            request_status = RegistrationRequestStatus.REJECTED
            user_status = UserStatus.INACTIVE
            notification_title = "Registration rejected"
            notification_body = "Your registration was not approved. Please contact institute administration."
            audit_action = "admin.registration.reject"

        await self.repo.decide(
            request=request,
            status=request_status,
            reviewed_by_user_id=actor_user_id,
            note=note,
        )
        user.status = user_status

        self.session.add(
            Notification(
                recipient_user_id=user.id,
                notification_type=NotificationType.SYSTEM,
                title=notification_title,
                body=notification_body,
                metadata_json={
                    "request_id": request.id,
                    "status": request_status.value,
                },
                is_read=False,
            )
        )

        self.session.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action=audit_action,
                entity_type="registration_request",
                entity_id=request.id,
                before_state=json.dumps(before, default=str),
                after_state=json.dumps(
                    {
                        "request_status": request_status.value,
                        "user_status": user_status.value,
                        "note": note,
                    },
                    default=str,
                ),
                ip_address=ip_address,
                created_at=datetime.now(UTC),
            )
        )

        await self.session.commit()

        return {
            "request_id": request.id,
            "status": request.status.value,
            "user_id": user.id,
            "user_status": user.status.value if hasattr(user.status, "value") else str(user.status),
            "reviewed_at": request.reviewed_at,
            "note": request.decision_note,
        }
