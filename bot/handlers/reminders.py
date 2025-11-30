"""Reminder creation and management handlers."""

import datetime
import re
import aiosqlite
import pytz
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config import (
    DB_PATH,
    DATE_FORMAT,
    FULL_DATE_FORMAT,
    TIME_FORMAT,
    FREQUENCY_ZERO,
    CITY_TIMEZONES
)
from bot.database import get_user_timezone
from bot.keyboards import keyboard, inline_markup_cancel, create_inline_keyboard, create_calendar, process_calendar_selection
from bot.states import ReminderStates
from bot.utils import resolve_date, finalize_date

router = Router()


@router.message(F.text == '+')
async def add_reminder(message: types.Message, state: FSMContext):
    """Start reminder creation process."""
    user_id = message.from_user.id
    timezone = await get_user_timezone(user_id)

    if timezone is None:
        city_buttons = [[(city, f"city_{city}")] for city in CITY_TIMEZONES.keys()]
        inline_markup_cities = create_inline_keyboard(city_buttons)
        msg = await message.answer(
            "Пожалуйста, выберите ваш город, соответствующий вашему часовому поясу, из списка:",
            reply_markup=inline_markup_cities
        )
        await state.update_data(bot_message_id=msg.message_id)
        await state.set_state(ReminderStates.waiting_for_city)
    else:
        msg = await message.answer("Введите название уведомления:", reply_markup=inline_markup_cancel)
        await state.update_data(bot_message_id=msg.message_id)
        await state.set_state(ReminderStates.waiting_for_name)


@router.message(ReminderStates.waiting_for_name)
async def get_name(message: types.Message, state: FSMContext):
    """Handle reminder name input."""
    await message.delete()
    data = await state.get_data()
    bot_message_id = data['bot_message_id']
    name_reminder = message.text

    await state.update_data(name_reminder=name_reminder)
    await message.bot.edit_message_text(
        text=f"Название уведомления: *{name_reminder}*\n\n"
             f"Введите частоту уведомления ({FREQUENCY_ZERO} для одноразового "
             f"или, например, '1min 1h 1d 1m 1y'):",
        chat_id=message.chat.id,
        message_id=bot_message_id,
        reply_markup=inline_markup_cancel,
        parse_mode="Markdown"
    )
    await state.set_state(ReminderStates.waiting_for_frequency)


@router.message(ReminderStates.waiting_for_frequency)
async def get_frequency(message: types.Message, state: FSMContext):
    """Handle reminder frequency input."""
    await message.delete()
    frequency = message.text.strip()

    if frequency != FREQUENCY_ZERO and not re.match(r'^(\d+(min|h|d|m|y)\s*)*$', frequency.lower()):
        data = await state.get_data()
        bot_message_id = data['bot_message_id']
        name_reminder = data['name_reminder']
        await message.bot.edit_message_text(
            text=f"Название уведомления: *{name_reminder}*\n\n"
                 f"Пожалуйста, введите частоту в формате '{FREQUENCY_ZERO}' или '1min 1h 1d 1m 1y' "
                 f"(можно указать только часть):",
            chat_id=message.chat.id,
            message_id=bot_message_id,
            reply_markup=inline_markup_cancel,
            parse_mode="Markdown"
        )
        return

    data = await state.get_data()
    bot_message_id = data['bot_message_id']
    name_reminder = data['name_reminder']
    await state.update_data(frequency=frequency)

    calendar_markup = create_calendar()

    await message.bot.edit_message_text(
        text=f"Название уведомления: *{name_reminder}*\n"
             f"Частота: *{frequency}*\n\n"
             f"Выберите дату из календаря или введите даты в формате {DATE_FORMAT} или {FULL_DATE_FORMAT} "
             f"(можно несколько через запятую, например 15.10,16.10):",
        chat_id=message.chat.id,
        message_id=bot_message_id,
        reply_markup=calendar_markup,
        parse_mode="Markdown"
    )
    await state.set_state(ReminderStates.waiting_for_date)


@router.message(ReminderStates.waiting_for_date)
async def get_date(message: types.Message, state: FSMContext):
    """Handle reminder date input."""
    await message.delete()
    dates = message.text

    try:
        date_list = [date.strip() for date in dates.split(",")]
        resolved_dates = []
        for date in date_list:
            resolved_date, _ = resolve_date(date)
            resolved_dates.append(resolved_date)

        data = await state.get_data()
        bot_message_id = data['bot_message_id']
        name_reminder = data['name_reminder']
        frequency = data['frequency']
        await state.update_data(dates=",".join(resolved_dates))

        await message.bot.edit_message_text(
            text=f"Название уведомления: *{name_reminder}*\n"
                 f"Частота: *{frequency}*\n"
                 f"Даты: *{','.join(resolved_dates)}*\n\n"
                 f"Введите время в формате {TIME_FORMAT} (можно несколько через запятую):",
            chat_id=message.chat.id,
            message_id=bot_message_id,
            reply_markup=inline_markup_cancel,
            parse_mode="Markdown"
        )
        await state.set_state(ReminderStates.waiting_for_time)
    except ValueError:
        data = await state.get_data()
        bot_message_id = data['bot_message_id']
        name_reminder = data['name_reminder']
        frequency = data['frequency']

        calendar_markup = create_calendar()

        await message.bot.edit_message_text(
            text=f"Название уведомления: *{name_reminder}*\n"
                 f"Частота: *{frequency}*\n\n"
                 f"Пожалуйста, выберите дату из календаря или введите даты в формате {DATE_FORMAT} или {FULL_DATE_FORMAT} "
                 f"(можно несколько через запятую, например 15.10,16.10):",
            chat_id=message.chat.id,
            message_id=bot_message_id,
            reply_markup=calendar_markup,
            parse_mode="Markdown"
        )


@router.message(ReminderStates.waiting_for_time)
async def get_time(message: types.Message, state: FSMContext):
    """Handle reminder time input."""
    await message.delete()
    times = message.text

    try:
        time_list = [time.strip() for time in times.split(",")]
        for time in time_list:
            datetime.datetime.strptime(time, TIME_FORMAT)

        data = await state.get_data()
        user_id = message.from_user.id
        name_reminder = data['name_reminder']
        frequency = data['frequency']
        dates = data['dates']
        timezone = await get_user_timezone(user_id)
        current_dt = datetime.datetime.now(pytz.UTC)

        date_list = dates.split(",")
        finalized_dates = []
        for date in date_list:
            for time in time_list:
                finalized_date = finalize_date(date, time, current_dt, timezone)
                if finalized_date not in finalized_dates:
                    finalized_dates.append(finalized_date)
        finalized_dates.sort()

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                'INSERT INTO reminders (user_id, name_reminder, frequency, dates, times, active) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (user_id, name_reminder, frequency, ",".join(finalized_dates), ",".join(time_list), 1)
            )
            await db.commit()

        bot_message_id = data['bot_message_id']
        await message.bot.edit_message_text(
            text=f"Напоминание успешно добавлено!\n\n"
                 f"Название: *{name_reminder}*\n"
                 f"Частота: *{frequency}*\n"
                 f"Даты: *{','.join(finalized_dates)}*\n"
                 f"Время: *{times}*",
            chat_id=message.chat.id,
            message_id=bot_message_id,
            parse_mode="Markdown"
        )
        await state.clear()
    except ValueError:
        data = await state.get_data()
        bot_message_id = data['bot_message_id']
        name_reminder = data['name_reminder']
        frequency = data['frequency']
        dates = data['dates']

        await message.bot.edit_message_text(
            text=f"Название уведомления: *{name_reminder}*\n"
                 f"Частота: *{frequency}*\n"
                 f"Даты: *{dates}*\n\n"
                 f"Пожалуйста, введите время в формате {TIME_FORMAT} "
                 f"(можно несколько через запятую):",
            chat_id=message.chat.id,
            message_id=bot_message_id,
            reply_markup=inline_markup_cancel,
            parse_mode="Markdown"
        )


@router.message(F.text == 'Мои уведомления')
async def list_reminders(message: types.Message):
    """List all active reminders."""
    user_id = message.from_user.id
    timezone = await get_user_timezone(user_id)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT id, name_reminder, frequency, dates, times, active '
            'FROM reminders WHERE user_id = ? AND active = 1',
            (user_id,)
        ) as cursor:
            reminders = await cursor.fetchall()

    if reminders:
        response = "Ваши активные уведомления:\n"
        user_tz = pytz.timezone(timezone)
        for reminder in reminders:
            id, name, frequency, dates, times, active = reminder
            date_list = dates.split(",")
            local_dates = []
            for date in date_list:
                date_dt = datetime.datetime.strptime(date, FULL_DATE_FORMAT)
                date_local = date_dt.astimezone(user_tz).strftime(FULL_DATE_FORMAT)
                if date_local not in local_dates:
                    local_dates.append(date_local)
            response += (
                f"Название: {name}\n"
                f"Частота: {frequency}\n"
                f"Даты: {','.join(local_dates)}\n"
                f"Время: {times}\n"
                f"Команда для удаления: /delete{id}\n\n"
            )
        await message.answer(response)
    else:
        await message.answer("У вас нет активных уведомлений.")


@router.message(F.text.startswith('/delete'))
async def handle_delete_command(message: types.Message):
    """Delete a reminder by ID."""
    try:
        reminder_id = int(message.text.split("/delete")[1])
    except ValueError:
        await message.answer("Неверный формат команды.")
        return

    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT 1 FROM reminders WHERE id = ? AND user_id = ?',
            (reminder_id, user_id)
        ) as cursor:
            if not await cursor.fetchone():
                await message.answer("Напоминание не найдено или не принадлежит вам.")
                return
        await db.execute(
            'DELETE FROM reminders WHERE id = ? AND user_id = ?',
            (reminder_id, user_id)
        )
        await db.commit()

    await list_reminders(message)


@router.callback_query(lambda c: c.data == "cancel")
async def cancel_creation(callback: types.CallbackQuery, state: FSMContext):
    """Cancel reminder creation."""
    await state.clear()
    await callback.message.edit_text("Создание уведомления отменено.", reply_markup=None)
    await callback.message.answer("Выбери действие:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith(("DAY;", "PREV-MONTH;", "NEXT-MONTH;", "IGNORE;")))
async def handle_calendar_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle calendar callback queries."""
    current_state = await state.get_state()

    # Only process calendar callbacks when waiting for date
    if current_state != ReminderStates.waiting_for_date:
        await callback.answer()
        return

    selected, date = await process_calendar_selection(callback, callback.data)

    if selected:
        # User selected a date
        selected_date = date.strftime(FULL_DATE_FORMAT)

        await state.update_data(dates=selected_date)
        data = await state.get_data()
        bot_message_id = data['bot_message_id']
        name_reminder = data['name_reminder']
        frequency = data['frequency']

        await callback.message.bot.edit_message_text(
            text=f"Название уведомления: *{name_reminder}*\n"
                 f"Частота: *{frequency}*\n"
                 f"Даты: *{selected_date}*\n\n"
                 f"Введите время в формате {TIME_FORMAT} (можно несколько через запятую):",
            chat_id=callback.message.chat.id,
            message_id=bot_message_id,
            reply_markup=inline_markup_cancel,
            parse_mode="Markdown"
        )
        await state.set_state(ReminderStates.waiting_for_time)


@router.callback_query(lambda c: c.data.startswith(("delete_", "last_")))
async def delete_new_reminder(callback: types.CallbackQuery):
    """Mark reminder as done or delete temporary reminder."""
    callback_data = callback.data

    if callback_data.startswith("last_"):
        # For last temporary reminder, just change button to "doned ✅"
        reminder_id = int(callback_data.split("_")[1])
        inline_button_doned = InlineKeyboardButton(
            text="doned ✅",
            callback_data=f"doned_{reminder_id}"
        )
        inline_markup_doned = InlineKeyboardMarkup(inline_keyboard=[[inline_button_doned]])
        await callback.message.edit_reply_markup(reply_markup=inline_markup_doned)
        await callback.answer("Напоминание отмечено как выполненное.")
    else:
        # Delete temporary reminder from database
        new_reminder_id = int(callback_data.split("_")[1])
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                'SELECT 1 FROM reminders WHERE id = ? AND user_id = ?',
                (new_reminder_id, callback.from_user.id)
            ) as cursor:
                if not await cursor.fetchone():
                    await callback.answer("Напоминание не найдено.")
                    return
            await db.execute(
                'DELETE FROM reminders WHERE id = ? AND user_id = ?',
                (new_reminder_id, callback.from_user.id)
            )
            await db.commit()

        inline_button_doned = InlineKeyboardButton(
            text="doned ✅",
            callback_data=f"doned_{new_reminder_id}"
        )
        inline_markup_doned = InlineKeyboardMarkup(inline_keyboard=[[inline_button_doned]])
        await callback.message.edit_reply_markup(reply_markup=inline_markup_doned)
        await callback.answer("Напоминание успешно выполнено.")
