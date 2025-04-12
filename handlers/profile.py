from aiogram import Router
from aiogram.filters import StateFilter, Command
from aiogram.types import Message
from psycopg import sql
router = Router()


@router.message(StateFilter(None), Command("profile"))
async def profile_command(message: Message):
    """
    Обращение (типа "добрый день, ...")
    Информация о количестве заказов, общая сумма всех заказов, наиболее часто заказываемая категория, статус текущей доставки, дата регистрации пользователя
    В кнопках: редактирование информации о профиле, просмотр заказов, доставок, экспорт информации о профиле, удаление профиля
    (в регистрацию добавить возможность импортировать информацию о профиле)
    (возможно получение информации сделать процедурой, экспорт информации однозначно процедура)
    """
    order_count = (sql.SQL(
        ""
    ))
    order_total_amount = (sql.SQL(
        ""
    ))
    most_ordered_category = (sql.SQL(
        ""
    ))
    pass