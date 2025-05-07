from aiogram.utils.keyboard import InlineKeyboardBuilder


def rate_courier_kb():
    builder = InlineKeyboardBuilder()
    for grade in range(1, 6):
        builder.button(text='⭐' * grade, callback_data=f'grade_{grade}')
    builder.adjust(3, 2)

    return builder.as_markup()
