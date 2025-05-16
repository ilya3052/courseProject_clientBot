from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_delivery_kb(order_id: int):
    builder = InlineKeyboardBuilder()

    builder.button(text="Открыть заказ", callback_data=f"order_{order_id}")

    return builder.as_markup()
