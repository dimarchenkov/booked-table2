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

    choosing_date = State()
    choosing_slot = State()


@router.message(F.text == "Забронировать")
async def start_booking(message: Message, state: FSMContext, client: BackendClient) -> None:
    """Start booking flow by selecting date first."""

    builder = InlineKeyboardBuilder()
    builder.button(text="Сегодня", callback_data="date:today")
    builder.button(text="Завтра", callback_data="date:tomorrow")
    await message.answer("Выберите дату:", reply_markup=builder.as_markup())
    await state.set_state(BookingStates.choosing_date)


@router.callback_query(F.data.startswith("date:") & BookingStates.choosing_date)
async def select_date(callback: CallbackQuery, state: FSMContext, client: BackendClient) -> None:
    """Handle date selection and fetch slots with any free table."""

    choice = callback.data.split(":")[1]
    chosen_date = date.today() if choice == "today" else date.today() + timedelta(days=1)

    tables = await client.get_tables()
    slot_to_table: dict[tuple[str, str], int] = {}
    for table in tables:
        table_slots = await client.get_availability(table["id"], chosen_date)
        for slot in table_slots:
            key = (slot["start_at"], slot["end_at"])
            slot_to_table.setdefault(key, table["id"])

    slots = sorted(slot_to_table.keys())
    builder = InlineKeyboardBuilder()
    slot_options: list[dict] = []
    for idx, (start_at, end_at) in enumerate(slots):
        start = datetime.fromisoformat(start_at).strftime("%H:%M")
        end = datetime.fromisoformat(end_at).strftime("%H:%M")
        builder.button(text=f"{start}-{end}", callback_data=f"slot:{idx}")
        slot_options.append(
            {
                "start_at": start_at,
                "end_at": end_at,
                "table_id": slot_to_table[(start_at, end_at)],
            }
        )
    if not slots:
        await callback.message.answer("Нет доступных слотов на выбранную дату.")
        await state.clear()
        await callback.answer()
        return
    await state.update_data(slot_options=slot_options)
    await callback.message.answer("Выберите слот:", reply_markup=builder.as_markup())
    await state.set_state(BookingStates.choosing_slot)
    await callback.answer()


@router.callback_query(F.data.startswith("slot:") & BookingStates.choosing_slot)
async def select_slot(callback: CallbackQuery, state: FSMContext, client: BackendClient) -> None:
    """Handle slot selection and create booking hold on any available table."""

    slot_index = int(callback.data.split(":")[1])
    data = await state.get_data()
    slot = data["slot_options"][slot_index]
    payload = {
        "table_id": slot["table_id"],
        "start_at": slot["start_at"],
        "end_at": slot["end_at"],
        "tg_user_id": str(callback.from_user.id),
        "name": callback.from_user.full_name,
    }
    booking = await client.create_hold(payload)
    await callback.message.answer(
        f"Бронь #{booking['id']} создана. Стол №{booking['table_id']}. Оплата: {booking.get('payment_url', 'нет ссылки')}"
    )
    await state.clear()
    await callback.answer()
