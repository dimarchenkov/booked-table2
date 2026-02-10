"""API schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class TableOut(BaseModel):
    id: int
    name: str
    location: str | None
    active: bool


class AvailabilitySlot(BaseModel):
    start_at: datetime
    end_at: datetime


class BookingHoldIn(BaseModel):
    table_id: int
    start_at: datetime
    end_at: datetime
    tg_user_id: str
    name: str | None = None
    phone: str | None = None


class BookingOut(BaseModel):
    id: int
    table_id: int
    client_id: int
    start_at: datetime
    end_at: datetime
    status: str
    payment_url: str | None = None


class BookingCancelOut(BaseModel):
    id: int
    status: str


class BookingConfirmOut(BaseModel):
    id: int
    status: str


class AvailabilityQuery(BaseModel):
    table_id: int = Field(..., alias="table_id")
    date: date


class WebhookResponse(BaseModel):
    status: str
