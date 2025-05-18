import asyncio

from core.bot import setup_bot
from core.logger import setup_logger
from core.notify import setup_notifications


async def main():
    setup_logger()
    await setup_notifications()
    await setup_bot()


if __name__ == "__main__":
    asyncio.run(main())
