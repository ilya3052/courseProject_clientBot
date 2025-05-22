from handlers import get_notify
from .database import Database


async def setup_notifications():
    await Database.listen_channel("order_accept", get_notify)
    await Database.listen_channel("order_status", get_notify)
