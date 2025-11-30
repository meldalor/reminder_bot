"""Timezone selection handlers."""

import aiosqlite
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from bot.config import CITY_TIMEZONES, DB_PATH
from bot.keyboards import keyboard, create_inline_keyboard
from bot.states import ReminderStates

router = Router()


@router.message(F.text == 'Изменить часовой пояс')
async def set_city_command(message: types.Message, state: FSMContext):
    """Handle timezone change request."""
    city_buttons = [[(city, f"city_{city}")] for city in CITY_TIMEZONES.keys()]
    city_buttons.append([("Отмена", "cancel_city")])
    inline_markup_cities = create_inline_keyboard(city_buttons)

    msg = await message.answer(
        "Пожалуйста, выберите ваш город, соответствующий вашему часовому поясу, из списка:",
        reply_markup=inline_markup_cities
    )
    await state.update_data(bot_message_id=msg.message_id)
    await state.set_state(ReminderStates.waiting_for_city)


@router.callback_query(lambda c: c.data.startswith("city_"))
async def select_city(callback: types.CallbackQuery, state: FSMContext):
    """Handle city selection."""
    city = callback.data.split("_", 1)[1]
    user_id = callback.from_user.id
    timezone = CITY_TIMEZONES[city]

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT OR REPLACE INTO users (user_id, timezone) VALUES (?, ?)',
            (user_id, timezone)
        )
        await db.commit()

    await callback.message.edit_text("Часовой пояс успешно установлен!", reply_markup=None)
    await callback.message.answer("Выбери действие:", reply_markup=keyboard)
    await state.clear()
    await callback.answer()


@router.callback_query(lambda c: c.data == "cancel_city")
async def cancel_city_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle city selection cancellation."""
    await state.clear()
    await callback.message.edit_text("Выбор часового пояса отменен.", reply_markup=None)
    await callback.message.answer("Выбери действие:", reply_markup=keyboard)
    await callback.answer()
