"""Calendar provider interfaces and implementations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Booking


@dataclass(slots=True)
class CalendarEvent:
    """Representation of a calendar event."""

    uid: str
    href: str


class CalendarProvider(Protocol):
    """Interface for calendar providers."""

    def create_event(self, booking: Booking) -> CalendarEvent | None:
        """Create a calendar event for a booking."""

    def delete_event(self, uid: str) -> None:
        """Delete a calendar event by UID."""


class StubCalendarProvider:
    """Stub calendar provider used by default."""

    def create_event(self, booking: Booking) -> CalendarEvent | None:
        """No-op calendar creation for stub provider."""

        return None

    def delete_event(self, uid: str) -> None:
        """No-op calendar deletion for stub provider."""

        return None


class YandexCalDAVCalendarProvider:
    """Placeholder calendar provider for Yandex CalDAV."""

    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url
        self.username = username
        self.password = password

    def create_event(self, booking: Booking) -> CalendarEvent | None:
        """Create an event (stub implementation)."""

        return CalendarEvent(uid=f"booking-{booking.id}", href=f"{self.base_url}/event/{booking.id}")

    def delete_event(self, uid: str) -> None:
        """Delete an event (stub implementation)."""

        return None
