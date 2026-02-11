"""Initial schema.

Revision ID: 0001_initial
Revises: 
Create Date: 2024-01-24
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "tables",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("location", sa.String, nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "clients",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tg_user_id", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=True),
        sa.Column("phone", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "schedule_rules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("timezone", sa.String, nullable=False, server_default="Europe/Oslo"),
        sa.Column("slot_minutes", sa.Integer, nullable=False, server_default="60"),
        sa.Column("buffer_minutes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("min_booking_minutes", sa.Integer, nullable=False, server_default="60"),
        sa.Column("max_booking_minutes", sa.Integer, nullable=False, server_default="240"),
        sa.Column("hold_minutes", sa.Integer, nullable=False, server_default="10"),
    )

    op.create_table(
        "working_hours",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("weekday", sa.Integer, nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("is_open", sa.Boolean, nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "closures",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("table_id", sa.Integer, sa.ForeignKey("tables.id"), nullable=True),
        sa.Column("reason", sa.String, nullable=True),
    )

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("table_id", sa.Integer, sa.ForeignKey("tables.id"), nullable=False),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("start_at", sa.DateTime, nullable=False),
        sa.Column("end_at", sa.DateTime, nullable=False),
        sa.Column("status", sa.Enum("HOLD", "CONFIRMED", "CANCELLED", "EXPIRED", name="bookingstatus"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
        sa.Column("calendar_event_uid", sa.String, nullable=True),
        sa.Column("calendar_event_href", sa.String, nullable=True),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("booking_id", sa.Integer, sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("provider", sa.String, nullable=False, server_default="tbank"),
        sa.Column("amount", sa.Integer, nullable=False, server_default="0"),
        sa.Column("currency", sa.String, nullable=False, server_default="RUB"),
        sa.Column("status", sa.Enum("NEW", "PENDING", "PAID", "FAILED", "CANCELLED", name="paymentstatus"), nullable=False),
        sa.Column("provider_payment_id", sa.String, nullable=True),
        sa.Column("payment_url", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    op.execute(
        """
        ALTER TABLE bookings
        ADD CONSTRAINT bookings_no_overlap
        EXCLUDE USING gist (
            table_id WITH =,
            tsrange(start_at, end_at, '[)') WITH &&
        )
        WHERE (status IN ('HOLD', 'CONFIRMED'))
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS payments")
    op.execute("DROP TABLE IF EXISTS bookings")
    op.execute("DROP TABLE IF EXISTS closures")
    op.execute("DROP TABLE IF EXISTS working_hours")
    op.execute("DROP TABLE IF EXISTS schedule_rules")
    op.execute("DROP TABLE IF EXISTS clients")
    op.execute("DROP TABLE IF EXISTS tables")
    op.execute("DROP TYPE IF EXISTS bookingstatus")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
