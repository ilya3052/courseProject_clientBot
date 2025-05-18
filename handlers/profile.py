import logging
from datetime import datetime as dt

import psycopg as ps
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from icecream import ic
from psycopg import sql
from psycopg.errors import LockNotAvailable

from Filters.IsRegistered import IsRegistered
from core.bot_instance import bot
from core.database import Database
from handlers.register import cmd_start
from keyboards import get_orders_list_kb, get_delivery_kb
from keyboards import get_profile_kb, order_info_kb, get_rate_order_kb

router = Router()
page_size = 3


class Profile(StatesGroup):
    show_profile = State()
    show_orders = State()
    show_order = State()


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


# оформить в качестве хранимой процедуры (вызов через callproc)
@router.callback_query(F.data.startswith("grade_"), StateFilter(Profile.show_order), IsRegistered())
async def rate_delivery(callback: CallbackQuery, state: FSMContext):
    connect: ps.connect = Database.get_connection()
    data = await state.get_data()
    delivery_rating = int(callback.data.split("_")[1])
    order_id = data.get('order_id')

    update_delivery_rating = sql.SQL("UPDATE delivery SET delivery_rating = {} WHERE order_id = {};")

    get_courier_id = sql.SQL("SELECT courier_id FROM delivery WHERE order_id = {};")
    get_courier_rating = sql.SQL("SELECT courier_rating FROM courier WHERE courier_id = {};")
    get_count_courier_orders = sql.SQL("""SELECT COUNT(*) 
    FROM delivery d 
    JOIN \"order\" o 
    ON d.order_id = o.order_id 
    WHERE d.courier_id = {} AND o.order_status = 2;""")

    update_courier_rating = sql.SQL("UPDATE courier SET courier_rating = {} WHERE courier_id = {};")

    with connect.cursor() as cur:
        try:
            cur.execute(update_delivery_rating.format(delivery_rating, order_id))

            courier_id = cur.execute(get_courier_id.format(order_id)).fetchone()[0]
            courier_rating = cur.execute(get_courier_rating.format(courier_id)).fetchone()[0]
            count_courier_orders = cur.execute(get_count_courier_orders.format(courier_id)).fetchone()[0]

            new_courier_rating = (count_courier_orders * courier_rating + delivery_rating) / (count_courier_orders + 1)
            cur.execute(update_courier_rating.format(round(new_courier_rating, 2), courier_id))

            connect.commit()
        except ps.Error as p:
            logging.exception(f"При выполнении запроса произошла ошибка: {p}")
            connect.rollback()

    await show_order(callback, state)


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
    connect: ps.connect = Database.get_connection()
    data = await state.get_data()
    order_id = data.get('order_id') or callback.data.split("_")[1]
    get_order_info = (sql.SQL(
        """SELECT o.order_id, o.order_status, u.user_surname, u.user_name, u.user_phonenumber, p.product_article, COUNT(p.product_article), p.product_name, p.product_price 
    FROM "order" o 
        JOIN added a ON o.order_id = a.order_id 
        JOIN product p ON a.product_article = p.product_article 
        JOIN delivery d ON o.order_id = d.order_id
        JOIN courier c ON d.courier_id = c.courier_id
        JOIN users u ON c.user_id = u.user_id
    WHERE o.order_id = {}
    GROUP BY o.order_id, u.user_surname, u.user_name, p.product_article, u.user_phonenumber;"""
    ))

    get_not_accept_order_info = (sql.SQL(
        """SELECT o.order_id, o.order_status, p.product_article, COUNT(p.product_article), p.product_name, p.product_price 
    FROM "order" o 
        JOIN added a ON o.order_id = a.order_id 
        JOIN product p ON a.product_article = p.product_article 
    WHERE o.order_id = {}
    GROUP BY o.order_id, p.product_article;"""
    ))

    is_order_accept = True

    with connect.cursor() as cur:
        try:
            order_info = cur.execute(get_order_info.format(order_id)).fetchall()
            if not order_info:
                order_info = cur.execute(get_not_accept_order_info.format(order_id)).fetchall()
                is_order_accept = False
                # raise Warning('Курьер еще не назначен на заказ!')
        except ps.Error as e:
            logging.exception(f"Произошла ошибка при выполнении запроса {e}")
            await callback.answer()
            return
        # except Warning as wr:
        # await callback.answer(str(wr), True)
        # return
    ic(order_info)
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
    ic(order_id)
    ic(callback.data.split("_")[1])
    match callback.data.split("_")[1]:
        case "confirmReceipt":
            await confirm_receipt(callback, state, order_id)
        case "retrySearch":
            await Database.notify_channel('create_order', f'order_id: {order_id}')
        case "cancelOrder":
            await cancel_order(callback, state, order_id)
        case "back":
            await state.set_state(Profile.show_orders)
            await state.update_data(order_id=None)
            await show_orders(callback, state)
    await callback.answer()

# @router.message(~IsRegistered())
# async def reg_handler(message: Message, state: FSMContext):
#     await cmd_start(message, state)
#
# @router.callback_query(~IsRegistered())
# async def reg_handler(callback: CallbackQuery, state: FSMContext):
#     await cmd_start(callback.message, state)

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
        # нет client_id — ничего не показываем
        return

    # получаем все order_id пользователя
    query = sql.SQL("SELECT o.order_id FROM \"order\" o WHERE o.client_id = %s;")
    connect: ps.connect = Database.get_connection()
    with connect.cursor() as cur:
        try:
            rows = cur.execute(query, (client_id,)).fetchall()
            orders = [r[0] for r in rows]
        except ps.Error as e:
            logging.exception(f"Ошибка при получении заказов: {e}")
            connect.rollback()
            return

    # сохраняем список заказов и сбрасываем страницу
    await state.update_data(orders_list=orders, orders_page=0)
    # показываем первую «страницу»
    await show_orders(callback, state)


async def show_orders(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ic(data)

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


# можно оформить как транзакцию внутри постгреса или функцию
async def confirm_receipt(callback: CallbackQuery, state: FSMContext, order_id: int):
    connect: ps.connect = Database.get_connection()
    data = await state.get_data()
    msg = data.get('msg')
    update_status = (sql.SQL(
        "UPDATE \"order\" SET order_status = 2 WHERE order_id = {};"
    ))
    get_courier_id = (sql.SQL(
        "SELECT c.courier_id FROM courier c JOIN delivery d ON d.courier_id = c.courier_id WHERE d.order_id = {};"
    ))

    update_courier_status = (sql.SQL(
        "UPDATE courier SET courier_is_busy_with_order = false WHERE courier_id = {};"
    ))
    await callback.message.edit_text(text=f"{msg}\nПожалуйста оцените доставку!", reply_markup=get_rate_order_kb())
    with connect.cursor() as cur:
        try:
            cur.execute(update_status.format(order_id))
            courier_id = cur.execute(get_courier_id.format(order_id)).fetchone()[0]
            cur.execute(update_courier_status.format(courier_id))
            connect.commit()
        except ps.Error as e:
            logging.exception(f"Произошла ошибка при выполнении запроса: {e}")
            connect.rollback()


# можно оформить как транзакцию внутри постгреса или функцию
async def cancel_order(callback: CallbackQuery, state: FSMContext, order_id: int):
    connect: ps.connect = Database.get_connection()
    try:
        with connect.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM \"order\" WHERE order_id = {} FOR UPDATE NOWAIT".format(order_id)).fetchone()
            cur.execute("DELETE FROM \"order\" WHERE order_id = {}".format(order_id))

            await callback.answer("Заказ успешно удален..", show_alert=True)
            connect.commit()
        await handle_profile_callback(callback, state)
    except LockNotAvailable:
        connect.rollback()
        await callback.answer("Заказ уже принят курьером!")
        return
    except ps.Error as p:
        logging.exception(f"Произошла ошибка при выполнении запроса: {p}")


async def send_notify(order_id: int, notify_type: str):
    connect: ps.connect = Database.get_connection()
    get_client_id = (sql.SQL(
        "SELECT client_id FROM \"order\" WHERE order_id = {};"
    ))
    get_user_tgchat_id = (sql.SQL(
        "SELECT u.user_tgchat_id FROM users u JOIN client c ON u.user_id = c.user_id WHERE c.client_id = {};"
    ))
    try:
        with connect.cursor() as cur:
            client_id = cur.execute(get_client_id.format(order_id)).fetchone()[0]
            tgchat_id = cur.execute(get_user_tgchat_id.format(client_id)).fetchone()[0]
    except ps.Error as p:
        logging.exception(f"Произошла ошибка при выполнении запроса: {p}")

    msg = ("Ваш заказ принят курьером! Ожидайте получения"
           if notify_type == "order_accept"
           else "К сожалению сейчас нет свободных курьеров, пожалуйста, откройте заказ и повторите попытку")

    await bot.send_message(chat_id=tgchat_id,
                           text=msg,
                           reply_markup=get_delivery_kb(order_id))


async def get_user_info(user_tgchat_id: int, state: FSMContext) -> str | None:
    connect: ps.connect = Database.get_connection()
    get_user_id = (sql.SQL(
        "SELECT user_id FROM users WHERE user_tgchat_id = {} AND user_role = 'user';"
    ))
    get_user_nickname = (sql.SQL(
        "SELECT c.client_nickname FROM client c JOIN users u on c.user_id = u.user_id WHERE u.user_id = {};"
    ))
    get_client_id = (sql.SQL(
        "SELECT c.client_id FROM client c JOIN users u on c.user_id = u.user_id WHERE u.user_id = {};"
    ))
    get_order_count = (sql.SQL(
        "SELECT COUNT(*) FROM \"order\" WHERE client_id = {};"
    ))
    get_order_total_amount = (sql.SQL(
        """SELECT SUM(p.product_price) FROM product p 
        JOIN added a on a.product_article = p.product_article 
        JOIN \"order\" o on o.order_id = a.order_id 
        WHERE o.client_id = {};"""
    ))
    get_most_ordered_category = (sql.SQL(
        """WITH user_category_stats AS (
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
        u.user_id = {}
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
    ))
    get_user_register_date = (sql.SQL(
        "SELECT client_registerdate FROM client WHERE user_id = {};"
    ))
    with connect.cursor() as cur:
        try:
            user_id = cur.execute(get_user_id.format(user_tgchat_id)).fetchone()[0]
            user_nickname = cur.execute(get_user_nickname.format(user_id)).fetchone()[0]
            client_id = cur.execute(get_client_id.format(user_id)).fetchone()[0]
            order_count = cur.execute(get_order_count.format(client_id)).fetchone()[0]
            order_total_amount = cur.execute(get_order_total_amount.format(client_id)).fetchone()[0]
            most_ordered_category = cur.execute(get_most_ordered_category.format(user_id)).fetchall()
            register_date = cur.execute(get_user_register_date.format(user_id)).fetchone()[0]
            connect.commit()
        except ps.Error as e:
            logging.exception(f"Произошла ошибка при выполнении запроса {e}")
            connect.rollback()
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
    courier = f"{order_info[0][2]} {order_info[0][3]}\nНомер телефона для связи: +{order_info[0][4]}" if status != 0 else "Не назначен"
    products = ""
    total_sum = 0
    for item in order_info:
        products += f"{item[5]} - {item[7]}, количество в заказе - {item[6]}\n"
        total_sum += item[6] * item[8]
    products += f"Общая сумма заказа: {total_sum}"
    msg = (f"Заказ №{order_id}\n"
           f"Статус заказа: {order_status}\n"
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
    courier = "Не назначен"
    products = ""
    total_sum = 0
    for item in order_info:
        products += f"{item[2]} - {item[4]}, количество в заказе - {item[3]}\n"
        total_sum += item[3] * item[5]
    products += f"Общая сумма заказа: {total_sum}"
    msg = (f"Заказ №{order_id}\n"
           f"Статус заказа: {order_status}\n"
           f"Курьер: {courier}\n"
           f"Товары:\n"
           f"{products}\n")
    return msg
