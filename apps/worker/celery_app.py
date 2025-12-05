"""Celery application for background tasks."""

from celery import Celery
from celery.schedules import crontab

from apps.api.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "produckai",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Configure beat schedule
celery_app.conf.beat_schedule = {
    'refresh-tokens-every-10-min': {
        'task': 'refresh_expiring_tokens',
        'schedule': crontab(minute='*/10'),
    },
    'daily-clustering-pipeline': {
        'task': 'run_daily_clustering_pipeline',
        'schedule': crontab(hour=2, minute=0),  # Run at 2:00 AM UTC daily
        'options': {
            'expires': 3600,  # Task expires after 1 hour if not picked up
        },
    },
}

# Auto-discover tasks
celery_app.autodiscover_tasks(["apps.worker.tasks"])
