from aiogram.utils.keyboard import InlineKeyboardBuilder


def order_info_kb(status):
    builder = InlineKeyboardBuilder()
    if status == 0:
        builder.button(text="Повторить поиск курьера 🔁", callback_data="action_retrySearch")
        builder.button(text="Отказаться от заказа ❌", callback_data="action_cancelOrder")
    elif status == 1:
        builder.button(text="Подтвердить получение ✅", callback_data="action_confirmReceipt")
    builder.button(text="Вернуться назад ↩️️", callback_data="action_back")
    builder.adjust(1)

    return builder.as_markup()
