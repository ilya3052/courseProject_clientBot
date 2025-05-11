import asyncio
import logging
import os
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from handlers import catalog_router, reg_router, profile_router
from shared.database import Database

log_path = os.path.join(os.path.dirname(__file__), "logs/client_bot_logs.log")

logging.basicConfig(
    level=logging.DEBUG,
    filename=log_path,
    filemode="a",
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="UTF-8"
)


async def main():
    try:
        bot = Bot(
            token=os.getenv("BOT_TOKEN"),
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML
            )
        )

        logging.info("Бот запущен")

        dp = Dispatcher()
        dp.include_router(reg_router)
        dp.include_router(profile_router)
        dp.include_router(catalog_router)

        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        logging.info("Завершение работы")
        logging.shutdown()
        await Database.close_connection()


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
