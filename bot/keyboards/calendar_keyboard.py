"""Calendar keyboard for date selection in aiogram 3.x."""

import datetime
import calendar
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def create_callback_data(action: str, year: int, month: int, day: int) -> str:
    """Create the callback data associated to each button."""
    return ";".join([action, str(year), str(month), str(day)])


def separate_callback_data(data: str) -> tuple:
    """Separate the callback data."""
    parts = data.split(";")
    return parts[0], int(parts[1]), int(parts[2]), int(parts[3])


def create_calendar(year: int = None, month: int = None) -> InlineKeyboardMarkup:
    """
    Create an inline keyboard with the provided year and month.

    :param year: Year to use in the calendar, if None the current year is used.
    :param month: Month to use in the calendar, if None the current month is used.
    :return: Returns the InlineKeyboardMarkup object with the calendar.
    """
    now = datetime.datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

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
                row.append(InlineKeyboardButton(
                    text=str(day),
                    callback_data=create_callback_data("DAY", year, month, day)
                ))
        keyboard.append(row)

    # Last row - Navigation buttons and Cancel
    row = []
    row.append(InlineKeyboardButton(
        text="<",
        callback_data=create_callback_data("PREV-MONTH", year, month, 1)
    ))
    row.append(InlineKeyboardButton(
        text="Отмена",
        callback_data="cancel"
    ))
    row.append(InlineKeyboardButton(
        text=">",
        callback_data=create_callback_data("NEXT-MONTH", year, month, 1)
    ))
    keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def process_calendar_selection(callback_query, callback_data: str) -> tuple:
    """
    Process the callback_query for calendar navigation.

    :param callback_query: The callback query from aiogram
    :param callback_data: The callback data string
    :return: Returns a tuple (Boolean, datetime.date), indicating if a date is selected
    """
    ret_data = (False, None)
    action, year, month, day = separate_callback_data(callback_data)
    curr = datetime.date(year, month, 1)

    if action == "IGNORE":
        await callback_query.answer()
    elif action == "DAY":
        await callback_query.answer()
        ret_data = True, datetime.date(year, month, day)
    elif action == "PREV-MONTH":
        pre = curr - datetime.timedelta(days=1)
        await callback_query.message.edit_reply_markup(
            reply_markup=create_calendar(pre.year, pre.month)
        )
        await callback_query.answer()
    elif action == "NEXT-MONTH":
        ne = curr + datetime.timedelta(days=31)
        await callback_query.message.edit_reply_markup(
            reply_markup=create_calendar(ne.year, ne.month)
        )
        await callback_query.answer()
    else:
        await callback_query.answer("Что-то пошло не так!")

    return ret_data
