"""Celery app configuration."""
from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "booked",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.beat_schedule = {
    "expire-holds": {
        "task": "app.workers.tasks.expire_holds",
        "schedule": 60.0,
    }
}
