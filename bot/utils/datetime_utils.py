"""Date and time utility functions."""

import datetime
import re
from dateutil.relativedelta import relativedelta
import pytz

from bot.config import (
    DATE_FORMAT,
    FULL_DATE_FORMAT,
    TIME_FORMAT,
    FREQUENCY_ZERO,
    TEMP_YEAR
)


def parse_frequency(frequency: str) -> dict:
    """
    Parse frequency string into time intervals.

    Args:
        frequency: Frequency string (e.g., "1d 2h 30min")

    Returns:
        Dictionary with intervals: {'min': 0, 'h': 0, 'd': 0, 'm': 0, 'y': 0}
    """
    intervals = {'min': 0, 'h': 0, 'd': 0, 'm': 0, 'y': 0}
    if frequency == FREQUENCY_ZERO:
        return intervals

    pattern = r'(\d+)(min|h|d|m|y)'
    matches = re.findall(pattern, frequency.lower())
    for value, unit in matches:
        intervals[unit] = int(value)
    return intervals


def calculate_next_datetime(
    current_datetime: datetime.datetime,
    frequency: str
) -> datetime.datetime:
    """
    Calculate next datetime based on frequency.

    Args:
        current_datetime: Current datetime
        frequency: Frequency string

    Returns:
        Next datetime
    """
    if frequency == FREQUENCY_ZERO:
        return current_datetime

    intervals = parse_frequency(frequency)
    dt = current_datetime + datetime.timedelta(
        days=intervals['d'],
        hours=intervals['h'],
        minutes=intervals['min']
    )
    dt = dt + relativedelta(
        years=intervals['y'],
        months=intervals['m']
    )
    return dt


def shift_times(times: str, frequency: str, user_tz: pytz.timezone) -> str:
    """
    Shift times based on frequency (minutes and hours only).

    Args:
        times: Comma-separated times
        frequency: Frequency string
        user_tz: User timezone

    Returns:
        Shifted times as comma-separated string
    """
    intervals = parse_frequency(frequency)
    if intervals['min'] == 0 and intervals['h'] == 0:
        return times

    time_list = times.split(",")
    shifted_times = []
    for time in time_list:
        time_dt = datetime.datetime.strptime(time, TIME_FORMAT)
        time_dt = user_tz.localize(time_dt)
        shifted_dt = time_dt + datetime.timedelta(
            hours=intervals['h'],
            minutes=intervals['min']
        )
        shifted_time = shifted_dt.strftime(TIME_FORMAT)
        shifted_times.append(shifted_time)
    return ",".join(shifted_times)


def shift_dates(dates: str, frequency: str, user_tz: pytz.timezone) -> str:
    """
    Shift dates based on frequency (days, months, years).

    Args:
        dates: Comma-separated dates
        frequency: Frequency string
        user_tz: User timezone

    Returns:
        Shifted dates as comma-separated string
    """
    intervals = parse_frequency(frequency)
    if intervals['d'] == 0 and intervals['m'] == 0 and intervals['y'] == 0:
        return dates

    date_list = dates.split(",")
    shifted_dates = []
    for date in date_list:
        date_dt = datetime.datetime.strptime(date, FULL_DATE_FORMAT)
        date_dt = user_tz.localize(date_dt)
        shifted_dt = date_dt + relativedelta(
            days=intervals['d'],
            months=intervals['m'],
            years=intervals['y']
        )
        shifted_date = shifted_dt.strftime(FULL_DATE_FORMAT)
        shifted_dates.append(shifted_date)
    return ",".join(shifted_dates)


def resolve_date(date_str: str) -> tuple[str, bool]:
    """
    Parse and resolve date string.

    Args:
        date_str: Date string in format DD.MM or DD.MM.YYYY

    Returns:
        Tuple of (parsed_date_string, is_full_date)
    """
    try:
        parsed_date = datetime.datetime.strptime(date_str, FULL_DATE_FORMAT)
        return parsed_date.strftime(FULL_DATE_FORMAT), True
    except ValueError:
        date_with_temp_year = f"{date_str}.{TEMP_YEAR}"
        parsed_date = datetime.datetime.strptime(date_with_temp_year, FULL_DATE_FORMAT)
        return parsed_date.strftime(DATE_FORMAT), False


def finalize_date(
    date_str: str,
    time_str: str,
    current_dt: datetime.datetime,
    user_timezone: str
) -> str:
    """
    Determine the correct year for a date.

    Args:
        date_str: Date string (DD.MM or DD.MM.YYYY)
        time_str: Time string (HH:MM)
        current_dt: Current datetime in UTC
        user_timezone: User's timezone string

    Returns:
        Date string in DD.MM.YYYY format
    """
    is_full_date = date_str.count('.') == 2
    if is_full_date:
        return date_str

    temp_date_time = f"{date_str}.{TEMP_YEAR} {time_str}"
    user_tz = pytz.timezone(user_timezone)
    parsed_dt = datetime.datetime.strptime(
        temp_date_time,
        f'{FULL_DATE_FORMAT} {TIME_FORMAT}'
    )
    parsed_dt = user_tz.localize(parsed_dt)
    current_dt_user = current_dt.astimezone(user_tz)

    parsed_day_month = (parsed_dt.day, parsed_dt.month)
    current_day_month = (current_dt_user.day, current_dt_user.month)

    if parsed_day_month < current_day_month:
        return parsed_dt.replace(year=current_dt_user.year + 1).strftime(FULL_DATE_FORMAT)
    return parsed_dt.replace(year=current_dt_user.year).strftime(FULL_DATE_FORMAT)
