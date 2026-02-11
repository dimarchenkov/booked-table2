"""API routes."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import (
    AvailabilitySlot,
    DaySlotStatus,
    BookingCancelOut,
    BookingConfirmOut,
    BookingHoldAutoIn,
    BookingHoldIn,
    BookingOut,
    TableOut,
    WebhookResponse,
)
from app.core.config import get_settings
from datetime import datetime

from app.models import Booking, BookingStatus, Client, Payment, PaymentStatus, ScheduleRule, Table
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService
from app.services.integrations.calendar import StubCalendarProvider, YandexCalDAVCalendarProvider
from app.services.integrations.payment import StubPaymentProvider, TBankPaymentProvider

router = APIRouter()
settings = get_settings()


def _get_payment_provider():
    if settings.tbank_enabled and settings.tbank_terminal_key and settings.tbank_token:
        return TBankPaymentProvider(settings.tbank_terminal_key, settings.tbank_token)
    return StubPaymentProvider()


def _get_calendar_provider():
    if settings.calendar_enabled and settings.calendar_base_url and settings.calendar_username and settings.calendar_password:
        return YandexCalDAVCalendarProvider(
            str(settings.calendar_base_url),
            settings.calendar_username,
            settings.calendar_password,
        )
    return StubCalendarProvider()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/tables", response_model=list[TableOut])
def list_tables(db: Session = Depends(get_db)) -> list[TableOut]:
    tables = db.execute(select(Table).where(Table.active.is_(True))).scalars().all()
    return [TableOut(id=t.id, name=t.name, location=t.location, active=t.active) for t in tables]


@router.get("/availability", response_model=list[AvailabilitySlot])
def availability(table_id: int, date: date, db: Session = Depends(get_db)) -> list[AvailabilitySlot]:
    service = AvailabilityService(db)
    slots = service.generate_slots(table_id, date)
    return [AvailabilitySlot(start_at=s.start_at, end_at=s.end_at) for s in slots]


@router.get("/availability/auto", response_model=list[DaySlotStatus])
def availability_auto(date: date, db: Session = Depends(get_db)) -> list[DaySlotStatus]:
    service = AvailabilityService(db)
    slots = service.generate_any_table_availability(date)
    return [DaySlotStatus(start_at=s.start_at, end_at=s.end_at, is_free=is_free) for s, is_free in slots]


@router.post("/bookings/hold", response_model=BookingOut)
def create_hold(payload: BookingHoldIn, db: Session = Depends(get_db)) -> BookingOut:
    service = BookingService(db, _get_payment_provider(), _get_calendar_provider())
    try:
        booking = service.create_hold(
            table_id=payload.table_id,
            start_at=payload.start_at,
            end_at=payload.end_at,
            tg_user_id=payload.tg_user_id,
            name=payload.name,
            phone=payload.phone,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    rule = db.execute(select(ScheduleRule)).scalar_one_or_none()
    payment = booking.payments[-1] if booking.payments else None
    return BookingOut(
        id=booking.id,
        table_id=booking.table_id,
        client_id=booking.client_id,
        start_at=booking.start_at,
        end_at=booking.end_at,
        status=booking.status.value,
        payment_url=payment.payment_url if payment else None,
        table_name=booking.table.name if booking.table else None,
        hold_minutes=rule.hold_minutes if rule else 10,
    )


@router.post("/bookings/hold/auto", response_model=BookingOut)
def create_hold_auto(payload: BookingHoldAutoIn, db: Session = Depends(get_db)) -> BookingOut:
    service = BookingService(db, _get_payment_provider(), _get_calendar_provider())
    try:
        booking = service.create_hold_auto(
            start_at=payload.start_at,
            end_at=payload.end_at,
            tg_user_id=payload.tg_user_id,
            name=payload.name,
            phone=payload.phone,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    rule = db.execute(select(ScheduleRule)).scalar_one_or_none()
    payment = booking.payments[-1] if booking.payments else None
    return BookingOut(
        id=booking.id,
        table_id=booking.table_id,
        client_id=booking.client_id,
        start_at=booking.start_at,
        end_at=booking.end_at,
        status=booking.status.value,
        payment_url=payment.payment_url if payment else None,
        table_name=booking.table.name if booking.table else None,
        hold_minutes=rule.hold_minutes if rule else 10,
    )


@router.get("/bookings/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: int, db: Session = Depends(get_db)) -> BookingOut:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    rule = db.execute(select(ScheduleRule)).scalar_one_or_none()
    payment = booking.payments[-1] if booking.payments else None
    return BookingOut(
        id=booking.id,
        table_id=booking.table_id,
        client_id=booking.client_id,
        start_at=booking.start_at,
        end_at=booking.end_at,
        status=booking.status.value,
        payment_url=payment.payment_url if payment else None,
        table_name=booking.table.name if booking.table else None,
        hold_minutes=rule.hold_minutes if rule else 10,
    )


@router.post("/bookings/{booking_id}/cancel", response_model=BookingCancelOut)
def cancel_booking(booking_id: int, db: Session = Depends(get_db)) -> BookingCancelOut:
    service = BookingService(db, _get_payment_provider(), _get_calendar_provider())
    try:
        booking = service.cancel_booking(booking_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BookingCancelOut(id=booking.id, status=booking.status.value)


@router.post("/bookings/{booking_id}/confirm", response_model=BookingConfirmOut)
def confirm_booking(booking_id: int, request: Request, db: Session = Depends(get_db)) -> BookingConfirmOut:
    if settings.debug is False:
        api_key = request.headers.get("X-Admin-Api-Key")
        if not settings.admin_api_key or api_key != settings.admin_api_key:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin API key required")

    service = BookingService(db, _get_payment_provider(), _get_calendar_provider())
    try:
        booking = service.confirm_booking(booking_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BookingConfirmOut(id=booking.id, status=booking.status.value)


@router.post("/webhooks/tbank", response_model=WebhookResponse)
def tbank_webhook(payload: dict, db: Session = Depends(get_db)) -> WebhookResponse:
    if not settings.tbank_enabled:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TBank disabled")

    provider = _get_payment_provider()
    if not provider.verify_webhook(payload):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook")

    payment_id = payload.get("payment_id")
    status_value = payload.get("status", PaymentStatus.PAID.value)

    payment = db.get(Payment, payment_id)
    if payment:
        payment.status = PaymentStatus(status_value)
        payment.updated_at = datetime.utcnow()
        if payment.status == PaymentStatus.PAID:
            booking = payment.booking
            booking.status = BookingStatus.CONFIRMED
            booking.updated_at = datetime.utcnow()
        db.commit()

    return WebhookResponse(status="ok")


@router.get("/payments/{payment_id}/stub")
def payment_stub(payment_id: int) -> dict:
    return {"status": "stub", "payment_id": payment_id}


@router.get("/clients/{tg_user_id}/bookings", response_model=list[BookingOut])
def list_bookings_for_user(tg_user_id: str, db: Session = Depends(get_db)) -> list[BookingOut]:
    client = db.execute(select(Client).where(Client.tg_user_id == tg_user_id)).scalar_one_or_none()
    if not client:
        return []
    bookings = db.execute(
        select(Booking).where(
            Booking.client_id == client.id,
            Booking.status.in_([BookingStatus.HOLD, BookingStatus.CONFIRMED]),
        )
    ).scalars().all()
    rule = db.execute(select(ScheduleRule)).scalar_one_or_none()
    result = []
    for booking in bookings:
        payment = booking.payments[-1] if booking.payments else None
        result.append(
            BookingOut(
                id=booking.id,
                table_id=booking.table_id,
                client_id=booking.client_id,
                start_at=booking.start_at,
                end_at=booking.end_at,
                status=booking.status.value,
                payment_url=payment.payment_url if payment else None,
                table_name=booking.table.name if booking.table else None,
                hold_minutes=rule.hold_minutes if rule else 10,
            )
        )
    return result
