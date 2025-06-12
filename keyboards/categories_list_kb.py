from aiogram.utils.keyboard import InlineKeyboardBuilder
from icecream import ic


def get_categories_kb(data: list[str]):
    builder = InlineKeyboardBuilder()
    for item in data:
        builder.button(text=item, callback_data=f"category_{item}")
    builder.adjust(3)

    static_builder = InlineKeyboardBuilder()
    static_builder.button(text="◀️ Предыдущая", callback_data="action_previous"),
    static_builder.button(text="Следующая ▶️", callback_data="action_next")
    static_builder.button(text="Закрыть каталог ❌", callback_data="action_close")
    static_builder.adjust(2)
    builder.attach(static_builder)

    return builder.as_markup()
