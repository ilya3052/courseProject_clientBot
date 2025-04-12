from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_product_info_kb(added_to_cart: bool = False):
    builder = InlineKeyboardBuilder()
    if added_to_cart:
        builder.button(text="-", callback_data="count_dec")
        builder.button(text="+", callback_data="count_inc")
        builder.button(text="◀️ Предыдущая", callback_data="action_previous"),
        builder.button(text="Следующая ▶️", callback_data="action_next")
        builder.button(text="Подтвердить заказ ✅", callback_data="action_confirm")
        builder.button(text="Вернуться назад ↩️️", callback_data="action_back")
        builder.button(text="Отменить заказ ❌", callback_data="action_cancel")
        builder.adjust(2, 2, 1, 1, 1)
    else:
        builder.button(text="Добавить в корзину 🛒", callback_data="action_addToCart")
        builder.button(text="◀️ Предыдущая", callback_data="action_previous"),
        builder.button(text="Следующая ▶️", callback_data="action_next")
        builder.button(text="Вернуться назад ↩️️", callback_data="action_back")
        builder.button(text="Отменить заказ ❌", callback_data="action_cancel")
        builder.adjust(1, 2, 1, 1)


    return builder.as_markup()
