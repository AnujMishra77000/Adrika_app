from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "adr_platform",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.tasks_notifications",
        "app.workers.tasks_outbox",
        "app.workers.tasks_assessments",
    ],
)

celery_app.conf.update(
    timezone="UTC",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=30,
    task_routes={
        "app.workers.tasks_notifications.*": {"queue": "notifications_bulk"},
        "app.workers.tasks_outbox.*": {"queue": "integrations"},
        "app.workers.tasks_assessments.*": {"queue": "assessments"},
    },
    beat_schedule={
        "process-outbox-every-minute": {
            "task": "app.workers.tasks_outbox.process_outbox_events",
            "schedule": 60.0,
        },
        "process-assessments-every-minute": {
            "task": "app.workers.tasks_assessments.process_assessment_schedules",
            "schedule": 60.0,
        },
    },
)
