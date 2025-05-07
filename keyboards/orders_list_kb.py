from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_orders_list_kb(data):
    builder = InlineKeyboardBuilder()
    for item in data:
        builder.button(text=str(item), callback_data=f"order_{item}")
    builder.adjust(3)

    static_builder = InlineKeyboardBuilder()
    static_builder.button(text="◀️ Предыдущая", callback_data="action_previous"),
    static_builder.button(text="Следующая ▶️", callback_data="action_next")
    static_builder.button(text="Вернуться назад ↩️️", callback_data="action_back")
    static_builder.adjust(2, 1)

    builder.attach(static_builder)

    return builder.as_markup()
