from aiogram import Router
from aiogram.filters import StateFilter, Command
from aiogram.types import Message
from psycopg import sql

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

    await message.answer(

    )
    pass


async def get_user_info(message: Message) -> str:
    get_user_nickname = (sql.SQL(
        "SELECT user_nickname FROM user WHERE user_id = {};"
    ))
    get_client_id = (sql.SQL(
        "SELECT client_id FROM client c JOIN user u on c.user_id = u.user_id WHERE u.user_id = {};"
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
        u.user_id = 890424375  -- Здесь подставьте ID нужного пользователя
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
        "SELECT client_registerdate FROM client WHERE user_id = {}:"
    ))

    hello_message = (f"👋🏼 Добрый день, {}!\n"
                     f"🛒 Общее количество заказов: {}\n"
                     f"💰 Общая сумма заказов: {}\n"
                     f"📅 Дата регистрации: {}\n")

    return hello_message
