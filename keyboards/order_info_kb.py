from aiogram.utils.keyboard import InlineKeyboardBuilder


def order_info_kb(status):
    builder = InlineKeyboardBuilder()
    if status == 1:
        builder.button(text="Подтвердить получение ✅", callback_data="action_confirmReceipt")
    builder.button(text="Вернуться назад ↩️️", callback_data="action_back")
    builder.adjust(1)

    return builder.as_markup()
