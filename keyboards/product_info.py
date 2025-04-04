from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_product_info_kb(added_to_cart: bool = False):
    builder = InlineKeyboardBuilder()
    if added_to_cart:
        builder.button(text="-", callback_data="count_decr")
        builder.button(text="+", callback_data="count_inc")
    else:
        builder.button(text="Добавить в корзину 🛒", callback_data="add_to_cart")
    builder.adjust(2)

    static_builder = InlineKeyboardBuilder()
    static_builder.button(text="◀️ Предыдущая", callback_data="action_previous"),
    static_builder.button(text="Следующая ▶️", callback_data="action_next")
    static_builder.button(text="Вернуться назад ↩️️", callback_data="action_back")
    static_builder.button(text="Отменить заказ ❌", callback_data="action_cancel")
    static_builder.adjust(2, 1, 1)

    builder.attach(static_builder)

    return builder.as_markup()
