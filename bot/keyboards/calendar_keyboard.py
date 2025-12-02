"""Calendar keyboard for date selection in aiogram 3.x."""

import datetime
import calendar
from typing import List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def create_callback_data(action: str, year: int, month: int, day: int) -> str:
    """Create the callback data associated to each button."""
    return ";".join([action, str(year), str(month), str(day)])


def separate_callback_data(data: str) -> tuple:
    """Separate the callback data."""
    parts = data.split(";")
    return parts[0], int(parts[1]), int(parts[2]), int(parts[3])


def create_calendar(year: int = None, month: int = None, selected_dates: List[datetime.date] = None) -> InlineKeyboardMarkup:
    """
    Create an inline keyboard with the provided year and month.

    :param year: Year to use in the calendar, if None the current year is used.
    :param month: Month to use in the calendar, if None the current month is used.
    :param selected_dates: List of already selected dates to mark with checkmarks.
    :return: Returns the InlineKeyboardMarkup object with the calendar.
    """
    now = datetime.datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    if selected_dates is None:
        selected_dates = []

    data_ignore = create_callback_data("IGNORE", year, month, 0)
    keyboard = []

    # First row - Month and Year
    row = []
    month_name = calendar.month_name[month]
    row.append(InlineKeyboardButton(
        text=f"{month_name} {year}",
        callback_data=data_ignore
    ))
    keyboard.append(row)

    # Second row - Week Days
    row = []
    for day in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]:
        row.append(InlineKeyboardButton(text=day, callback_data=data_ignore))
    keyboard.append(row)

    # Calendar days
    my_calendar = calendar.monthcalendar(year, month)
    for week in my_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data=data_ignore))
            else:
                # Check if this date is selected
                current_date = datetime.date(year, month, day)
                is_selected = current_date in selected_dates
                day_text = f"✓ {day}" if is_selected else str(day)

                row.append(InlineKeyboardButton(
                    text=day_text,
                    callback_data=create_callback_data("DAY", year, month, day)
                ))
        keyboard.append(row)

    # Last row - Navigation buttons and action buttons
    row = []
    row.append(InlineKeyboardButton(
        text="<",
        callback_data=create_callback_data("PREV-MONTH", year, month, 1)
    ))
    row.append(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="cancel"
    ))
    row.append(InlineKeyboardButton(
        text=">",
        callback_data=create_callback_data("NEXT-MONTH", year, month, 1)
    ))
    keyboard.append(row)

    # Add clear and confirm buttons if any dates are selected
    if selected_dates:
        action_row = []
        action_row.append(InlineKeyboardButton(
            text="🗑️ Очистить",
            callback_data="clear_dates"
        ))
        action_row.append(InlineKeyboardButton(
            text=f"✅ Подтвердить ({len(selected_dates)})",
            callback_data="confirm_dates"
        ))
        keyboard.append(action_row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
