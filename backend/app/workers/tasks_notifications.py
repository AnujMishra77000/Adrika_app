from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

import structlog
from celery import shared_task

from app.db.models.enums import DeliveryChannel
from app.db.models.notification import NotificationDelivery
from app.db.session import AsyncSessionLocal
from app.integrations.fcm_client import FCMClient
from app.repositories.notification_repo import NotificationRepository

logger = structlog.get_logger(__name__)


def _safe_json_loads(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


@shared_task(bind=True, max_retries=5)
def dispatch_push_notification(self, notification_id: str) -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            repo = NotificationRepository(session)
            notification = await repo.get_by_id(notification_id=notification_id)
            if not notification:
                logger.warning("push_notification_not_found", notification_id=notification_id)
                return

            devices = await repo.list_active_devices(user_id=notification.recipient_user_id)
            if not devices:
                session.add(
                    NotificationDelivery(
                        notification_id=notification_id,
                        channel=DeliveryChannel.PUSH,
                        status="no_device",
                        attempt_no=1,
                        provider_response=json.dumps({"reason": "no_active_device"}),
                    )
                )
                await session.commit()
                return

            deliveries = await repo.list_push_deliveries(notification_id=notification_id)
            delivered_or_invalid_tokens: set[str] = set()
            for delivery in deliveries:
                if delivery.status not in {"sent", "invalid_token"}:
                    continue
                payload = _safe_json_loads(delivery.provider_response)
                token = payload.get("device_token")
                if isinstance(token, str) and token:
                    delivered_or_invalid_tokens.add(token)

            pending_devices = [device for device in devices if device.push_token not in delivered_or_invalid_tokens]
            if not pending_devices:
                return

            fcm = FCMClient()
            base_attempt = await repo.max_delivery_attempt(
                notification_id=notification_id,
                channel=DeliveryChannel.PUSH,
            )
            retryable_failures = 0

            for index, device in enumerate(pending_devices, start=1):
                result = await fcm.send(
                    device_token=device.push_token,
                    title=notification.title,
                    body=notification.body,
                    data={
                        "notification_id": notification.id,
                        "notification_type": str(notification.notification_type.value if hasattr(notification.notification_type, "value") else notification.notification_type),
                    },
                )

                response_payload = {
                    "device_token": device.push_token,
                    "device_id": device.device_id,
                    "platform": device.platform,
                    "response": result.provider_response,
                }
                session.add(
                    NotificationDelivery(
                        notification_id=notification.id,
                        channel=DeliveryChannel.PUSH,
                        provider_message_id=result.provider_message_id,
                        status=result.status,
                        attempt_no=base_attempt + index,
                        provider_response=json.dumps(response_payload, default=str),
                    )
                )

                if result.invalid_token:
                    device.is_active = False

                if result.retryable:
                    retryable_failures += 1

            await session.commit()

            if retryable_failures:
                raise RuntimeError(f"{retryable_failures} push deliveries need retry")

    try:
        asyncio.run(_run())
    except Exception as exc:  # pragma: no cover - celery retry path
        logger.warning(
            "push_delivery_retry",
            notification_id=notification_id,
            error=str(exc),
            retry_count=self.request.retries,
        )
        raise self.retry(exc=exc, countdown=min(120, 5 * (self.request.retries + 1)))


@shared_task(bind=True, max_retries=5)
def dispatch_whatsapp_template(self, delivery_id: str) -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            delivery = await session.get(NotificationDelivery, delivery_id)
            if not delivery:
                logger.warning("whatsapp_delivery_not_found", delivery_id=delivery_id)
                return

            payload = {}
            if delivery.provider_response:
                try:
                    payload = json.loads(delivery.provider_response)
                except json.JSONDecodeError:
                    payload = {"raw": delivery.provider_response}

            delivery.status = "sent"
            if not delivery.provider_message_id:
                delivery.provider_message_id = f"wa_{uuid4().hex[:16]}"
            payload["sent_at"] = datetime.now(UTC).isoformat()
            delivery.provider_response = json.dumps(payload, default=str)
            await session.commit()

            logger.info(
                "dispatch_whatsapp_template",
                delivery_id=delivery_id,
                provider_message_id=delivery.provider_message_id,
            )

    asyncio.run(_run())
