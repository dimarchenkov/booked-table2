"""Booking flow handlers."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import httpx
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from telegram_bot.services.backend_client import BackendClient

router = Router()
MAX_DAYS_AHEAD = 14
SLOTS_PER_PAGE = 12
MIN_DURATION_HOURS = 1
MAX_DURATION_HOURS = 8


class BookingStates(StatesGroup):
    """FSM states for booking flow."""

    choosing_day = State()
    choosing_slot = State()
    choosing_duration = State()
    confirming = State()


def _format_day_label(day: date) -> str:
    return day.strftime("%a %d.%m")


def _slot_step_minutes(day_slots: list[dict]) -> int:
    """Infer slot step from data; fallback to 30 minutes."""

    if len(day_slots) < 2:
        return 30
    first = datetime.fromisoformat(day_slots[0]["start_at"])
    second = datetime.fromisoformat(day_slots[1]["start_at"])
    step = int((second - first).total_seconds() // 60)
    return step if step > 0 else 30


def _can_fit_duration(day_slots: list[dict], slot_index: int, duration_hours: int) -> bool:
    """Check if consecutive free slots can fit selected duration."""

    step = _slot_step_minutes(day_slots)
    required_steps = max(1, (duration_hours * 60) // step)
    if slot_index + required_steps > len(day_slots):
        return False
    return all(day_slots[i]["is_free"] for i in range(slot_index, slot_index + required_steps))


def _calculate_end_at(start_at_iso: str, day_slots: list[dict], duration_hours: int) -> str:
    """Calculate booking end from start and selected duration."""

    start_dt = datetime.fromisoformat(start_at_iso)
    end_dt = start_dt + timedelta(hours=duration_hours)
    return end_dt.isoformat()


async def _show_week(message: Message | CallbackQuery, state: FSMContext, week_start: int) -> None:
    """Render week selector within 14-day window."""

    max_offset = MAX_DAYS_AHEAD - 1
    week_start = max(0, min(week_start, max_offset))

    builder = InlineKeyboardBuilder()
    for offset in range(week_start, min(week_start + 7, MAX_DAYS_AHEAD)):
        day = date.today() + timedelta(days=offset)
        builder.button(text=_format_day_label(day), callback_data=f"day:{day.isoformat()}")
    builder.adjust(2)

    nav = []
    if week_start > 0:
        nav.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"week:{max(0, week_start - 7)}"))
    nav.append(InlineKeyboardButton(text="Today", callback_data="week:0"))
    if week_start + 7 < MAX_DAYS_AHEAD:
        nav.append(InlineKeyboardButton(text="Next ▶️", callback_data=f"week:{week_start + 7}"))

    markup = builder.as_markup()
    markup.inline_keyboard.append(nav)
    await state.set_state(BookingStates.choosing_day)
    await state.update_data(week_start=week_start)

    target = message.message if isinstance(message, CallbackQuery) else message
    await target.answer("Выберите день (2 недели):", reply_markup=markup)
    if isinstance(message, CallbackQuery):
        await message.answer()


async def _show_slots(callback: CallbackQuery, state: FSMContext, client: BackendClient, target_day: date, page: int = 0) -> None:
    """Render paginated slot list with free/busy flags."""

    all_slots = await client.get_auto_availability(target_day)
    all_slots = sorted(all_slots, key=lambda x: x["start_at"])

    total_pages = max(1, (len(all_slots) + SLOTS_PER_PAGE - 1) // SLOTS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    chunk = all_slots[page * SLOTS_PER_PAGE : (page + 1) * SLOTS_PER_PAGE]

    builder = InlineKeyboardBuilder()
    for idx, slot in enumerate(chunk):
        start = datetime.fromisoformat(slot["start_at"]).strftime("%H:%M")
        global_idx = page * SLOTS_PER_PAGE + idx
        if slot["is_free"]:
            builder.button(text=f"{start} ✅", callback_data=f"slot:{global_idx}")
        else:
            builder.button(text=f"{start} ❌", callback_data="slot_busy")

    builder.adjust(3)

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"slots_page:{target_day.isoformat()}:{page - 1}"))
    if page + 1 < total_pages:
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"slots_page:{target_day.isoformat()}:{page + 1}"))
    if nav_row:
        builder.row(*nav_row)
    builder.row(InlineKeyboardButton(text="🔙 Назад к дням", callback_data="week:0"))

    await state.update_data(day_slots=all_slots, selected_day=target_day.isoformat())
    await state.set_state(BookingStates.choosing_slot)
    await callback.message.answer(
        f"Слоты на {target_day.strftime('%d.%m.%Y')} (страница {page + 1}/{total_pages}):",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.message(F.text == "Забронировать")
async def start_booking(message: Message, state: FSMContext, client: BackendClient) -> None:
    """Start booking flow with calendar-first UX."""

    await _show_week(message, state, week_start=0)


@router.callback_query(F.data.startswith("week:"))
async def change_week(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle week navigation."""

    week_start = int(callback.data.split(":")[1])
    await _show_week(callback, state, week_start=week_start)


@router.callback_query(F.data.startswith("day:"), StateFilter(BookingStates.choosing_day))
async def choose_day(callback: CallbackQuery, state: FSMContext, client: BackendClient) -> None:
    """Handle day selection."""

    day = date.fromisoformat(callback.data.split(":")[1])
    if day < date.today() or day > date.today() + timedelta(days=MAX_DAYS_AHEAD - 1):
        await callback.answer("Можно выбрать только ближайшие 2 недели", show_alert=True)
        return
    await _show_slots(callback, state, client, day, page=0)


@router.callback_query(F.data.startswith("slots_page:"), StateFilter(BookingStates.choosing_slot))
async def slots_page(callback: CallbackQuery, state: FSMContext, client: BackendClient) -> None:
    """Handle slot pagination."""

    _, day_iso, page_raw = callback.data.split(":")
    await _show_slots(callback, state, client, date.fromisoformat(day_iso), int(page_raw))


@router.callback_query((F.data == "slot_busy"), StateFilter(BookingStates.choosing_slot))
async def slot_busy(callback: CallbackQuery) -> None:
    """Show occupied slot alert."""

    await callback.answer("Занято", show_alert=True)


@router.callback_query(F.data.startswith("slot:"), StateFilter(BookingStates.choosing_slot))
async def choose_slot(callback: CallbackQuery, state: FSMContext) -> None:
    """Ask user to choose booking duration for selected start slot."""

    slot_index = int(callback.data.split(":")[1])
    data = await state.get_data()
    day_slots = data.get("day_slots", [])
    if slot_index >= len(day_slots):
        await callback.answer("Слот не найден", show_alert=True)
        return
    if not day_slots[slot_index]["is_free"]:
        await callback.answer("Занято", show_alert=True)
        return

    start = datetime.fromisoformat(day_slots[slot_index]["start_at"]).strftime("%d.%m.%Y %H:%M")
    kb = InlineKeyboardBuilder()
    for h in range(MIN_DURATION_HOURS, MAX_DURATION_HOURS + 1):
        if _can_fit_duration(day_slots, slot_index, h):
            kb.button(text=f"{h} ч ✅", callback_data=f"dur:{h}")
        else:
            kb.button(text=f"{h} ч ❌", callback_data="dur_busy")
    kb.adjust(4)
    kb.row(InlineKeyboardButton(text="🔙 Назад к слотам", callback_data=f"slots_page:{data['selected_day']}:0"))

    await state.update_data(slot_index=slot_index)
    await state.set_state(BookingStates.choosing_duration)
    await callback.message.answer(f"Старт: {start}\nВыберите длительность:", reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query((F.data == "dur_busy"), StateFilter(BookingStates.choosing_duration))
async def duration_busy(callback: CallbackQuery) -> None:
    """Show alert when chosen duration doesn't fit."""

    await callback.answer("Недостаточно свободных слотов подряд", show_alert=True)


@router.callback_query(F.data.startswith("dur:"), StateFilter(BookingStates.choosing_duration))
async def choose_duration(callback: CallbackQuery, state: FSMContext) -> None:
    """Ask user to confirm booking for selected duration."""

    duration_hours = int(callback.data.split(":")[1])
    data = await state.get_data()
    day_slots = data.get("day_slots", [])
    slot_index = data.get("slot_index")
    if slot_index is None or slot_index >= len(day_slots):
        await callback.answer("Слот не выбран", show_alert=True)
        return
    if not _can_fit_duration(day_slots, slot_index, duration_hours):
        await callback.answer("Этот интервал уже занят", show_alert=True)
        return

    start_at = day_slots[slot_index]["start_at"]
    end_at = _calculate_end_at(start_at, day_slots, duration_hours)
    start_label = datetime.fromisoformat(start_at).strftime("%d.%m.%Y %H:%M")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_slot")],
            [InlineKeyboardButton(text="🔙 Назад к длительности", callback_data="back_duration")],
        ]
    )
    await state.update_data(chosen_slot={"start_at": start_at, "end_at": end_at, "duration_hours": duration_hours})
    await state.set_state(BookingStates.confirming)
    await callback.message.answer(
        f"Дата и время: {start_label}\nДлительность: {duration_hours} ч. Подтвердить?",
        reply_markup=keyboard,
    )
    await callback.answer()




@router.callback_query((F.data == "back_duration"), StateFilter(BookingStates.confirming))
async def back_duration(callback: CallbackQuery, state: FSMContext) -> None:
    """Return from confirmation to duration selection."""

    data = await state.get_data()
    day_slots = data.get("day_slots", [])
    slot_index = data.get("slot_index")
    if slot_index is None or slot_index >= len(day_slots):
        await callback.answer("Слот не выбран", show_alert=True)
        return

    start = datetime.fromisoformat(day_slots[slot_index]["start_at"]).strftime("%d.%m.%Y %H:%M")
    kb = InlineKeyboardBuilder()
    for h in range(MIN_DURATION_HOURS, MAX_DURATION_HOURS + 1):
        if _can_fit_duration(day_slots, slot_index, h):
            kb.button(text=f"{h} ч ✅", callback_data=f"dur:{h}")
        else:
            kb.button(text=f"{h} ч ❌", callback_data="dur_busy")
    kb.adjust(4)
    kb.row(InlineKeyboardButton(text="🔙 Назад к слотам", callback_data=f"slots_page:{data['selected_day']}:0"))

    await state.set_state(BookingStates.choosing_duration)
    await callback.message.answer(f"Старт: {start}\nВыберите длительность:", reply_markup=kb.as_markup())
    await callback.answer()

@router.callback_query((F.data == "confirm_slot"), StateFilter(BookingStates.confirming))
async def confirm_slot(callback: CallbackQuery, state: FSMContext, client: BackendClient) -> None:
    """Create booking hold with automatic table assignment."""

    data = await state.get_data()
    slot = data.get("chosen_slot")
    if not slot:
        await callback.answer("Слот не выбран", show_alert=True)
        return

    payload = {
        "start_at": slot["start_at"],
        "end_at": slot["end_at"],
        "tg_user_id": str(callback.from_user.id),
        "name": callback.from_user.full_name,
    }

    try:
        booking = await client.create_hold_auto(payload)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 409:
            await callback.message.answer("Этот интервал уже заняли. Выберите другой слот или длительность.")
            await callback.answer("Слот занят", show_alert=True)
            await state.set_state(BookingStates.choosing_slot)
            return
        raise

    hold_minutes = booking.get("hold_minutes", 10)
    table_label = booking.get("table_name") or f"Стол №{booking['table_id']}"

    buttons = []
    if booking.get("payment_url"):
        buttons.append([InlineKeyboardButton(text="Оплатить", url=booking["payment_url"])])
    buttons.append([InlineKeyboardButton(text="Отменить бронь", callback_data=f"cancel_hold:{booking['id']}")])

    await callback.message.answer(
        f"Готово! Назначен стол: {table_label}. Оплатите в течение {hold_minutes} минут.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_hold:"))
async def cancel_hold(callback: CallbackQuery, client: BackendClient) -> None:
    """Cancel hold from inline button."""

    booking_id = int(callback.data.split(":")[1])
    await client.cancel_booking(booking_id)
    await callback.message.answer("Бронь отменена.")
    await callback.answer()
