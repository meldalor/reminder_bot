"""FSM states for the bot."""

from aiogram.fsm.state import State, StatesGroup


class ReminderStates(StatesGroup):
    """States for reminder creation flow."""
    waiting_for_template_choice = State()
    waiting_for_name = State()
    waiting_for_frequency = State()
    waiting_for_date = State()
    waiting_for_date_calendar_only = State()
    waiting_for_time = State()
    waiting_for_city = State()
    waiting_for_quick_template_name = State()
    editing_reminder = State()
    viewing_history = State()
