"""Wait for database readiness."""
from __future__ import annotations

import os
import time

import psycopg


def main() -> None:
    """Block until the database accepts connections."""

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    timeout_seconds = int(os.getenv("DB_WAIT_SECONDS", "30"))
    deadline = time.time() + timeout_seconds

    while True:
        try:
            with psycopg.connect(database_url):
                return
        except Exception:  # noqa: BLE001
            if time.time() >= deadline:
                raise SystemExit("Database is not ready")
            time.sleep(1)


if __name__ == "__main__":
    main()
