"""Booking flow handlers."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from telegram_bot.services.backend_client import BackendClient

router = Router()


class BookingStates(StatesGroup):
    """FSM states for booking flow."""

    choosing_table = State()
    choosing_date = State()
    choosing_slot = State()


@router.message(F.text == "Забронировать")
async def start_booking(message: Message, state: FSMContext, client: BackendClient) -> None:
    """Start booking flow by selecting a table."""

    tables = await client.get_tables()
    builder = InlineKeyboardBuilder()
    for table in tables:
        builder.button(text=table["name"], callback_data=f"table:{table['id']}")
    await message.answer("Выберите стол:", reply_markup=builder.as_markup())
    await state.set_state(BookingStates.choosing_table)


@router.callback_query(F.data.startswith("table:") & BookingStates.choosing_table)
async def select_table(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle table selection."""

    table_id = int(callback.data.split(":")[1])
    await state.update_data(table_id=table_id)
    builder = InlineKeyboardBuilder()
    builder.button(text="Сегодня", callback_data="date:today")
    builder.button(text="Завтра", callback_data="date:tomorrow")
    await callback.message.answer("Выберите дату:", reply_markup=builder.as_markup())
    await state.set_state(BookingStates.choosing_date)
    await callback.answer()


@router.callback_query(F.data.startswith("date:") & BookingStates.choosing_date)
async def select_date(callback: CallbackQuery, state: FSMContext, client: BackendClient) -> None:
    """Handle date selection and fetch slots."""

    choice = callback.data.split(":")[1]
    chosen_date = date.today() if choice == "today" else date.today() + timedelta(days=1)
    data = await state.get_data()
    table_id = data["table_id"]
    slots = await client.get_availability(table_id, chosen_date)
    builder = InlineKeyboardBuilder()
    for slot in slots:
        start = datetime.fromisoformat(slot["start_at"]).strftime("%H:%M")
        end = datetime.fromisoformat(slot["end_at"]).strftime("%H:%M")
        builder.button(text=f"{start}-{end}", callback_data=f"slot:{slot['start_at']}|{slot['end_at']}")
    if not slots:
        await callback.message.answer("Нет доступных слотов на выбранную дату.")
        await state.clear()
        await callback.answer()
        return
    await callback.message.answer("Выберите слот:", reply_markup=builder.as_markup())
    await state.set_state(BookingStates.choosing_slot)
    await callback.answer()


@router.callback_query(F.data.startswith("slot:") & BookingStates.choosing_slot)
async def select_slot(callback: CallbackQuery, state: FSMContext, client: BackendClient) -> None:
    """Handle slot selection and create booking hold."""

    slot_payload = callback.data.split(":")[1]
    start_at, end_at = slot_payload.split("|")
    data = await state.get_data()
    payload = {
        "table_id": data["table_id"],
        "start_at": start_at,
        "end_at": end_at,
        "tg_user_id": str(callback.from_user.id),
        "name": callback.from_user.full_name,
    }
    booking = await client.create_hold(payload)
    await callback.message.answer(
        f"Бронь #{booking['id']} создана. Оплата: {booking.get('payment_url', 'нет ссылки')}"
    )
    await state.clear()
    await callback.answer()
