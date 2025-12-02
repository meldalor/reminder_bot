"""Keyboard layouts for the bot."""

from .main_keyboard import (
    keyboard,
    inline_markup_cancel,
    create_inline_keyboard,
    inline_markup_quick_templates,
    inline_markup_popular_times
)
from .calendar_keyboard import create_calendar, separate_callback_data

__all__ = [
    "keyboard",
    "inline_markup_cancel",
    "create_inline_keyboard",
    "inline_markup_quick_templates",
    "inline_markup_popular_times",
    "create_calendar",
    "separate_callback_data"
]
