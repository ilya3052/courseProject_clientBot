from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_categories_kb(data: list[str]):
    builder = InlineKeyboardBuilder()
    for item in data:
        builder.button(text=item, callback_data=f"category_{item}")
    builder.adjust(3)

    return builder.as_markup()
