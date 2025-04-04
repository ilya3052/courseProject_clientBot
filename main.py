import asyncio
import logging
import os
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from handlers import catalog, register
from shared.database import Database

log_path = os.path.join(os.path.dirname(__file__), "logs/client_bot_logs.log")

logging.basicConfig(
    level=logging.DEBUG,
    filename=log_path,
    filemode="a",
    format="%(asctime)s %(levelname)s [User: %(user_id)s, State: %(state)s] %(message)s",
    encoding="UTF-8"
)

def log_event(message: str, chat_id: Optional[int] = None, user_id: Optional[int] = None, state: Optional[str] = None, error: str = None, level: str = "info"):
    match level:
        case "info":
            logging.info(
                message,
                extra={
                    'chat_id': chat_id or 'N/A',
                    'user_id': user_id or 'N/A',
                    'state': state or 'N/A',
                    'error': error or 'N/A'
                }
            )
        case "error":
            logging.error(
                message,
                extra={
                    'chat_id': chat_id or 'N/A',
                    'user_id': user_id or 'N/A',
                    'state': state or 'N/A',
                    'error': error or 'N/A'
                }
            )
        case "critical":
            logging.critical(
                message,
                extra={
                    'chat_id': chat_id or 'N/A',
                    'user_id': user_id or 'N/A',
                    'state': state or 'N/A',
                    'error': error or 'N/A'
                }
            )

async def main():
    try:
        bot = Bot(
            token=os.getenv("BOT_TOKEN"),
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML
            )
        )

        log_event("Бот запущен")

        dp = Dispatcher()
        dp.include_router(register.router)
        dp.include_router(catalog.router)

        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        log_event("Завершение работы")
        logging.shutdown()
        Database.close_connection()


if __name__ == "__main__":
    asyncio.run(main())
