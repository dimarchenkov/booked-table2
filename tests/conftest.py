"""Pytest fixtures for database."""
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def seed_schedule(db_session):
    from app.models import ScheduleRule, WorkingHour

    db_session.add(
        ScheduleRule(
            timezone="Europe/Oslo",
            slot_minutes=60,
            buffer_minutes=0,
            min_booking_minutes=60,
            max_booking_minutes=240,
            hold_minutes=10,
        )
    )
    db_session.add(
        WorkingHour(
            weekday=dt.date.today().weekday(),
            start_time=dt.time(9, 0),
            end_time=dt.time(12, 0),
            is_open=True,
        )
    )
    db_session.commit()
    return db_session
