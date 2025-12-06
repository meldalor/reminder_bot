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

    # Get state data to check if this is onboarding
    data = await state.get_data()
    is_onboarding = data.get('is_onboarding', False)

    async with aiosqlite.connect(DB_PATH) as db:
        # Check if user exists
        async with db.execute(
            'SELECT user_id FROM users WHERE user_id = ?',
            (user_id,)
        ) as cursor:
            user_exists = await cursor.fetchone()

        if user_exists:
            await db.execute(
                'UPDATE users SET timezone = ? WHERE user_id = ?',
                (timezone, user_id)
            )
        else:
            await db.execute(
                'INSERT INTO users (user_id, timezone, onboarding_completed) VALUES (?, ?, ?)',
                (user_id, timezone, 0)
            )
        await db.commit()

    if is_onboarding:
        # Show tutorial after first timezone selection
        tutorial_text = (
            "🎓 *Быстрое обучение*\n\n"
            "*Как создать напоминание:*\n"
            "1️⃣ Нажмите кнопку '+'\n"
            "2️⃣ Выберите быстрый шаблон или создайте свое\n"
            "3️⃣ Укажите название, дату и время\n\n"
            "*Управление напоминаниями:*\n"
            "• *Мои уведомления* - список всех напоминаний\n"
            "• *История* - статистика и выполненные напоминания\n\n"
            "*При срабатывании напоминания:*\n"
            "⏰ Отложить на 5мин/15мин/1час/завтра\n"
            "✅ Отметить как выполненное\n\n"
            "Хотите попробовать создать первое напоминание?"
        )

        tutorial_buttons = [
            [("✅ Создать напоминание", "tutorial_create")],
            [("⏭️ Пропустить обучение", "tutorial_skip")]
        ]
        inline_markup_tutorial = create_inline_keyboard(tutorial_buttons)

        await callback.message.edit_text("✅ Часовой пояс успешно установлен!\n\n" + tutorial_text, reply_markup=inline_markup_tutorial, parse_mode="Markdown")
    else:
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
