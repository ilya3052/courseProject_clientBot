import asyncio
import logging
import os

import psycopg as ps
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from shared.database import Database
from handlers import register

log_path = os.path.join(os.path.dirname(__file__), "../logs/client_bot_logs.log")

logging.basicConfig(
    level=logging.INFO,
    filename=log_path,
    filemode="a",
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="UTF-8"
)

bot = Bot(
    token=os.getenv("CLIENT_BOT_TOKEN"),
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

logging.info("Бот запущен")
connect: ps.connect = Database.get_connection()

logging.info("Соединение создано")

dp = Dispatcher()
dp.include_router(register.router)


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
