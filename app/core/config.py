"""Application configuration settings."""
from __future__ import annotations

from functools import lru_cache
from pydantic import AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Base application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    env: str = "development"
    debug: bool = True

    database_url: str = "postgresql+psycopg2://booked:booked@postgres:5432/booked"
    redis_url: str = "redis://redis:6379/0"

    admin_email: str = "admin@example.com"
    admin_password_hash: str = (
        "$2b$12$Xo8eH4mUhKopD4w9b0Hdc.u1gB2xFVt4C8rvb3bqlYQfF.JTkwq5a"
    )
    admin_api_key: str | None = None

    telegram_bot_token: str | None = None
    telegram_bot_username: str | None = None
    admin_tg_ids: str = ""

    tbank_enabled: bool = False
    tbank_token: str | None = None
    tbank_merchant_id: str | None = None
    tbank_terminal_key: str | None = None

    calendar_enabled: bool = False
    calendar_base_url: AnyUrl | None = None
    calendar_username: str | None = None
    calendar_password: str | None = None

    default_timezone: str = "Europe/Oslo"

    api_host: str = "0.0.0.0"
    api_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
