"""Tests for hold expiration."""
from __future__ import annotations

from datetime import datetime, timedelta

from app.models import Booking, BookingStatus, Client, Table
from app.services.booking_service import BookingService
from app.services.integrations.calendar import StubCalendarProvider
from app.services.integrations.payment import StubPaymentProvider


def test_expire_holds(db_session, seed_schedule):
    table = Table(name="Table", location=None, active=True)
    client = Client(tg_user_id="1", name="Client", phone=None)
    db_session.add_all([table, client])
    db_session.commit()

    booking = Booking(
        table_id=table.id,
        client_id=client.id,
        start_at=datetime.utcnow(),
        end_at=datetime.utcnow() + timedelta(hours=1),
        status=BookingStatus.HOLD,
        created_at=datetime.utcnow() - timedelta(minutes=20),
        updated_at=datetime.utcnow(),
    )
    db_session.add(booking)
    db_session.commit()

    service = BookingService(db_session, StubPaymentProvider(), StubCalendarProvider())
    expired = service.expire_holds()

    assert expired == 1
    assert booking.status == BookingStatus.EXPIRED
