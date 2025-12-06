"""Start command handler."""

import aiosqlite
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.config import CITY_TIMEZONES, DB_PATH
from bot.database import get_user_timezone
from bot.keyboards import keyboard, create_inline_keyboard
from bot.states import ReminderStates

router = Router()


@router.message(Command(commands=['start']))
async def start(message: types.Message, state: FSMContext):
    """Handle /start command with onboarding."""
    user_id = message.from_user.id
    timezone = await get_user_timezone(user_id)

    # Check if user completed onboarding
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT onboarding_completed FROM users WHERE user_id = ?',
            (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            onboarding_completed = result[0] if result else 0

    if timezone is None:
        # Show welcome message with timezone selection
        welcome_text = (
            "👋 *Добро пожаловать в бот напоминаний!*\n\n"
            "С помощью этого бота вы сможете:\n"
            "🔔 Создавать напоминания с гибкими настройками\n"
            "📅 Выбирать даты через удобный календарь\n"
            "🔄 Настраивать повторяющиеся напоминания\n"
            "⏰ Откладывать напоминания на нужное время\n"
            "📊 Просматривать историю и статистику\n\n"
            "Для начала выберите ваш часовой пояс:"
        )

        city_buttons = [[(city, f"city_{city}")] for city in CITY_TIMEZONES.keys()]
        inline_markup_cities = create_inline_keyboard(city_buttons)
        msg = await message.answer(
            welcome_text,
            reply_markup=inline_markup_cities,
            parse_mode="Markdown"
        )
        await state.update_data(bot_message_id=msg.message_id, is_onboarding=True)
        await state.set_state(ReminderStates.waiting_for_city)
    elif not onboarding_completed:
        # Show tutorial
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

        await message.answer(tutorial_text, reply_markup=inline_markup_tutorial, parse_mode="Markdown")
    else:
        await message.answer("Выбери действие:", reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "tutorial_create")
async def tutorial_create(callback: types.CallbackQuery, state: FSMContext):
    """Start tutorial reminder creation."""
    user_id = callback.from_user.id

    # Mark onboarding as completed
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'UPDATE users SET onboarding_completed = 1 WHERE user_id = ?',
            (user_id,)
        )
        await db.commit()

    await callback.message.edit_text(
        "Отлично! Давайте создадим ваше первое напоминание.\n\n"
        "Нажмите кнопку '+' внизу, чтобы начать.",
        parse_mode="Markdown"
    )
    await callback.message.answer("Выбери действие:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(lambda c: c.data == "tutorial_skip")
async def tutorial_skip(callback: types.CallbackQuery, state: FSMContext):
    """Skip tutorial."""
    user_id = callback.from_user.id

    # Mark onboarding as completed
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'UPDATE users SET onboarding_completed = 1 WHERE user_id = ?',
            (user_id,)
        )
        await db.commit()

    await callback.message.edit_text("Хорошо! Вы всегда можете вызвать /start для справки.")
    await callback.message.answer("Выбери действие:", reply_markup=keyboard)
    await callback.answer()
