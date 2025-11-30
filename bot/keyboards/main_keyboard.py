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
