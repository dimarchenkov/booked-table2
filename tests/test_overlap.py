"""Tests for overlap prevention."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.models import Table
from app.services.booking_service import BookingService
from app.services.integrations.calendar import StubCalendarProvider
from app.services.integrations.payment import StubPaymentProvider


def test_overlap_prevention(db_session, seed_schedule):
    table = Table(name="Table", location=None, active=True)
    db_session.add(table)
    db_session.commit()

    service = BookingService(db_session, StubPaymentProvider(), StubCalendarProvider())
    start_at = datetime.utcnow()
    end_at = start_at + timedelta(hours=1)

    service.create_hold(
        table_id=table.id,
        start_at=start_at,
        end_at=end_at,
        tg_user_id="1",
        name="Client",
        phone=None,
    )

    with pytest.raises(ValueError):
        service.create_hold(
            table_id=table.id,
            start_at=start_at + timedelta(minutes=30),
            end_at=end_at + timedelta(minutes=30),
            tg_user_id="2",
            name="Client2",
            phone=None,
        )
