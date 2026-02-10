"""Telegram bot settings."""
from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    """Settings for Telegram bot service."""

    model_config = SettingsConfigDict(
        env_ignore_empty=True,
        extra="ignore",
    )

    telegram_bot_token: str | None = None
    telegram_bot_username: str | None = None
    backend_url: str = "http://api:8000"
    redis_url: str = "redis://redis:6379/1"
    admin_tg_ids: str = ""


@lru_cache
def get_bot_settings() -> BotSettings:
    """Return cached bot settings."""

    return BotSettings()
