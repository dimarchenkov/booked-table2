"""Tests for availability generation."""
from __future__ import annotations

from datetime import date

from app.models import Closure, Table
from app.services.availability_service import AvailabilityService


def test_availability_with_closure(db_session, seed_schedule):
    table = Table(name="Table", location=None, active=True)
    db_session.add(table)
    db_session.commit()

    closure = Closure(date=date.today(), table_id=table.id, reason="Closed")
    db_session.add(closure)
    db_session.commit()

    service = AvailabilityService(db_session)
    slots = service.generate_slots(table.id, date.today())

    assert slots == []
