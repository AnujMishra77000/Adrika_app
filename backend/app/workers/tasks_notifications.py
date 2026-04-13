import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

import structlog
from celery import shared_task

from app.db.models.notification import NotificationDelivery
from app.db.session import AsyncSessionLocal

logger = structlog.get_logger(__name__)


@shared_task(bind=True, max_retries=5)
def dispatch_push_notification(self, notification_id: str) -> None:
    logger.info("dispatch_push_notification", notification_id=notification_id)


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
