"""Telegram bot settings."""
from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    """Settings for Telegram bot service."""

    model_config = SettingsConfigDict(
        env_ignore_empty=True,
        extra="allow",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Ignore dotenv source to avoid parsing unrelated keys from project .env."""

        return init_settings, env_settings, file_secret_settings

    telegram_bot_token: str | None = None
    telegram_bot_username: str | None = None
    backend_url: str = "http://api:8000"
    redis_url: str = "redis://redis:6379/1"
    admin_tg_ids: str = ""

    # Compatibility fields for shared .env files used by API service.
    debug: bool | None = None
    database_url: str | None = None
    admin_email: str | None = None
    admin_password_hash: str | None = None
    tbank_enabled: bool | None = None
    calendar_enabled: bool | None = None
    calendar_base_url: str | None = None
    default_timezone: str | None = None


@lru_cache
def get_bot_settings() -> BotSettings:
    """Return cached bot settings."""

    return BotSettings()
