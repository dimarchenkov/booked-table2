"""Booking operations for the service."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Booking,
    BookingStatus,
    Client,
    Payment,
    PaymentStatus,
    ScheduleRule,
    Table,
)
from app.services.integrations.calendar import CalendarProvider
from app.services.integrations.payment import PaymentProvider


class BookingService:
    """Service that encapsulates booking creation and confirmation."""

    def __init__(
        self,
        session: Session,
        payment_provider: PaymentProvider,
        calendar_provider: CalendarProvider,
    ) -> None:
        self.session = session
        self.payment_provider = payment_provider
        self.calendar_provider = calendar_provider

    def create_hold(
        self,
        *,
        table_id: int,
        start_at: datetime,
        end_at: datetime,
        tg_user_id: str,
        name: str | None,
        phone: str | None,
    ) -> Booking:
        """Create a HOLD booking with a NEW payment.

        Ensures overlap protection through database constraints and returns
        the booking with payment URL attached.
        """

        rule = self.session.execute(select(ScheduleRule)).scalar_one_or_none()
        _ = rule.hold_minutes if rule else 10

        client = self._upsert_client(tg_user_id=tg_user_id, name=name, phone=phone)
        overlap = self.session.execute(
            select(Booking).where(
                Booking.table_id == table_id,
                Booking.status.in_([BookingStatus.HOLD, BookingStatus.CONFIRMED]),
                Booking.start_at < end_at,
                Booking.end_at > start_at,
            )
        ).scalar_one_or_none()
        if overlap:
            raise ValueError("Booking overlaps with existing reservation.")

        booking = Booking(
            table_id=table_id,
            client_id=client.id,
            start_at=start_at,
            end_at=end_at,
            status=BookingStatus.HOLD,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        payment = Payment(
            booking=booking,
            status=PaymentStatus.NEW,
            amount=0,
            currency="RUB",
        )

        self.session.add_all([booking, payment])
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ValueError("Booking overlaps with existing reservation.") from exc

        payment_init = self.payment_provider.init_payment(payment)
        payment.payment_url = payment_init.payment_url
        payment.provider_payment_id = payment_init.provider_payment_id
        booking.updated_at = datetime.utcnow()

        self.session.commit()
        self.session.refresh(booking)
        return booking

    def create_hold_auto(
        self,
        *,
        start_at: datetime,
        end_at: datetime,
        tg_user_id: str,
        name: str | None,
        phone: str | None,
    ) -> Booking:
        """Create HOLD by assigning any free active table for interval."""

        tables = self.session.execute(select(Table).where(Table.active.is_(True)).order_by(Table.id)).scalars().all()
        for table in tables:
            overlap = self.session.execute(
                select(Booking).where(
                    Booking.table_id == table.id,
                    Booking.status.in_([BookingStatus.HOLD, BookingStatus.CONFIRMED]),
                    Booking.start_at < end_at,
                    Booking.end_at > start_at,
                )
            ).scalar_one_or_none()
            if overlap is None:
                return self.create_hold(
                    table_id=table.id,
                    start_at=start_at,
                    end_at=end_at,
                    tg_user_id=tg_user_id,
                    name=name,
                    phone=phone,
                )
        raise ValueError("No free tables for selected time interval.")

    def confirm_booking(self, booking_id: int) -> Booking:
        """Confirm a booking and create a calendar event."""

        booking = self.session.get(Booking, booking_id)
        if booking is None:
            raise ValueError("Booking not found")

        booking.status = BookingStatus.CONFIRMED
        booking.updated_at = datetime.utcnow()
        event = self.calendar_provider.create_event(booking)
        if event:
            booking.calendar_event_uid = event.uid
            booking.calendar_event_href = event.href
        self.session.commit()
        return booking

    def cancel_booking(self, booking_id: int) -> Booking:
        """Cancel a booking."""

        booking = self.session.get(Booking, booking_id)
        if booking is None:
            raise ValueError("Booking not found")

        booking.status = BookingStatus.CANCELLED
        booking.updated_at = datetime.utcnow()
        if booking.calendar_event_uid:
            self.calendar_provider.delete_event(booking.calendar_event_uid)
        self.session.commit()
        return booking

    def expire_holds(self) -> int:
        """Expire HOLD bookings that exceed configured hold duration."""

        rule = self.session.execute(select(ScheduleRule)).scalar_one_or_none()
        hold_minutes = rule.hold_minutes if rule else 10
        threshold = datetime.utcnow() - timedelta(minutes=hold_minutes)

        bookings = (
            self.session.execute(
                select(Booking).where(
                    Booking.status == BookingStatus.HOLD,
                    Booking.created_at < threshold,
                )
            )
            .scalars()
            .all()
        )
        for booking in bookings:
            booking.status = BookingStatus.EXPIRED
            booking.updated_at = datetime.utcnow()
        self.session.commit()
        return len(bookings)

    def _upsert_client(self, *, tg_user_id: str, name: str | None, phone: str | None) -> Client:
        """Create or update client by Telegram user ID."""

        client = self.session.execute(
            select(Client).where(Client.tg_user_id == tg_user_id)
        ).scalar_one_or_none()
        if client is None:
            client = Client(tg_user_id=tg_user_id, name=name, phone=phone)
            self.session.add(client)
            self.session.flush()
        else:
            client.name = name or client.name
            client.phone = phone or client.phone
        return client
