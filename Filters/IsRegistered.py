import logging

from aiogram.filters import BaseFilter
from aiogram.types import Message

from core.database import db  # ваша обертка для asyncpg


class IsRegistered(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        try:
            user_id = message.from_user.id
            return await db.is_user_registered(user_id)
        except Exception as e:
            logging.exception(f"Ошибка базы данных в фильтре: {e}")
            return False
