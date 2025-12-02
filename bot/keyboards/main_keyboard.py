"""Main keyboard layouts and utilities."""

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


def create_inline_keyboard(buttons: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    """
    Create inline keyboard from button list.

    Args:
        buttons: List of rows, each containing (text, callback_data) tuples

    Returns:
        InlineKeyboardMarkup instance
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=data) for text, data in row]
            for row in buttons
        ]
    )


# Main menu keyboard
button_add = KeyboardButton(text='+')
button_list = KeyboardButton(text='Мои уведомления')
button_setcity = KeyboardButton(text='Изменить часовой пояс')

keyboard = ReplyKeyboardMarkup(
    keyboard=[[button_add, button_list], [button_setcity]],
    resize_keyboard=True
)

# Cancel button
inline_markup_cancel = create_inline_keyboard([[("Отмена", "cancel")]])

# Quick templates for reminders
quick_template_buttons = [
    [("⏰ Через 1 час", "quick_in_1h"), ("⏰ Через 2 часа", "quick_in_2h")],
    [("🌅 Завтра в 9:00", "quick_tomorrow_9"), ("🌆 Завтра в 18:00", "quick_tomorrow_18")],
    [("📅 Через неделю", "quick_in_1week")],
    [("✏️ Создать свое", "custom_reminder")]
]
inline_markup_quick_templates = create_inline_keyboard(quick_template_buttons)

# Popular time buttons for custom reminders
popular_time_buttons = [
    [("09:00", "time_09:00"), ("12:00", "time_12:00"), ("15:00", "time_15:00")],
    [("18:00", "time_18:00"), ("21:00", "time_21:00")],
    [("✏️ Ввести свое время", "time_custom"), ("Отмена", "cancel")]
]
inline_markup_popular_times = create_inline_keyboard(popular_time_buttons)
