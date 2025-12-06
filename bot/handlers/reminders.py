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
from bot.keyboards import (
    keyboard,
    inline_markup_cancel,
    create_inline_keyboard,
    create_calendar,
    separate_callback_data,
    inline_markup_quick_templates,
    inline_markup_popular_times,
    inline_markup_frequency_presets
)
from bot.states import ReminderStates
from bot.utils import resolve_date, finalize_date

router = Router()


@router.message(F.text == '+')
async def add_reminder(message: types.Message, state: FSMContext):
    """Start reminder creation process with quick templates."""
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
        msg = await message.answer(
            "Выберите быстрый шаблон или создайте свое напоминание:",
            reply_markup=inline_markup_quick_templates
        )
        await state.update_data(bot_message_id=msg.message_id)
        await state.set_state(ReminderStates.waiting_for_template_choice)


@router.callback_query(lambda c: c.data.startswith("quick_"))
async def handle_quick_template(callback: types.CallbackQuery, state: FSMContext):
    """Handle quick template selection."""
    template = callback.data
    user_id = callback.from_user.id
    timezone = await get_user_timezone(user_id)
    user_tz = pytz.timezone(timezone)
    current_dt = datetime.datetime.now(user_tz)

    # Calculate date and time based on template
    if template == "quick_in_1h":
        reminder_dt = current_dt + datetime.timedelta(hours=1)
        template_name = "Напоминание через 1 час"
    elif template == "quick_in_2h":
        reminder_dt = current_dt + datetime.timedelta(hours=2)
        template_name = "Напоминание через 2 часа"
    elif template == "quick_tomorrow_9":
        reminder_dt = (current_dt + datetime.timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        template_name = "Напоминание завтра в 9:00"
    elif template == "quick_tomorrow_18":
        reminder_dt = (current_dt + datetime.timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)
        template_name = "Напоминание завтра в 18:00"
    elif template == "quick_in_1week":
        reminder_dt = current_dt + datetime.timedelta(weeks=1)
        template_name = "Напоминание через неделю"
    else:
        await callback.answer("Неизвестный шаблон")
        return

    date_str = reminder_dt.strftime(FULL_DATE_FORMAT)
    time_str = reminder_dt.strftime(TIME_FORMAT)

    data = await state.get_data()
    bot_message_id = data['bot_message_id']

    await state.update_data(
        quick_template=template,
        dates=date_str,
        times=time_str,
        frequency=FREQUENCY_ZERO
    )

    await callback.message.edit_text(
        f"Шаблон: *{template_name}*\n"
        f"Дата: *{date_str}*\n"
        f"Время: *{time_str}*\n\n"
        f"Введите название напоминания:",
        reply_markup=inline_markup_cancel,
        parse_mode="Markdown"
    )
    await state.set_state(ReminderStates.waiting_for_quick_template_name)
    await callback.answer()


@router.callback_query(lambda c: c.data == "custom_reminder")
async def handle_custom_reminder(callback: types.CallbackQuery, state: FSMContext):
    """Handle custom reminder creation."""
    await callback.message.edit_text(
        "Введите название уведомления:",
        reply_markup=inline_markup_cancel
    )
    await state.set_state(ReminderStates.waiting_for_name)
    await callback.answer()


@router.message(ReminderStates.waiting_for_quick_template_name)
async def get_quick_template_name(message: types.Message, state: FSMContext):
    """Handle reminder name input for quick template."""
    await message.delete()
    data = await state.get_data()
    bot_message_id = data['bot_message_id']
    name_reminder = message.text
    dates = data['dates']
    times = data['times']
    frequency = data['frequency']

    user_id = message.from_user.id
    timezone = await get_user_timezone(user_id)
    current_dt = datetime.datetime.now(pytz.UTC)

    # Convert to UTC for storage
    finalized_date = finalize_date(dates, times, current_dt, timezone)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO reminders (user_id, name_reminder, frequency, dates, times, active) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, name_reminder, frequency, finalized_date, times, 1)
        )
        await db.commit()

    # Calculate when reminder will trigger
    reminder_dt = datetime.datetime.strptime(f"{dates} {times}", f"{FULL_DATE_FORMAT} {TIME_FORMAT}")
    reminder_dt = pytz.timezone(timezone).localize(reminder_dt)
    current_dt = datetime.datetime.now(pytz.timezone(timezone))
    time_diff = reminder_dt - current_dt

    # Format time difference
    if time_diff.days > 0:
        time_until = f"через {time_diff.days} дн. {time_diff.seconds // 3600} ч."
    elif time_diff.seconds >= 3600:
        hours = time_diff.seconds // 3600
        minutes = (time_diff.seconds % 3600) // 60
        time_until = f"через {hours} ч. {minutes} мин."
    else:
        minutes = time_diff.seconds // 60
        time_until = f"через {minutes} мин."

    await message.bot.edit_message_text(
        text=f"✅ Напоминание успешно добавлено!\n\n"
             f"📝 Название: *{name_reminder}*\n"
             f"📅 Дата: *{dates}*\n"
             f"🕐 Время: *{times}*\n\n"
             f"⏰ Напоминание сработает {time_until} (*{dates} в {times}*)",
        chat_id=message.chat.id,
        message_id=bot_message_id,
        parse_mode="Markdown"
    )
    await state.clear()


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
             f"Выберите частоту повторения или введите свою:",
        chat_id=message.chat.id,
        message_id=bot_message_id,
        reply_markup=inline_markup_frequency_presets,
        parse_mode="Markdown"
    )
    await state.set_state(ReminderStates.waiting_for_frequency)


@router.callback_query(lambda c: c.data.startswith("freq_"))
async def handle_frequency_preset(callback: types.CallbackQuery, state: FSMContext):
    """Handle frequency preset button selection."""
    current_state = await state.get_state()

    if current_state != ReminderStates.waiting_for_frequency:
        await callback.answer()
        return

    freq_data = callback.data
    data = await state.get_data()
    bot_message_id = data['bot_message_id']
    name_reminder = data['name_reminder']

    if freq_data == "freq_custom":
        # User wants to enter custom frequency
        await callback.message.edit_text(
            text=f"Название уведомления: *{name_reminder}*\n\n"
                 f"Введите частоту в формате '{FREQUENCY_ZERO}' для одноразового или '1min 1h 1d 1m 1y' "
                 f"(можно указать только часть):",
            reply_markup=inline_markup_cancel,
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    # Extract frequency from callback data (e.g., "freq_0" -> "0", "freq_1d" -> "1d")
    frequency = freq_data.replace("freq_", "")

    # Convert human-readable frequency to internal format
    freq_map = {
        "0": FREQUENCY_ZERO,
        "1d": "1d",
        "7d": "7d",
        "30d": "30d",
        "365d": "365d",
        "1h": "1h",
        "30min": "30min"
    }

    frequency = freq_map.get(frequency, frequency)

    # Determine human-readable description
    freq_display_map = {
        FREQUENCY_ZERO: "Не повторяется",
        "1d": "Каждый день",
        "7d": "Каждую неделю",
        "30d": "Каждый месяц",
        "365d": "Каждый год",
        "1h": "Каждый час",
        "30min": "Каждые 30 минут"
    }
    freq_display = freq_display_map.get(frequency, frequency)

    await state.update_data(frequency=frequency, selected_calendar_dates=[], calendar_mode=False)

    calendar_markup = create_calendar()

    await callback.message.edit_text(
        text=f"Название уведомления: *{name_reminder}*\n"
             f"Частота: *{freq_display}*\n\n"
             f"Выберите даты из календаря или введите даты в формате {DATE_FORMAT} или {FULL_DATE_FORMAT} "
             f"(можно несколько через запятую, например 15.10,16.10):",
        reply_markup=calendar_markup,
        parse_mode="Markdown"
    )
    await state.set_state(ReminderStates.waiting_for_date)
    await callback.answer()


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
    await state.update_data(frequency=frequency, selected_calendar_dates=[], calendar_mode=False)

    calendar_markup = create_calendar()

    await message.bot.edit_message_text(
        text=f"Название уведомления: *{name_reminder}*\n"
             f"Частота: *{frequency}*\n\n"
             f"Выберите даты из календаря или введите даты в формате {DATE_FORMAT} или {FULL_DATE_FORMAT} "
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

    data = await state.get_data()
    calendar_mode = data.get('calendar_mode', False)

    # If calendar mode is active, ignore text input
    if calendar_mode:
        return

    dates = message.text

    try:
        date_list = [date.strip() for date in dates.split(",")]
        resolved_dates = []
        for date in date_list:
            resolved_date, _ = resolve_date(date)
            resolved_dates.append(resolved_date)

        bot_message_id = data['bot_message_id']
        name_reminder = data['name_reminder']
        frequency = data['frequency']
        await state.update_data(dates=",".join(resolved_dates))

        await message.bot.edit_message_text(
            text=f"Название уведомления: *{name_reminder}*\n"
                 f"Частота: *{frequency}*\n"
                 f"Даты: *{','.join(resolved_dates)}*\n\n"
                 f"Выберите популярное время или введите свое в формате {TIME_FORMAT}:",
            chat_id=message.chat.id,
            message_id=bot_message_id,
            reply_markup=inline_markup_popular_times,
            parse_mode="Markdown"
        )
        await state.set_state(ReminderStates.waiting_for_time)
    except ValueError:
        bot_message_id = data['bot_message_id']
        name_reminder = data['name_reminder']
        frequency = data['frequency']

        # Reset selected calendar dates on error
        await state.update_data(selected_calendar_dates=[])
        calendar_markup = create_calendar()

        await message.bot.edit_message_text(
            text=f"Название уведомления: *{name_reminder}*\n"
                 f"Частота: *{frequency}*\n\n"
                 f"Пожалуйста, выберите даты из календаря или введите даты в формате {DATE_FORMAT} или {FULL_DATE_FORMAT} "
                 f"(можно несколько через запятую, например 15.10,16.10):",
            chat_id=message.chat.id,
            message_id=bot_message_id,
            reply_markup=calendar_markup,
            parse_mode="Markdown"
        )


@router.callback_query(lambda c: c.data.startswith("time_"))
async def handle_time_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle popular time button selection."""
    current_state = await state.get_state()

    if current_state != ReminderStates.waiting_for_time:
        await callback.answer()
        return

    time_data = callback.data

    if time_data == "time_custom":
        # User wants to enter custom time
        data = await state.get_data()
        bot_message_id = data['bot_message_id']
        name_reminder = data['name_reminder']
        frequency = data['frequency']
        dates = data['dates']

        await callback.message.edit_text(
            text=f"Название уведомления: *{name_reminder}*\n"
                 f"Частота: *{frequency}*\n"
                 f"Даты: *{dates}*\n\n"
                 f"Введите время в формате {TIME_FORMAT} (можно несколько через запятую):",
            reply_markup=inline_markup_cancel,
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    # Extract time from callback data (e.g., "time_09:00" -> "09:00")
    selected_time = time_data.replace("time_", "")

    # Process the selected time
    data = await state.get_data()
    user_id = callback.from_user.id
    name_reminder = data['name_reminder']
    frequency = data['frequency']
    dates = data['dates']
    timezone = await get_user_timezone(user_id)
    current_dt = datetime.datetime.now(pytz.UTC)

    date_list = dates.split(",")
    finalized_dates = []
    for date in date_list:
        finalized_date = finalize_date(date, selected_time, current_dt, timezone)
        if finalized_date not in finalized_dates:
            finalized_dates.append(finalized_date)
    finalized_dates.sort()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO reminders (user_id, name_reminder, frequency, dates, times, active, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, name_reminder, frequency, ",".join(finalized_dates), selected_time, 1, datetime.datetime.now(pytz.UTC).isoformat())
        )
        await db.commit()

    # Calculate when reminder will trigger
    user_tz = pytz.timezone(timezone)
    first_date_str = finalized_dates[0]
    reminder_dt = datetime.datetime.strptime(f"{first_date_str} {selected_time}", f"{FULL_DATE_FORMAT} {TIME_FORMAT}")
    reminder_dt = user_tz.localize(reminder_dt)
    current_dt_tz = datetime.datetime.now(user_tz)
    time_diff = reminder_dt - current_dt_tz

    # Format time difference
    if time_diff.days > 0:
        time_until = f"через {time_diff.days} дн. {time_diff.seconds // 3600} ч."
    elif time_diff.seconds >= 3600:
        hours = time_diff.seconds // 3600
        minutes = (time_diff.seconds % 3600) // 60
        time_until = f"через {hours} ч. {minutes} мин."
    else:
        minutes = time_diff.seconds // 60
        time_until = f"через {minutes} мин."

    bot_message_id = data['bot_message_id']
    await callback.message.edit_text(
        text=f"✅ Напоминание успешно добавлено!\n\n"
             f"📝 Название: *{name_reminder}*\n"
             f"🔁 Частота: *{frequency}*\n"
             f"📅 Даты: *{','.join(finalized_dates)}*\n"
             f"🕐 Время: *{selected_time}*\n\n"
             f"⏰ Следующее срабатывание {time_until} (*{first_date_str} в {selected_time}*)",
        parse_mode="Markdown"
    )
    await state.clear()
    await callback.answer("Напоминание создано!")


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
                'INSERT INTO reminders (user_id, name_reminder, frequency, dates, times, active, created_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                (user_id, name_reminder, frequency, ",".join(finalized_dates), ",".join(time_list), 1, datetime.datetime.now(pytz.UTC).isoformat())
            )
            await db.commit()

        # Calculate when reminder will trigger
        user_tz = pytz.timezone(timezone)
        first_date_str = finalized_dates[0]
        first_time_str = time_list[0]
        reminder_dt = datetime.datetime.strptime(f"{first_date_str} {first_time_str}", f"{FULL_DATE_FORMAT} {TIME_FORMAT}")
        reminder_dt = user_tz.localize(reminder_dt)
        current_dt_tz = datetime.datetime.now(user_tz)
        time_diff = reminder_dt - current_dt_tz

        # Format time difference
        if time_diff.days > 0:
            time_until = f"через {time_diff.days} дн. {time_diff.seconds // 3600} ч."
        elif time_diff.seconds >= 3600:
            hours = time_diff.seconds // 3600
            minutes = (time_diff.seconds % 3600) // 60
            time_until = f"через {hours} ч. {minutes} мин."
        else:
            minutes = time_diff.seconds // 60
            time_until = f"через {minutes} мин."

        bot_message_id = data['bot_message_id']
        await message.bot.edit_message_text(
            text=f"✅ Напоминание успешно добавлено!\n\n"
                 f"📝 Название: *{name_reminder}*\n"
                 f"🔁 Частота: *{frequency}*\n"
                 f"📅 Даты: *{','.join(finalized_dates)}*\n"
                 f"🕐 Время: *{times}*\n\n"
                 f"⏰ Следующее срабатывание {time_until} (*{first_date_str} в {first_time_str}*)",
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
    """List all active reminders with inline buttons and grouping."""
    user_id = message.from_user.id
    timezone = await get_user_timezone(user_id)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT id, name_reminder, frequency, dates, times, active '
            'FROM reminders WHERE user_id = ? AND active = 1',
            (user_id,)
        ) as cursor:
            reminders = await cursor.fetchall()

    if not reminders:
        await message.answer("У вас нет активных уведомлений.")
        return

    user_tz = pytz.timezone(timezone)
    current_dt = datetime.datetime.now(user_tz)
    today = current_dt.date()
    tomorrow = today + datetime.timedelta(days=1)
    week_end = today + datetime.timedelta(days=7)

    # Group reminders by time category
    groups = {
        "Сегодня": [],
        "Завтра": [],
        "На этой неделе": [],
        "Позже": []
    }

    for reminder in reminders:
        reminder_id, name, frequency, dates, times, active = reminder
        date_list = dates.split(",")

        # Find nearest date
        nearest_date = None
        for date_str in date_list:
            date_dt = datetime.datetime.strptime(date_str, FULL_DATE_FORMAT)
            date_local = date_dt.astimezone(user_tz).date()
            if nearest_date is None or date_local < nearest_date:
                nearest_date = date_local

        # Determine emoji based on frequency and proximity
        if frequency != FREQUENCY_ZERO:
            emoji = "🔄"
        elif nearest_date == today:
            emoji = "⏰"
        else:
            emoji = "🔔"

        reminder_data = (reminder_id, name, frequency, dates, times, nearest_date, emoji)

        # Categorize reminder
        if nearest_date == today:
            groups["Сегодня"].append(reminder_data)
        elif nearest_date == tomorrow:
            groups["Завтра"].append(reminder_data)
        elif nearest_date <= week_end:
            groups["На этой неделе"].append(reminder_data)
        else:
            groups["Позже"].append(reminder_data)

    # Send reminders grouped
    for group_name, group_reminders in groups.items():
        if not group_reminders:
            continue

        header = f"*{group_name}*\n\n"
        await message.answer(header, parse_mode="Markdown")

        for reminder_id, name, frequency, dates, times, nearest_date, emoji in group_reminders:
            date_list = dates.split(",")
            local_dates = []
            for date in date_list:
                date_dt = datetime.datetime.strptime(date, FULL_DATE_FORMAT)
                date_local = date_dt.astimezone(user_tz).strftime(FULL_DATE_FORMAT)
                if date_local not in local_dates:
                    local_dates.append(date_local)

            # Format frequency for display
            freq_display = "Не повторяется" if frequency == FREQUENCY_ZERO else f"Повторяется каждые {frequency}"

            card_text = (
                f"{emoji} *{name}*\n"
                f"📅 Даты: {', '.join(local_dates[:3])}" + ("..." if len(local_dates) > 3 else "") + "\n"
                f"🕐 Время: {times}\n"
                f"🔁 {freq_display}"
            )

            # Create inline buttons for each reminder
            inline_keyboard = [
                [
                    InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{reminder_id}"),
                    InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_confirm_{reminder_id}")
                ]
            ]
            markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

            await message.answer(card_text, reply_markup=markup, parse_mode="Markdown")


@router.callback_query(lambda c: c.data.startswith("delete_confirm_"))
async def delete_confirmation(callback: types.CallbackQuery):
    """Show delete confirmation dialog."""
    reminder_id = int(callback.data.split("_")[2])

    # Create confirmation buttons
    inline_keyboard = [
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_yes_{reminder_id}"),
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"delete_no_{reminder_id}")
        ]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    await callback.message.edit_text(
        "Вы уверены, что хотите удалить это напоминание?",
        reply_markup=markup
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("delete_yes_"))
async def delete_reminder_confirmed(callback: types.CallbackQuery):
    """Delete reminder after confirmation."""
    reminder_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    async with aiosqlite.connect(DB_PATH) as db:
        # Get reminder info before deleting for history
        async with db.execute(
            'SELECT name_reminder, frequency, dates, times FROM reminders WHERE id = ? AND user_id = ?',
            (reminder_id, user_id)
        ) as cursor:
            reminder_info = await cursor.fetchone()

        if not reminder_info:
            await callback.message.edit_text("Напоминание не найдено.")
            await callback.answer()
            return

        name, frequency, dates, times = reminder_info

        # Save to history
        completed_at = datetime.datetime.now(pytz.UTC).isoformat()
        await db.execute(
            'INSERT INTO reminder_history (reminder_id, user_id, name_reminder, frequency, dates, times, completed_at, action) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (reminder_id, user_id, name, frequency, dates, times, completed_at, 'deleted')
        )

        # Delete reminder
        await db.execute(
            'DELETE FROM reminders WHERE id = ? AND user_id = ?',
            (reminder_id, user_id)
        )
        await db.commit()

    await callback.message.edit_text("✅ Напоминание успешно удалено.")
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("delete_no_"))
async def delete_reminder_cancelled(callback: types.CallbackQuery):
    """Cancel reminder deletion."""
    reminder_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT name_reminder, frequency, dates, times FROM reminders WHERE id = ? AND user_id = ?',
            (reminder_id, user_id)
        ) as cursor:
            reminder_info = await cursor.fetchone()

    if reminder_info:
        name, frequency, dates, times = reminder_info
        timezone = await get_user_timezone(user_id)
        user_tz = pytz.timezone(timezone)

        date_list = dates.split(",")
        local_dates = []
        for date in date_list:
            date_dt = datetime.datetime.strptime(date, FULL_DATE_FORMAT)
            date_local = date_dt.astimezone(user_tz).strftime(FULL_DATE_FORMAT)
            if date_local not in local_dates:
                local_dates.append(date_local)

        emoji = "🔄" if frequency != FREQUENCY_ZERO else "🔔"
        freq_display = "Не повторяется" if frequency == FREQUENCY_ZERO else f"Повторяется каждые {frequency}"

        card_text = (
            f"{emoji} *{name}*\n"
            f"📅 Даты: {', '.join(local_dates[:3])}" + ("..." if len(local_dates) > 3 else "") + "\n"
            f"🕐 Время: {times}\n"
            f"🔁 {freq_display}"
        )

        inline_keyboard = [
            [
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{reminder_id}"),
                InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_confirm_{reminder_id}")
            ]
        ]
        markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

        await callback.message.edit_text(card_text, reply_markup=markup, parse_mode="Markdown")

    await callback.answer("Удаление отменено")


@router.message(F.text.startswith('/delete'))
async def handle_delete_command(message: types.Message):
    """Delete a reminder by ID (legacy command)."""
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

    await message.answer("✅ Напоминание успешно удалено.")


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

    action, year, month, day = separate_callback_data(callback.data)
    data = await state.get_data()
    selected_dates = data.get('selected_calendar_dates', [])
    calendar_mode = data.get('calendar_mode', False)

    # Convert string dates back to date objects if needed
    if selected_dates and isinstance(selected_dates[0], str):
        selected_dates = [datetime.datetime.strptime(d, FULL_DATE_FORMAT).date() for d in selected_dates]

    curr = datetime.date(year, month, 1)

    if action == "IGNORE":
        await callback.answer()
    elif action == "DAY":
        # Toggle date selection and switch to calendar-only mode
        selected_date = datetime.date(year, month, day)
        if selected_date in selected_dates:
            selected_dates.remove(selected_date)
            await callback.answer("Дата убрана")
        else:
            selected_dates.append(selected_date)
            await callback.answer("Дата добавлена")

        # Update state with selected dates and enable calendar mode
        await state.update_data(selected_calendar_dates=selected_dates, calendar_mode=True)

        # Update calendar with checkmarks and show selected dates
        calendar_markup = create_calendar(year, month, selected_dates)

        # Format selected dates for display
        selected_dates_sorted = sorted(selected_dates)
        selected_dates_str = ", ".join([d.strftime("%d.%m.%Y") for d in selected_dates_sorted])

        name_reminder = data['name_reminder']
        frequency = data['frequency']

        message_text = (
            f"Название уведомления: *{name_reminder}*\n"
            f"Частота: *{frequency}*\n\n"
        )

        if selected_dates:
            message_text += f"Выбранные даты:\n*{selected_dates_str}*\n\n"

        message_text += "Выберите даты из календаря:"

        await callback.message.edit_text(
            text=message_text,
            reply_markup=calendar_markup,
            parse_mode="Markdown"
        )

    elif action == "PREV-MONTH":
        pre = curr - datetime.timedelta(days=1)
        calendar_markup = create_calendar(pre.year, pre.month, selected_dates)
        await callback.message.edit_reply_markup(reply_markup=calendar_markup)
        await callback.answer()

    elif action == "NEXT-MONTH":
        ne = curr + datetime.timedelta(days=31)
        calendar_markup = create_calendar(ne.year, ne.month, selected_dates)
        await callback.message.edit_reply_markup(reply_markup=calendar_markup)
        await callback.answer()


@router.callback_query(lambda c: c.data == "clear_dates")
async def clear_calendar_dates(callback: types.CallbackQuery, state: FSMContext):
    """Clear all selected dates from calendar."""
    current_state = await state.get_state()

    if current_state != ReminderStates.waiting_for_date:
        await callback.answer()
        return

    data = await state.get_data()

    # Clear selected dates
    await state.update_data(selected_calendar_dates=[])

    # Get current calendar view
    callback_data = callback.message.reply_markup.inline_keyboard[0][0].callback_data
    if ";" in callback_data:
        _, year, month, _ = separate_callback_data(callback_data + ";0;0;0")
    else:
        now = datetime.datetime.now()
        year, month = now.year, now.month

    calendar_markup = create_calendar(year, month, [])

    name_reminder = data['name_reminder']
    frequency = data['frequency']

    await callback.message.edit_text(
        text=f"Название уведомления: *{name_reminder}*\n"
             f"Частота: *{frequency}*\n\n"
             f"Выберите даты из календаря:",
        reply_markup=calendar_markup,
        parse_mode="Markdown"
    )
    await callback.answer("Выбор очищен")


@router.callback_query(lambda c: c.data == "confirm_dates")
async def confirm_calendar_dates(callback: types.CallbackQuery, state: FSMContext):
    """Confirm selected dates from calendar."""
    current_state = await state.get_state()

    if current_state != ReminderStates.waiting_for_date:
        await callback.answer()
        return

    data = await state.get_data()
    selected_dates = data.get('selected_calendar_dates', [])

    if not selected_dates:
        await callback.answer("Выберите хотя бы одну дату!")
        return

    # Convert date objects to strings in FULL_DATE_FORMAT
    if isinstance(selected_dates[0], datetime.date):
        selected_dates_str = [d.strftime(FULL_DATE_FORMAT) for d in selected_dates]
    else:
        selected_dates_str = selected_dates

    # Sort dates
    selected_dates_sorted = sorted(selected_dates_str, key=lambda x: datetime.datetime.strptime(x, FULL_DATE_FORMAT))

    await state.update_data(dates=",".join(selected_dates_sorted))
    bot_message_id = data['bot_message_id']
    name_reminder = data['name_reminder']
    frequency = data['frequency']

    await callback.message.bot.edit_message_text(
        text=f"Название уведомления: *{name_reminder}*\n"
             f"Частота: *{frequency}*\n"
             f"Даты: *{','.join(selected_dates_sorted)}*\n\n"
             f"Выберите популярное время или введите свое в формате {TIME_FORMAT}:",
        chat_id=callback.message.chat.id,
        message_id=bot_message_id,
        reply_markup=inline_markup_popular_times,
        parse_mode="Markdown"
    )
    await state.set_state(ReminderStates.waiting_for_time)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("snooze_"))
async def handle_snooze(callback: types.CallbackQuery):
    """Handle snooze button clicks."""
    parts = callback.data.split("_")
    snooze_type = parts[1]
    reminder_id = int(parts[2])
    user_id = callback.from_user.id

    async with aiosqlite.connect(DB_PATH) as db:
        # Get reminder info
        async with db.execute(
            'SELECT name_reminder, expiration_time FROM reminders WHERE id = ? AND user_id = ?',
            (reminder_id, user_id)
        ) as cursor:
            reminder_info = await cursor.fetchone()

        if not reminder_info:
            await callback.answer("Напоминание не найдено.")
            return

        name, expiration_time = reminder_info
        timezone = await get_user_timezone(user_id)
        user_tz = pytz.timezone(timezone)
        current_dt = datetime.datetime.now(user_tz)

        # Calculate snooze time
        if snooze_type == "5":
            snooze_dt = current_dt + datetime.timedelta(minutes=5)
            snooze_text = "5 минут"
        elif snooze_type == "15":
            snooze_dt = current_dt + datetime.timedelta(minutes=15)
            snooze_text = "15 минут"
        elif snooze_type == "60":
            snooze_dt = current_dt + datetime.timedelta(hours=1)
            snooze_text = "1 час"
        elif snooze_type == "tomorrow":
            snooze_dt = (current_dt + datetime.timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            snooze_text = "завтра в 9:00"
        else:
            await callback.answer("Неизвестный тип отложения.")
            return

        new_date = snooze_dt.strftime(FULL_DATE_FORMAT)
        new_time = snooze_dt.strftime(TIME_FORMAT)

        # Update reminder with new date/time
        await db.execute(
            'UPDATE reminders SET dates = ?, times = ? WHERE id = ? AND user_id = ?',
            (new_date, new_time, reminder_id, user_id)
        )
        await db.commit()

    await callback.message.edit_text(
        f"✅ Напоминание '*{name}*' отложено на {snooze_text}",
        parse_mode="Markdown"
    )
    await callback.answer(f"Отложено на {snooze_text}")


@router.callback_query(lambda c: c.data.startswith(("delete_", "last_")))
async def delete_new_reminder(callback: types.CallbackQuery):
    """Mark reminder as done or delete temporary reminder."""
    callback_data = callback.data

    if callback_data.startswith("last_"):
        # For last temporary reminder, just change button to "doned ✅"
        reminder_id = int(callback_data.split("_")[1])

        # Save to history
        user_id = callback.from_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                'SELECT name_reminder, frequency, dates, times FROM reminders WHERE id = ? AND user_id = ?',
                (reminder_id, user_id)
            ) as cursor:
                reminder_info = await cursor.fetchone()

            if reminder_info:
                name, frequency, dates, times = reminder_info
                completed_at = datetime.datetime.now(pytz.UTC).isoformat()
                await db.execute(
                    'INSERT INTO reminder_history (reminder_id, user_id, name_reminder, frequency, dates, times, completed_at, action) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (reminder_id, user_id, name, frequency, dates, times, completed_at, 'completed')
                )
                await db.commit()

        inline_button_doned = InlineKeyboardButton(
            text="✅ Выполнено",
            callback_data=f"doned_{reminder_id}"
        )
        inline_markup_doned = InlineKeyboardMarkup(inline_keyboard=[[inline_button_doned]])
        await callback.message.edit_reply_markup(reply_markup=inline_markup_doned)
        await callback.answer("Напоминание отмечено как выполненное.")
    else:
        # Delete temporary reminder from database
        new_reminder_id = int(callback_data.split("_")[1])
        async with aiosqlite.connect(DB_PATH) as db:
            # Get reminder info for history
            async with db.execute(
                'SELECT name_reminder, frequency, dates, times FROM reminders WHERE id = ? AND user_id = ?',
                (new_reminder_id, callback.from_user.id)
            ) as cursor:
                reminder_info = await cursor.fetchone()

            if not reminder_info:
                await callback.answer("Напоминание не найдено.")
                return

            name, frequency, dates, times = reminder_info

            # Save to history
            completed_at = datetime.datetime.now(pytz.UTC).isoformat()
            await db.execute(
                'INSERT INTO reminder_history (reminder_id, user_id, name_reminder, frequency, dates, times, completed_at, action) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (new_reminder_id, callback.from_user.id, name, frequency, dates, times, completed_at, 'completed')
            )

            await db.execute(
                'DELETE FROM reminders WHERE id = ? AND user_id = ?',
                (new_reminder_id, callback.from_user.id)
            )
            await db.commit()

        inline_button_doned = InlineKeyboardButton(
            text="✅ Выполнено",
            callback_data=f"doned_{new_reminder_id}"
        )
        inline_markup_doned = InlineKeyboardMarkup(inline_keyboard=[[inline_button_doned]])
        await callback.message.edit_reply_markup(reply_markup=inline_markup_doned)
        await callback.answer("Напоминание успешно выполнено.")


@router.message(F.text == '📊 История')
async def show_history(message: types.Message):
    """Show reminder history and statistics."""
    user_id = message.from_user.id
    timezone = await get_user_timezone(user_id)
    user_tz = pytz.timezone(timezone)

    async with aiosqlite.connect(DB_PATH) as db:
        # Get statistics for the past week
        week_ago = (datetime.datetime.now(user_tz) - datetime.timedelta(days=7)).isoformat()

        async with db.execute(
            'SELECT COUNT(*) FROM reminder_history WHERE user_id = ? AND completed_at >= ?',
            (user_id, week_ago)
        ) as cursor:
            week_count = (await cursor.fetchone())[0]

        async with db.execute(
            'SELECT COUNT(*) FROM reminder_history WHERE user_id = ? AND action = "completed"',
            (user_id,)
        ) as cursor:
            total_completed = (await cursor.fetchone())[0]

        async with db.execute(
            'SELECT COUNT(*) FROM reminder_history WHERE user_id = ?',
            (user_id,)
        ) as cursor:
            total_count = (await cursor.fetchone())[0]

        # Get recent history (last 10 items)
        async with db.execute(
            'SELECT name_reminder, completed_at, action FROM reminder_history '
            'WHERE user_id = ? ORDER BY completed_at DESC LIMIT 10',
            (user_id,)
        ) as cursor:
            history_items = await cursor.fetchall()

    # Send statistics
    stats_text = (
        "📊 *Ваша статистика*\n\n"
        f"За последнюю неделю: {week_count} напоминаний\n"
        f"Всего выполнено: {total_completed}\n"
        f"Всего действий: {total_count}\n"
    )

    await message.answer(stats_text, parse_mode="Markdown")

    # Send history
    if history_items:
        history_text = "*Последние действия:*\n\n"

        for name, completed_at, action in history_items:
            completed_dt = datetime.datetime.fromisoformat(completed_at).astimezone(user_tz)
            date_str = completed_dt.strftime("%d.%m.%Y %H:%M")

            action_emoji = "✅" if action == "completed" else "🗑️"
            action_text = "выполнено" if action == "completed" else "удалено"

            history_text += f"{action_emoji} *{name}* - {action_text}\n📅 {date_str}\n\n"

        await message.answer(history_text, parse_mode="Markdown")
    else:
        await message.answer("История пуста")
