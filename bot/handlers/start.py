"""Start command handler."""

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.config import CITY_TIMEZONES
from bot.database import get_user_timezone
from bot.keyboards import keyboard, create_inline_keyboard
from bot.states import ReminderStates

router = Router()


@router.message(Command(commands=['start']))
async def start(message: types.Message, state: FSMContext):
    """Handle /start command."""
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
        await message.answer("Выбери действие:", reply_markup=keyboard)
