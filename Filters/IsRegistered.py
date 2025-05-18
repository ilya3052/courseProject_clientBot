from aiogram.filters import BaseFilter
from aiogram.types import Message
from typing import Callable
from database import Database  # ваша обертка для asyncpg

class IsRegistered(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        try:
            user_id = message.from_user.id
            return await Database.is_user_registered(user_id)
        except Exception as e:
            # Например, база недоступна
            print(f"DB error in IsRegistered filter: {e}")
            return False