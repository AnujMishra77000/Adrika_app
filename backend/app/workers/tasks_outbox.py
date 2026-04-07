import structlog
from celery import shared_task

logger = structlog.get_logger(__name__)


@shared_task(bind=True, max_retries=5)
def process_outbox_events(self) -> None:
    logger.info("process_outbox_events_tick")
