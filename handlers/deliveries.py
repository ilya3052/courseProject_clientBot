from handlers.profile import send_notify


async def get_notify(conn, pid, channel, payload):
    order_id = int(str(payload).split(":")[1].strip())
    print(f"[{channel}] => {payload} => {order_id}")
    await send_notify(order_id)
