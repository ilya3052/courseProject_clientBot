import logging

from .bot_instance import bot, dp
from handlers import catalog_router, reg_router, profile_router


async def setup_bot():
    dp.include_router(reg_router)
    dp.include_router(profile_router)
    dp.include_router(catalog_router)

    logging.info("Бот запущен")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
