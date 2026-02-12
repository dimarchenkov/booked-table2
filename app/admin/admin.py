"""Admin setup using SQLAdmin."""
from __future__ import annotations

import bcrypt
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import engine
from app.models import Booking, Closure, Payment, ScheduleRule, Table, WorkingHour

settings = get_settings()


class AdminAuthBackend(AuthenticationBackend):
    """Authentication backend for admin panel."""

    async def login(self, request) -> bool:
        form = await request.form()
        email = form.get("username")
        password = form.get("password")
        if not email or not password:
            return False
        if email != settings.admin_email:
            return False
        if not bcrypt.checkpw(password.encode(), settings.admin_password_hash.encode()):
            return False
        request.session.update({"token": "admin"})
        return True

    async def logout(self, request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request) -> bool:
        return request.session.get("token") == "admin"


class TableAdmin(ModelView, model=Table):
    column_list = [Table.id, Table.name, Table.location, Table.active, Table.created_at]
    name = "Table"
    name_plural = "Tables"

    async def delete_model(self, request, pk: int) -> None:
        session: Session = self.session_maker()
        table = session.get(Table, pk)
        if table:
            table.active = False
            session.commit()


class ScheduleRuleAdmin(ModelView, model=ScheduleRule):
    column_list = [
        ScheduleRule.timezone,
        ScheduleRule.slot_minutes,
        ScheduleRule.buffer_minutes,
        ScheduleRule.min_booking_minutes,
        ScheduleRule.max_booking_minutes,
        ScheduleRule.hold_minutes,
    ]


class WorkingHourAdmin(ModelView, model=WorkingHour):
    column_list = [
        WorkingHour.weekday,
        WorkingHour.start_time,
        WorkingHour.end_time,
        WorkingHour.is_open,
    ]


class ClosureAdmin(ModelView, model=Closure):
    column_list = [Closure.date, Closure.table_id, Closure.reason]


class BookingAdmin(ModelView, model=Booking):
    column_list = [
        Booking.id,
        Booking.table_id,
        Booking.client_id,
        Booking.start_at,
        Booking.end_at,
        Booking.status,
        Booking.created_at,
    ]
    can_create = False
    can_edit = False
    can_delete = False


class PaymentAdmin(ModelView, model=Payment):
    column_list = [
        Payment.id,
        Payment.booking_id,
        Payment.provider,
        Payment.amount,
        Payment.status,
        Payment.created_at,
    ]
    can_create = False
    can_edit = False
    can_delete = False


def setup_admin(app) -> Admin:
    """Initialize SQLAdmin with configured views."""

    authentication_backend = AdminAuthBackend(secret_key="admin-secret")
    admin = Admin(app, engine, authentication_backend=authentication_backend)
    admin.add_view(TableAdmin)
    admin.add_view(ScheduleRuleAdmin)
    admin.add_view(WorkingHourAdmin)
    admin.add_view(ClosureAdmin)
    admin.add_view(BookingAdmin)
    admin.add_view(PaymentAdmin)
    return admin
