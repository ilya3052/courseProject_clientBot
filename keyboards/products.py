from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_products(data: list[str]):
    builder = InlineKeyboardBuilder()
    for item in data:
        builder.button(text=item[1], callback_data=f"product_{item[0]}")
    builder.adjust(3)

    static_builder = InlineKeyboardBuilder()
    static_builder.button(text="Назад", callback_data="action_previous"),
    static_builder.button(text="Далее", callback_data="action_next")

    builder.attach(static_builder)

    return builder.as_markup()
