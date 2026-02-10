"""Client for backend API."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import httpx


@dataclass(slots=True)
class BackendClient:
    """HTTP client for booking backend."""

    base_url: str

    async def get_tables(self) -> list[dict]:
        """Fetch available tables."""

        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.get("/tables")
            response.raise_for_status()
            return response.json()

    async def get_availability(self, table_id: int, target_date: date) -> list[dict]:
        """Fetch availability slots."""

        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.get(
                "/availability",
                params={"table_id": table_id, "date": target_date.isoformat()},
            )
            response.raise_for_status()
            return response.json()

    async def create_hold(self, payload: dict) -> dict:
        """Create a hold booking."""

        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.post("/bookings/hold", json=payload)
            response.raise_for_status()
            return response.json()

    async def get_booking(self, booking_id: int) -> dict:
        """Fetch booking details."""

        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.get(f"/bookings/{booking_id}")
            response.raise_for_status()
            return response.json()

    async def cancel_booking(self, booking_id: int) -> dict:
        """Cancel booking."""

        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.post(f"/bookings/{booking_id}/cancel")
            response.raise_for_status()
            return response.json()

    async def get_booking_for_user(self, tg_user_id: str) -> list[dict]:
        """Fetch active bookings for a Telegram user."""

        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.get(f"/clients/{tg_user_id}/bookings")
            response.raise_for_status()
            return response.json()
