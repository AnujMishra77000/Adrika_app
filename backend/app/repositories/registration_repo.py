from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.academic import StudentProfile, TeacherProfile
from app.db.models.enums import RegistrationRequestStatus, RoleCode
from app.db.models.registration import RegistrationRequest
from app.db.models.user import User


class RegistrationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, *, request_id: str) -> RegistrationRequest | None:
        return await self.session.get(RegistrationRequest, request_id)

    async def get_by_user_id(self, *, user_id: str) -> RegistrationRequest | None:
        result = await self.session.execute(
            select(RegistrationRequest).where(RegistrationRequest.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: str,
        requested_role: RoleCode,
    ) -> RegistrationRequest:
        request = RegistrationRequest(
            user_id=user_id,
            requested_role=requested_role,
            status=RegistrationRequestStatus.PENDING,
        )
        self.session.add(request)
        await self.session.flush()
        return request

    async def list_requests(
        self,
        *,
        status: RegistrationRequestStatus,
        role: RoleCode | None,
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[RegistrationRequest, User, StudentProfile | None, TeacherProfile | None]], int]:
        filters = [RegistrationRequest.status == status]
        if role is not None:
            filters.append(RegistrationRequest.requested_role == role)

        base = (
            select(RegistrationRequest, User, StudentProfile, TeacherProfile)
            .join(User, User.id == RegistrationRequest.user_id)
            .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
            .outerjoin(TeacherProfile, TeacherProfile.user_id == User.id)
            .where(and_(*filters))
        )

        total = (
            await self.session.execute(
                select(func.count()).select_from(base.subquery())
            )
        ).scalar_one()

        rows = (
            await self.session.execute(
                base.order_by(RegistrationRequest.created_at.asc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return rows, total

    async def decide(
        self,
        *,
        request: RegistrationRequest,
        status: RegistrationRequestStatus,
        reviewed_by_user_id: str,
        note: str | None,
    ) -> RegistrationRequest:
        request.status = status
        request.reviewed_by_user_id = reviewed_by_user_id
        request.reviewed_at = datetime.now(UTC)
        request.decision_note = note
        await self.session.flush()
        return request
