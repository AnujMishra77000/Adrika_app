from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import DeliveryChannel, NotificationType
from app.db.models.notification import Notification, NotificationDelivery
from app.db.models.user import DeviceRegistration


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(
        self,
        *,
        user_id: str,
        is_read: bool | None,
        since_at: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Notification], int]:
        filters = [Notification.recipient_user_id == user_id]
        if is_read is not None:
            filters.append(Notification.is_read == is_read)
        if since_at is not None:
            filters.append(Notification.created_at >= since_at)

        base = select(Notification).where(*filters)
        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (
            await self.session.execute(base.order_by(Notification.created_at.desc()).limit(limit).offset(offset))
        ).scalars().all()
        return rows, total

    async def unread_count(self, *, user_id: str) -> int:
        stmt = select(func.count()).where(Notification.recipient_user_id == user_id, Notification.is_read.is_(False))
        return (await self.session.execute(stmt)).scalar_one()

    async def unread_count_for_users(self, *, user_ids: list[str]) -> dict[str, int]:
        if not user_ids:
            return {}
        rows = (
            await self.session.execute(
                select(Notification.recipient_user_id, func.count())
                .where(Notification.recipient_user_id.in_(user_ids), Notification.is_read.is_(False))
                .group_by(Notification.recipient_user_id)
            )
        ).all()
        return {str(user_id): int(total) for user_id, total in rows}

    async def unread_count_by_type(self, *, user_id: str, notification_type: NotificationType) -> int:
        stmt = select(func.count()).where(
            Notification.recipient_user_id == user_id,
            Notification.notification_type == notification_type,
            Notification.is_read.is_(False),
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def mark_read(self, *, notification_id: str, user_id: str) -> None:
        await self.session.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.recipient_user_id == user_id)
            .values(is_read=True)
        )

    async def mark_all_read(self, *, user_id: str) -> None:
        await self.session.execute(
            update(Notification).where(Notification.recipient_user_id == user_id).values(is_read=True)
        )

    async def mark_all_read_by_type(self, *, user_id: str, notification_type: NotificationType) -> None:
        await self.session.execute(
            update(Notification)
            .where(
                Notification.recipient_user_id == user_id,
                Notification.notification_type == notification_type,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )

    async def get_by_id(self, *, notification_id: str) -> Notification | None:
        return (
            await self.session.execute(
                select(Notification).where(Notification.id == notification_id)
            )
        ).scalar_one_or_none()

    async def list_push_deliveries(self, *, notification_id: str) -> list[NotificationDelivery]:
        return (
            await self.session.execute(
                select(NotificationDelivery)
                .where(
                    NotificationDelivery.notification_id == notification_id,
                    NotificationDelivery.channel == DeliveryChannel.PUSH,
                )
                .order_by(NotificationDelivery.created_at.asc())
            )
        ).scalars().all()

    async def max_delivery_attempt(self, *, notification_id: str, channel: DeliveryChannel) -> int:
        row = await self.session.execute(
            select(func.max(NotificationDelivery.attempt_no)).where(
                NotificationDelivery.notification_id == notification_id,
                NotificationDelivery.channel == channel,
            )
        )
        max_attempt = row.scalar_one_or_none()
        return int(max_attempt or 0)

    async def list_active_devices(self, *, user_id: str) -> list[DeviceRegistration]:
        return (
            await self.session.execute(
                select(DeviceRegistration).where(
                    DeviceRegistration.user_id == user_id,
                    DeviceRegistration.is_active.is_(True),
                )
            )
        ).scalars().all()

    async def get_device_by_token(self, *, push_token: str) -> DeviceRegistration | None:
        return (
            await self.session.execute(
                select(DeviceRegistration).where(DeviceRegistration.push_token == push_token)
            )
        ).scalar_one_or_none()

    async def get_device_by_identity(
        self, *, user_id: str, device_id: str, platform: str
    ) -> DeviceRegistration | None:
        return (
            await self.session.execute(
                select(DeviceRegistration).where(
                    DeviceRegistration.user_id == user_id,
                    DeviceRegistration.device_id == device_id,
                    DeviceRegistration.platform == platform,
                )
            )
        ).scalar_one_or_none()
