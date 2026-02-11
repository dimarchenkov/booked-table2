"""Common bot handlers."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from telegram_bot.services.backend_client import BackendClient
from telegram_bot.settings import get_bot_settings

router = Router()
settings = get_bot_settings()


def _build_main_keyboard() -> ReplyKeyboardBuilder:
    builder = ReplyKeyboardBuilder()
    builder.button(text="Забронировать")
    builder.button(text="Мои брони")
    return builder


@router.message(F.text.startswith("/start"))
async def start_command(message: Message) -> None:
    """Handle /start command."""

    payload = message.text.replace("/start", "").strip()
    if payload == "from_group":
        await message.answer("Вы пришли из группы. Давайте забронируем стол 👇")
    await message.answer("Добро пожаловать!", reply_markup=_build_main_keyboard().as_markup(resize_keyboard=True))


@router.message(F.text == "Мои брони")
async def my_bookings(message: Message, client: BackendClient) -> None:
    """Show active bookings for the user."""

    response = await client.get_booking_for_user(str(message.from_user.id))
    if not response:
        await message.answer("У вас нет активных броней.")
        return
    lines = [f"#{booking['id']} {booking['status']} {booking['start_at']}" for booking in response]
    await message.answer("\n".join(lines))


@router.message(F.text.startswith("/cancel"))
async def cancel_command(message: Message, client: BackendClient) -> None:
    """Cancel booking by ID."""

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Используйте /cancel <id>")
        return
    booking_id = int(parts[1])
    await client.cancel_booking(booking_id)
    await message.answer("Бронь отменена.")


@router.message(F.text == "/post_booking")
async def post_booking(message: Message) -> None:
    """Send group poster to admin group."""

    if message.chat.type not in {"group", "supergroup"}:
        await message.answer("Команда доступна только в группе.")
        return
    admin_ids = {int(x) for x in settings.admin_tg_ids.split(",") if x.strip().isdigit()}
    if message.from_user.id not in admin_ids:
        await message.answer("Недостаточно прав.")
        return
    bot_username = settings.telegram_bot_username or "<bot_username>"
    deep_link = f"https://t.me/{bot_username}?start=from_group"
    text = "📦 Аренда столов для упаковки. Нажмите кнопку ниже, чтобы забронировать время."
    button = InlineKeyboardButton(text="Забронировать", url=deep_link)
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[button]]))


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery) -> None:
    await callback.answer()
