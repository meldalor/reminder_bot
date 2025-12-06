"""Handlers module for the bot."""

from .start import router as start_router
from .reminders import router as reminders_router
from .timezone import router as timezone_router

__all__ = ["start_router", "reminders_router", "timezone_router"]
