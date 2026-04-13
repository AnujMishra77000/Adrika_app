import asyncio

import structlog
from celery import shared_task

from app.db.session import AsyncSessionLocal
from app.services.assessment_service import AssessmentService

logger = structlog.get_logger(__name__)


@shared_task(bind=True, max_retries=3)
def process_assessment_schedules(self) -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            stats = await AssessmentService(session).process_scheduled_events()
            logger.info("process_assessment_schedules", **stats)

    asyncio.run(_run())
