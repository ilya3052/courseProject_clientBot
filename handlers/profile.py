from aiogram import Router
from aiogram.filters import StateFilter, Command
from aiogram.types import Message
import logging
from psycopg import sql
import psycopg as ps
from datetime import datetime as dt

from shared.database import Database

router = Router()


@router.message(StateFilter(None), Command("profile"))
async def profile_command(message: Message):
    """
    Обращение (типа "добрый день, ...")
    Информация о количестве заказов, общая сумма всех заказов, наиболее часто
    заказываемая категория, дата регистрации пользователя

    В кнопках: редактирование информации о профиле, просмотр заказов, доставок, экспорт информации о профиле,
    удаление профиля (в регистрацию добавить возможность импортировать информацию о профиле)
    (возможно получение информации сделать процедурой, экспорт информации однозначно процедура)
    """
    msg = await get_user_info(message)
    if msg:
        await message.answer(
            text=msg
        )



async def get_user_info(message: Message) -> str | None:
    connect: ps.connect = Database.get_connection()
    get_user_nickname = (sql.SQL(
        "SELECT client_nickname FROM client c JOIN users u on c.user_id = u.user_id WHERE u.user_id = {};"
    ))
    get_client_id = (sql.SQL(
        "SELECT client_id FROM client c JOIN users u on c.user_id = u.user_id WHERE u.user_id = {};"
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
    user_id = message.from_user.id
    with connect.cursor() as cur:
        try:
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

    time = dt.now().hour
    greeting = (
        "Доброй ночи" if 0 <= time < 6 else
        "Доброе утро" if 6 <= time < 12 else
        "Добрый день" if 12 <= time < 18 else
        "Добрый вечер"
    )
    hello_message = (f"👋🏼 {greeting}, {user_nickname}!\n"
                     f"🛒 Общее количество заказов: {order_count}\n"
                     f"💰 Общая сумма заказов: {order_total_amount or 0}\n"
                     f"📈 Больше всего заказывали в категориях: {', '.join([category[0] for category in most_ordered_category]) or "еще нет заказов"}\n"
                     f"📅 Дата регистрации: {register_date}\n")

    return hello_message
