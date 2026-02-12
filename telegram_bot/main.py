"""Telegram bot entrypoint."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from telegram_bot.handlers.booking import router as booking_router
from telegram_bot.handlers.common import router as common_router
from telegram_bot.services.backend_client import BackendClient
from telegram_bot.settings import get_bot_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

settings = get_bot_settings()


async def _get_storage():
    try:
        redis = Redis.from_url(settings.redis_url)
        await redis.ping()
        return RedisStorage(redis)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis unavailable, using memory storage: %s", exc)
        return MemoryStorage()


async def main() -> None:
    """Run Telegram bot long polling."""

    if not settings.telegram_bot_token:
        logger.info("TELEGRAM_BOT_TOKEN missing, bot disabled")
        return

    bot = Bot(token=settings.telegram_bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    try:
        me = await bot.get_me()
        settings.telegram_bot_username = me.username
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unable to fetch bot username: %s", exc)

    storage = await _get_storage()
    dp = Dispatcher(storage=storage)

    backend_client = BackendClient(base_url=settings.backend_url)
    dp["client"] = backend_client

    dp.include_router(common_router)
    dp.include_router(booking_router)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
