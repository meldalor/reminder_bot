"""Scheduler service for sending reminders."""

import datetime
import aiosqlite
import pytz

from bot.config import (
    DB_PATH,
    DATETIME_FORMAT,
    TIME_FORMAT,
    FULL_DATE_FORMAT,
    FREQUENCY_ZERO,
    REMINDER_OFFSET_MINUTES,
    TEMP_REMINDER_EXPIRATION_HOURS
)
from bot.database import get_user_timezone
from bot.keyboards import create_inline_keyboard
from bot.utils import calculate_next_datetime, shift_dates, shift_times


async def send_reminders(bot):
    """
    Check and send due reminders.

    Args:
        bot: Bot instance for sending messages
    """
    current_datetime_utc = datetime.datetime.now(pytz.UTC)

    async with aiosqlite.connect(DB_PATH) as db:
        # Delete expired temporary reminders
        await db.execute(
            'DELETE FROM reminders WHERE expiration_time IS NOT NULL AND expiration_time < ?',
            (current_datetime_utc.strftime(DATETIME_FORMAT),)
        )
        await db.commit()

        # Get all active reminders
        async with db.execute(
            'SELECT id, user_id, name_reminder, frequency, dates, times, '
            'expiration_time, last_message_id FROM reminders WHERE active = 1',
            ()
        ) as cursor:
            reminders = await cursor.fetchall()

        for reminder in reminders:
            (
                reminder_id, user_id, name_reminder, frequency,
                dates, times, expiration_time, last_message_id
            ) = reminder

            timezone = await get_user_timezone(user_id)
            if not timezone:
                continue

            user_tz = pytz.timezone(timezone)
            current_time_user = current_datetime_utc.astimezone(user_tz).strftime(TIME_FORMAT)
            current_date_user = current_datetime_utc.astimezone(user_tz).strftime(FULL_DATE_FORMAT)

            date_list = dates.split(",")
            if current_date_user not in date_list:
                continue

            time_list = times.split(",")
            if current_time_user not in time_list:
                continue

            current_dt = datetime.datetime.strptime(
                f"{current_date_user} {current_time_user}",
                f'{FULL_DATE_FORMAT} {TIME_FORMAT}'
            )
            current_dt = user_tz.localize(current_dt).astimezone(pytz.UTC)

            is_temporary = expiration_time is not None
            if is_temporary:
                expiration_dt = datetime.datetime.strptime(
                    expiration_time,
                    DATETIME_FORMAT
                ).replace(tzinfo=pytz.UTC)
                expiration_time_new = expiration_time
            else:
                expiration_dt = current_dt + datetime.timedelta(
                    hours=TEMP_REMINDER_EXPIRATION_HOURS
                )
                expiration_time_new = expiration_dt.strftime(DATETIME_FORMAT)

            # Delete previous reminder message
            if last_message_id:
                try:
                    await bot.delete_message(chat_id=user_id, message_id=last_message_id)
                except Exception:
                    pass

            # Create next temporary reminder if needed
            new_reminder_id = None
            next_dt = current_dt + datetime.timedelta(minutes=REMINDER_OFFSET_MINUTES)

            if next_dt < expiration_dt:
                new_date = next_dt.astimezone(user_tz).strftime(FULL_DATE_FORMAT)
                new_times = next_dt.astimezone(user_tz).strftime(TIME_FORMAT)
                await db.execute(
                    'INSERT INTO reminders (user_id, name_reminder, frequency, dates, '
                    'times, active, expiration_time) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (user_id, name_reminder, FREQUENCY_ZERO, new_date,
                     new_times, 1, expiration_time_new)
                )
                await db.commit()
                new_reminder_id = (await (await db.execute(
                    'SELECT last_insert_rowid()'
                )).fetchone())[0]

                # Create inline keyboard with snooze and done buttons
                inline_markup_new = create_inline_keyboard([
                    [("⏰ +5мин", f"snooze_5_{new_reminder_id}"), ("⏰ +15мин", f"snooze_15_{new_reminder_id}")],
                    [("⏰ +1час", f"snooze_60_{new_reminder_id}"), ("📅 Завтра", f"snooze_tomorrow_{new_reminder_id}")],
                    [("✅ Готово", f"delete_{new_reminder_id}")]
                ])
            else:
                # For last temporary reminder use current reminder_id
                inline_markup_new = create_inline_keyboard([
                    [("⏰ +5мин", f"snooze_5_{reminder_id}"), ("⏰ +15мин", f"snooze_15_{reminder_id}")],
                    [("⏰ +1час", f"snooze_60_{reminder_id}"), ("📅 Завтра", f"snooze_tomorrow_{reminder_id}")],
                    [("✅ Готово", f"last_{reminder_id}")]
                ])

            # Send reminder message
            message = await bot.send_message(
                user_id,
                f"🔔 Напоминание: *{name_reminder}*",
                reply_markup=inline_markup_new,
                parse_mode="Markdown"
            )

            # Update last_message_id
            if new_reminder_id:
                await db.execute(
                    'UPDATE reminders SET last_message_id = ? WHERE id = ?',
                    (message.message_id, new_reminder_id)
                )
            else:
                await db.execute(
                    'UPDATE reminders SET last_message_id = ? WHERE id = ?',
                    (message.message_id, reminder_id)
                )
            await db.commit()

            # Create next recurring reminder if this is the last time slot
            if current_time_user == time_list[-1] and current_date_user == date_list[-1]:
                if not is_temporary and frequency != FREQUENCY_ZERO:
                    last_date_dt = datetime.datetime.strptime(
                        date_list[-1],
                        FULL_DATE_FORMAT
                    )
                    last_date_dt = user_tz.localize(last_date_dt)
                    next_dt_original = calculate_next_datetime(last_date_dt, frequency)
                    new_dates_original = shift_dates(dates, frequency, user_tz)
                    new_times_original = shift_times(times, frequency, user_tz)

                    await db.execute(
                        'INSERT INTO reminders (user_id, name_reminder, frequency, '
                        'dates, times, active) VALUES (?, ?, ?, ?, ?, ?)',
                        (user_id, name_reminder, frequency, new_dates_original,
                         new_times_original, 1)
                    )
                    await db.commit()

                # Delete current reminder
                await db.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
                await db.commit()
