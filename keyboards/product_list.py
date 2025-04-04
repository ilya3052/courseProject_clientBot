from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_products_list_kb(data: list[str]):
    builder = InlineKeyboardBuilder()
    for item in data:
        builder.button(text=item[1], callback_data=f"product_{item[0]}")
    builder.adjust(3)

    static_builder = InlineKeyboardBuilder()
    static_builder.button(text="◀️ Предыдущая", callback_data="action_previous"),
    static_builder.button(text="Следующая ▶️", callback_data="action_next")
    static_builder.button(text="Вернуться назад ↩️️", callback_data="action_back")
    static_builder.adjust(2)
    builder.attach(static_builder)

    return builder.as_markup()
