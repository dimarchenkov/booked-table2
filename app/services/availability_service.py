"""Availability computation for tables."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus, Closure, ScheduleRule, WorkingHour


@dataclass(slots=True)
class Slot:
    """Availability slot representation."""

    start_at: datetime
    end_at: datetime


class AvailabilityService:
    """Service to generate availability slots based on schedule rules."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def generate_slots(self, table_id: int, target_date: date) -> list[Slot]:
        """Generate available slots for a given table and date.

        Slots are generated from schedule rules and working hours in the configured
        timezone. Closed days and existing bookings are excluded. Output slots are
        returned in UTC.
        """

        rule = self.session.execute(select(ScheduleRule)).scalar_one_or_none()
        if rule is None:
            return []

        timezone = ZoneInfo(rule.timezone)
        working_hours = self.session.execute(
            select(WorkingHour).where(WorkingHour.weekday == target_date.weekday())
        ).scalars().all()
        if not working_hours:
            return []

        closures = self.session.execute(
            select(Closure).where(
                Closure.date == target_date,
                or_(Closure.table_id.is_(None), Closure.table_id == table_id),
            )
        ).scalars().all()
        if closures:
            return []

        slots: list[Slot] = []
        slot_delta = timedelta(minutes=rule.slot_minutes)
        buffer_delta = timedelta(minutes=rule.buffer_minutes)

        for window in working_hours:
            if not window.is_open:
                continue

            window_start = datetime.combine(target_date, window.start_time, tzinfo=timezone)
            window_end = datetime.combine(target_date, window.end_time, tzinfo=timezone)

            current = window_start
            while current + slot_delta <= window_end:
                slot_start = current
                slot_end = current + slot_delta
                if buffer_delta:
                    slot_end = slot_end + buffer_delta
                slots.append(Slot(start_at=slot_start.astimezone(ZoneInfo("UTC")), end_at=slot_end.astimezone(ZoneInfo("UTC"))))
                current = current + slot_delta

        if not slots:
            return []

        start_range = min(slot.start_at for slot in slots)
        end_range = max(slot.end_at for slot in slots)

        bookings = self.session.execute(
            select(Booking).where(
                and_(
                    Booking.table_id == table_id,
                    Booking.status.in_([BookingStatus.HOLD, BookingStatus.CONFIRMED]),
                    Booking.start_at < end_range,
                    Booking.end_at > start_range,
                )
            )
        ).scalars().all()

        available_slots: list[Slot] = []
        for slot in slots:
            overlap = any(
                booking.start_at < slot.end_at and booking.end_at > slot.start_at
                for booking in bookings
            )
            if not overlap:
                available_slots.append(slot)

        return available_slots
