from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_profile_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="Мои заказы", callback_data="get_orders")

    return builder.as_markup()
