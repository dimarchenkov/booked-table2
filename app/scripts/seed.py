"""Seed database with default data."""
from __future__ import annotations

from datetime import time

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import ScheduleRule, Table, WorkingHour


def main() -> None:
    """Seed tables, schedule rules, and working hours."""

    db = SessionLocal()
    try:
        rule = db.execute(select(ScheduleRule)).scalar_one_or_none()
        if rule is None:
            db.add(
                ScheduleRule(
                    timezone="Europe/Oslo",
                    slot_minutes=60,
                    buffer_minutes=0,
                    min_booking_minutes=60,
                    max_booking_minutes=240,
                    hold_minutes=10,
                )
            )

        existing_tables = db.execute(select(Table)).scalars().all()
        if not existing_tables:
            db.add_all(
                [
                    Table(name="Table 1", location="Main Hall"),
                    Table(name="Table 2", location="Main Hall"),
                    Table(name="Table 3", location="Window"),
                ]
            )

        existing_hours = db.execute(select(WorkingHour)).scalars().all()
        if not existing_hours:
            db.add_all(
                [
                    WorkingHour(weekday=weekday, start_time=time(9, 0), end_time=time(21, 0), is_open=True)
                    for weekday in range(7)
                ]
            )
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
