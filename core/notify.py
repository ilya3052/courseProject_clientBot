from .database import Database
from handlers import get_notify


async def setup_notifications():
    await Database.listen_channel("order_accept", get_notify)
    await Database.listen_channel("order_not_accept", get_notify)