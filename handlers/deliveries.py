# from handlers.profile import send_notify


async def get_notify(conn, pid, channel, payload):
    notify_type = payload.split(";")[0].split(":")[1].strip()
    order_id = int(payload.split(";")[1].split(":")[1].strip())
    # await send_notify(order_id, notify_type)
