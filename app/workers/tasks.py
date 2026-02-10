"""Celery tasks for background processing."""
from __future__ import annotations

import logging

from celery import shared_task

from app.db.session import SessionLocal
from app.services.booking_service import BookingService
from app.services.integrations.calendar import StubCalendarProvider
from app.services.integrations.payment import StubPaymentProvider

logger = logging.getLogger(__name__)


@shared_task(name="app.workers.tasks.expire_holds")
def expire_holds() -> int:
    """Expire holds that outlive the configured hold duration."""

    db = SessionLocal()
    try:
        service = BookingService(db, StubPaymentProvider(), StubCalendarProvider())
        expired = service.expire_holds()
        logger.info("Expired %s holds", expired)
        return expired
    finally:
        db.close()
