from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.billing import FeeInvoice, PaymentTransaction
from app.db.models.parent import ParentCommunicationPreference, ParentProfile, ParentStudentLink


class ParentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_profile_by_user_id(self, *, user_id: str) -> ParentProfile | None:
        result = await self.session.execute(select(ParentProfile).where(ParentProfile.user_id == user_id))
        return result.scalar_one_or_none()

    async def list_student_links(self, *, parent_id: str) -> list[ParentStudentLink]:
        rows = (
            await self.session.execute(
                select(ParentStudentLink)
                .where(ParentStudentLink.parent_id == parent_id, ParentStudentLink.is_active.is_(True))
                .order_by(ParentStudentLink.is_primary.desc(), ParentStudentLink.created_at.asc())
            )
        ).scalars().all()
        return rows

    async def linked_student_ids(self, *, parent_id: str) -> list[str]:
        rows = (
            await self.session.execute(
                select(ParentStudentLink.student_id)
                .where(ParentStudentLink.parent_id == parent_id, ParentStudentLink.is_active.is_(True))
                .order_by(ParentStudentLink.is_primary.desc(), ParentStudentLink.created_at.asc())
            )
        ).scalars().all()
        return rows

    async def is_student_linked(self, *, parent_id: str, student_id: str) -> bool:
        row = await self.session.execute(
            select(ParentStudentLink.id).where(
                ParentStudentLink.parent_id == parent_id,
                ParentStudentLink.student_id == student_id,
                ParentStudentLink.is_active.is_(True),
            )
        )
        return row.scalar_one_or_none() is not None

    async def get_preferences(self, *, parent_id: str) -> ParentCommunicationPreference | None:
        row = await self.session.execute(
            select(ParentCommunicationPreference).where(ParentCommunicationPreference.parent_id == parent_id)
        )
        return row.scalar_one_or_none()

    async def upsert_preferences(
        self,
        *,
        parent_id: str,
        in_app_enabled: bool,
        push_enabled: bool,
        whatsapp_enabled: bool,
        fee_reminders_enabled: bool,
        preferred_language: str,
    ) -> ParentCommunicationPreference:
        existing = await self.get_preferences(parent_id=parent_id)
        if existing:
            existing.in_app_enabled = in_app_enabled
            existing.push_enabled = push_enabled
            existing.whatsapp_enabled = whatsapp_enabled
            existing.fee_reminders_enabled = fee_reminders_enabled
            existing.preferred_language = preferred_language
            await self.session.flush()
            return existing

        created = ParentCommunicationPreference(
            parent_id=parent_id,
            in_app_enabled=in_app_enabled,
            push_enabled=push_enabled,
            whatsapp_enabled=whatsapp_enabled,
            fee_reminders_enabled=fee_reminders_enabled,
            preferred_language=preferred_language,
        )
        self.session.add(created)
        await self.session.flush()
        return created

    async def list_fee_invoices(
        self,
        *,
        student_id: str,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[FeeInvoice], int]:
        filters = [FeeInvoice.student_id == student_id]
        if status:
            filters.append(FeeInvoice.status == status)

        base = select(FeeInvoice).where(*filters)
        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (
            await self.session.execute(base.order_by(FeeInvoice.due_date.desc()).limit(limit).offset(offset))
        ).scalars().all()
        return rows, total

    async def pending_fee_count(self, *, student_id: str) -> int:
        stmt = select(func.count()).where(FeeInvoice.student_id == student_id, FeeInvoice.status == "pending")
        return (await self.session.execute(stmt)).scalar_one()

    async def list_payment_transactions(
        self,
        *,
        student_id: str,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[PaymentTransaction], int]:
        filters = [PaymentTransaction.student_id == student_id]
        if status:
            filters.append(PaymentTransaction.status == status)

        base = select(PaymentTransaction).where(*filters)
        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (
            await self.session.execute(base.order_by(PaymentTransaction.created_at.desc()).limit(limit).offset(offset))
        ).scalars().all()
        return rows, total
