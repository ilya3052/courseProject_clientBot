from handlers import get_notify
from .database import db


async def setup_notifications():
    await db.listen_channel("order_accept", get_notify)
    await db.listen_channel("order_status", get_notify)
