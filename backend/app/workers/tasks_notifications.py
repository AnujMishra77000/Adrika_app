import structlog
from celery import shared_task

logger = structlog.get_logger(__name__)


@shared_task(bind=True, max_retries=5)
def dispatch_push_notification(self, notification_id: str) -> None:
    logger.info("dispatch_push_notification", notification_id=notification_id)


@shared_task(bind=True, max_retries=5)
def dispatch_whatsapp_template(self, delivery_id: str) -> None:
    logger.info("dispatch_whatsapp_template", delivery_id=delivery_id)
