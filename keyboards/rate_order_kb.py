from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_rate_order_kb():
    builder = InlineKeyboardBuilder()
    for grade in range(1, 6):
        builder.button(text='⭐' * grade, callback_data=f'grade_{grade}')
    builder.button(text="Вернуться назад ↩️️", callback_data="action_back")
    builder.adjust(3, 2, 1)

    return builder.as_markup()
