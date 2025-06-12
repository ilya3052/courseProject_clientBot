import logging
from datetime import datetime as dt

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from asyncpg import PostgresError
from icecream import ic
from psycopg.errors import LockNotAvailable

from Filters.IsRegistered import IsRegistered
from core.bot_instance import bot
from core.database import db
from keyboards import get_orders_list_kb, get_delivery_kb
from keyboards import get_profile_kb, order_info_kb, get_rate_order_kb
from .register import cmd_start

router = Router()
page_size = 6


class Profile(StatesGroup):
    show_profile = State()
    show_orders = State()
    show_order = State()
    add_review = State()


@router.message(Command("profile"), IsRegistered())
async def handle_profile_message(message: Message, state: FSMContext):
    await handle_profile_common(message.chat.id, message.answer, state)


@router.callback_query(F.data == "profile", IsRegistered())
async def handle_profile_callback(callback: CallbackQuery, state: FSMContext):
    await handle_profile_common(callback.message.chat.id, callback.message.edit_text, state)
    await callback.answer()


@router.callback_query(F.data.startswith("get_"), StateFilter(Profile.show_profile), IsRegistered())
async def profile_action(callback: CallbackQuery, state: FSMContext):
    match callback.data.split("_")[1]:
        case "orders":
            await get_orders(callback, state)
            await state.set_state(Profile.show_orders)
    await callback.answer()


@router.callback_query(F.data.startswith("grade_"), StateFilter(Profile.show_order), IsRegistered())
async def rate_delivery(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    delivery_rating = int(callback.data.split("_")[1])
    order_id = data.get('order_id')
    try:
        async with db.pool.acquire() as connection:
            async with connection.transaction():
                await db.execute("SELECT rate_delivery($1, $2);", delivery_rating, order_id, execute=True)
    except PostgresError as p:
        logging.exception(f"При выполнении запроса произошла ошибка: {p}")
        return

    # await db.notify_channel('rate_delivery', '')

    answer = ("Пожалуйста, оставьте отзыв о доставке!" if delivery_rating == 5
              else "Пожалуйста, опишите что вам не понравилось" if delivery_rating == 4
    else "Приносим извинения за доставленные неудобства, пожалуйста, опишите проблему в сообщении. Мы примем меры как можно скорее!")

    await callback.answer()
    await callback.message.answer(
        f"{answer}\n(отправьте прочерк если не хотите оставлять отзыв)")
    await state.set_state(Profile.add_review)
    await state.update_data(order_id=order_id, delivery_rating=delivery_rating)


@router.message(F.text, StateFilter(Profile.add_review))
async def add_review(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get('order_id')
    delivery_rating = data.get('delivery_rating')
    update_review = "UPDATE \"order\" SET order_review = $1 WHERE order_id = $2"

    review = message.text
    try:
        async with db.pool.acquire() as connection:
            async with connection.transaction():
                await db.execute(update_review, review, order_id, execute=True)
    except PostgresError as p:
        logging.exception(f"Произошла ошибка при выполнении запроса: {p}")
        return

    answer = ("Благодарим за оставленный отзыв" if delivery_rating == 5 else
              "Спасибо за обратную связь!" if delivery_rating == 4 else
              "Спасибо за обратную связь, мы уже принимаем меры по улучшению качества работы!")
    await message.answer(answer)
    await state.set_state(None)


@router.callback_query(F.data.startswith("action_"), StateFilter(Profile.show_orders), IsRegistered())
async def orders_pagination(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    page = data.get('orders_page', 0)
    orders = data.get('orders_list', [])

    match callback.data.split("_")[1]:
        case "next":
            if (page + 1) * page_size < len(orders):
                await state.update_data(orders_page=page + 1)
        case "previous":
            if page > 0:
                await state.update_data(orders_page=page - 1)
        case "back":
            await state.clear()
            await callback.message.delete()
            msg = await get_user_info(callback.message.chat.id, state)
            if msg:
                await callback.message.answer(text=msg, reply_markup=get_profile_kb())
                await state.set_state(Profile.show_profile)
            return

    await show_orders(callback, state)


@router.callback_query(F.data.startswith('order_'), IsRegistered())
async def show_order(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order_id = data.get('order_id') or callback.data.split("_")[1]
    order_id = int(order_id)
    get_order_info = """SELECT o.order_id, o.order_status, u.user_surname, u.user_name, u.user_phonenumber, p.product_article, COUNT(p.product_article), p.product_name, p.product_price, o.order_address 
    FROM "order" o 
        JOIN added a ON o.order_id = a.order_id 
        JOIN product p ON a.product_article = p.product_article 
        JOIN delivery d ON o.order_id = d.order_id
        JOIN courier c ON d.courier_id = c.courier_id
        JOIN users u ON c.user_id = u.user_id
    WHERE o.order_id = $1
    GROUP BY o.order_id, u.user_surname, u.user_name, p.product_article, u.user_phonenumber;"""

    get_not_accept_order_info = """SELECT o.order_id, o.order_status, p.product_article, COUNT(p.product_article), p.product_name, p.product_price, o.order_address 
    FROM "order" o 
        JOIN added a ON o.order_id = a.order_id 
        JOIN product p ON a.product_article = p.product_article 
    WHERE o.order_id = $1
    GROUP BY o.order_id, p.product_article;"""

    is_order_accept = True

    try:
        order_info = await db.execute(get_order_info, order_id, fetch=True)
        if not order_info:
            order_info = await db.execute(get_not_accept_order_info, order_id, fetch=True)
            is_order_accept = False
    except PostgresError as e:
        logging.exception(f"Произошла ошибка при выполнении запроса {e}")
        await callback.answer()
        return
    except RuntimeWarning as R:
        logging.exception(f"Произошла ошибка при выполнении запроса: {R}")
        return

    if is_order_accept:
        msg = generate_accepted_order_info(order_info, order_id)
    else:
        msg = generate_non_accepted_order_info(order_info, order_id)
    await callback.message.edit_text(text=msg, reply_markup=order_info_kb(order_info[0][1]))
    await state.set_state(Profile.show_order)
    await state.update_data(order_id=order_id, msg=msg)


@router.callback_query(F.data.startswith("action_"), StateFilter(Profile.show_order), IsRegistered())
async def order_action(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    order_id = data.get('order_id', 1)
    match callback.data.split("_")[1]:
        case "confirmReceipt":
            await confirm_receipt(callback, state, order_id)
        case "retrySearch":
            await db.notify_channel('create_order', f'order_id: {order_id}')
        case "cancelOrder":
            await cancel_order(callback, state, order_id)
        case "back":
            await state.set_state(Profile.show_orders)
            await state.update_data(order_id=None)
            await show_orders(callback, state)
    await callback.answer()


@router.message(~IsRegistered())
@router.callback_query(~IsRegistered())
async def reg_handler(update: Message | CallbackQuery, state: FSMContext):
    message = update.message if isinstance(update, CallbackQuery) else update
    await cmd_start(message, state)


async def handle_profile_common(user_id: int, send_func, state: FSMContext):
    msg = await get_user_info(user_id, state)
    if msg:
        await send_func(text=msg, reply_markup=get_profile_kb())
        await state.set_state(Profile.show_profile)


async def get_orders(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client_id = data.get('client_id')
    if client_id is None:
        return

    query = "SELECT o.order_id FROM \"order\" o WHERE o.client_id = $1 ORDER BY o.order_id;"
    try:
        rows = await db.execute(query, client_id, fetch=True)
        orders = [r['order_id'] for r in rows]
    except PostgresError as e:
        logging.exception(f"Ошибка при получении заказов: {e}")
        return
    except RuntimeWarning as R:
        logging.exception(f"Произошла ошибка при выполнении запроса: {R}")
        return

    await state.update_data(orders_list=orders, orders_page=0)
    await show_orders(callback, state)


async def show_orders(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    orders = data.get('orders_list', [])
    page = data.get('orders_page', 0)

    if not orders:
        await callback.message.edit_text("У вас еще нет заказов.")
        return

    chunk = orders[page_size * page: page_size * (page + 1)]
    try:
        await callback.message.edit_text(
            f"Ваши заказы (страница {page + 1} из {((len(orders) - 1) // page_size) + 1}):",
            reply_markup=get_orders_list_kb(chunk)
        )
    except TelegramBadRequest as TBR:
        logging.exception(f"Произошла ошибка при выполнении запроса {TBR}")
    await callback.answer()


async def confirm_receipt(callback: CallbackQuery, state: FSMContext, order_id: int):
    data = await state.get_data()
    msg = data.get('msg')

    await callback.message.edit_text(text=f"{msg}\nПожалуйста оцените доставку!", reply_markup=get_rate_order_kb())
    try:
        async with db.pool.acquire() as connection:
            async with connection.transaction():
                if await db.execute("SELECT confirm_receipt($1)", order_id, fetchval=True) == 1:
                    raise PostgresError()
    except PostgresError as e:
        logging.exception(f"Произошла ошибка при выполнении запроса: {e}")


async def cancel_order(callback: CallbackQuery, state: FSMContext, order_id: int):
    ic(order_id)
    try:
        async with db.pool.acquire() as connection:
            async with connection.transaction():
                if await db.execute("SELECT cancel_order($1)", order_id, fetchval=True) == 1:
                    raise LockNotAvailable()
                await callback.answer("Заказ успешно удален..", show_alert=True)
        await handle_profile_callback(callback, state)
    except LockNotAvailable:
        await callback.answer("Заказ уже принят курьером!")
        return
    except PostgresError as p:
        logging.exception(f"Произошла ошибка при выполнении запроса: {p}")


async def send_notify(order_id: int, notify_type: str):
    get_client_id = "SELECT client_id FROM \"order\" WHERE order_id = $1;"
    get_user_tgchat_id = "SELECT u.user_tgchat_id FROM users u JOIN client c ON u.user_id = c.user_id WHERE c.client_id = $1;"
    try:
        client_id = await db.execute(get_client_id, order_id, fetchval=True)
        tgchat_id = await db.execute(get_user_tgchat_id, client_id, fetchval=True)
    except PostgresError as p:
        logging.exception(f"Произошла ошибка при выполнении запроса: {p}")
        return

    msg = ("Ваш заказ принят курьером! Ожидайте получения"
           if notify_type == "order_accept"
           else "К сожалению сейчас нет свободных курьеров, пожалуйста, откройте заказ и повторите попытку")

    await bot.send_message(chat_id=tgchat_id,
                           text=msg,
                           reply_markup=get_delivery_kb(order_id))


async def get_user_info(user_tgchat_id: int, state: FSMContext) -> str | None:
    get_user_id = "SELECT user_id FROM users WHERE user_tgchat_id = $1 AND user_role = 'user';"

    get_user_nickname = "SELECT c.client_nickname FROM client c JOIN users u on c.user_id = u.user_id WHERE u.user_id = $1;"

    get_client_id = "SELECT c.client_id FROM client c JOIN users u on c.user_id = u.user_id WHERE u.user_id = $1;"

    get_order_count = "SELECT COUNT(*) FROM \"order\" WHERE client_id = $1;"

    get_order_total_amount = """SELECT SUM(p.product_price) FROM product p 
        JOIN added a on a.product_article = p.product_article 
        JOIN \"order\" o on o.order_id = a.order_id 
        WHERE o.client_id = $1;"""

    get_most_ordered_category = """WITH user_category_stats AS (
    SELECT 
        p.product_category,
        COUNT(*) AS total_ordered
    FROM 
        users u
    JOIN 
        client c ON u.user_id = c.user_id
    JOIN 
        "order" o ON c.client_id = o.client_id
    JOIN 
        added a ON o.order_id = a.order_id
    JOIN 
        product p ON a.product_article = p.product_article
    WHERE 
        u.user_id = $1
    GROUP BY 
        p.product_category
),
max_ordered AS (
    SELECT MAX(total_ordered) AS max_count
    FROM user_category_stats
)
SELECT 
    ucs.product_category,
    ucs.total_ordered
FROM 
    user_category_stats ucs
CROSS JOIN 
    max_ordered mo
WHERE 
    ucs.total_ordered = mo.max_count
ORDER BY 
    ucs.product_category;
        """

    get_user_register_date = "SELECT client_registerdate FROM client WHERE user_id = $1;"

    try:
        user_id = await db.execute(get_user_id, user_tgchat_id, fetchval=True)
        user_nickname = await db.execute(get_user_nickname, user_id, fetchval=True)
        client_id = await db.execute(get_client_id, user_id, fetchval=True)
        order_count = await db.execute(get_order_count, client_id, fetchval=True)
        order_total_amount = await db.execute(get_order_total_amount, client_id, fetchval=True)
        most_ordered_category = await db.execute(get_most_ordered_category, user_id, fetch=True)
        register_date = await db.execute(get_user_register_date, user_id, fetchval=True)
    except PostgresError as e:
        logging.exception(f"Произошла ошибка при выполнении запроса {e}")

        return None
    await state.update_data(client_id=client_id)
    time = dt.now().hour
    greeting = (
        "Доброй ночи" if 0 <= time < 6 else
        "Доброе утро" if 6 <= time < 12 else
        "Добрый день" if 12 <= time < 18 else
        "Добрый вечер"
    )
    hello_message = (f"👋🏼 {greeting}, {user_nickname}!\n"
                     f"🛒 Общее количество заказов: {order_count}\n"
                     f"💰 Общая сумма заказов: {round(order_total_amount or 0, 2)}\n"
                     f"📈 Больше всего заказывали в категориях: {', '.join([category[0] for category in most_ordered_category]) or "еще нет заказов"}\n"
                     f"📅 Дата регистрации: {register_date}\n")

    return hello_message


def generate_accepted_order_info(order_info: list[tuple], order_id: int) -> str:
    status = order_info[0][1]
    order_status = (
        "Создан" if status == 0 else
        "Доставляется" if status == 1 else
        "Доставлен клиенту"
    )
    address = f"{order_info[0][9]}"
    courier = f"{order_info[0][2]} {order_info[0][3]}\nНомер телефона для связи: +{order_info[0][4]}" if status != 0 else "Не назначен"
    products = ""
    total_sum = 0
    for item in order_info:
        products += f"{item[5]} - {item[7]}, количество в заказе - {item[6]}\n"
        total_sum += item[6] * item[8]
    products += f"Общая сумма заказа: {total_sum}"
    msg = (f"Заказ №{order_id}\n"
           f"Статус заказа: {order_status}\n"
           f"Адрес заказа: {address}\n"
           f"Курьер: {courier}\n"
           f"Товары:\n"
           f"{products}\n")
    return msg


def generate_non_accepted_order_info(order_info: list[tuple], order_id: int) -> str:
    status = order_info[0][1]
    order_status = (
        "Создан" if status == 0 else
        "Доставляется" if status == 1 else
        "Доставлен клиенту"
    )
    address = f"{order_info[0][6]}"
    courier = "Не назначен"
    products = ""
    total_sum = 0
    for item in order_info:
        products += f"{item[2]} - {item[4]}, количество в заказе - {item[3]}\n"
        total_sum += item[3] * item[5]
    products += f"Общая сумма заказа: {total_sum}"
    msg = (f"Заказ №{order_id}\n"
           f"Статус заказа: {order_status}\n"
           f"Адрес заказа: {address}\n"
           f"Курьер: {courier}\n"
           f"Товары:\n"
           f"{products}\n")
    return msg
