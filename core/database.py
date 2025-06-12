import logging
import os
from typing import Union

import asyncpg
from asyncpg import Pool, Connection
from dotenv import load_dotenv

load_dotenv()


class Database:
    def __init__(self):
        self.pool: Union[Pool, None] = None
        self._listen_conn: Union[Connection, None] = None

    async def create_pool(self):
        user = os.getenv("USER")
        password = os.getenv("PASSWORD")
        database = os.getenv("DB_NAME")
        host = os.getenv("HOST")
        port = os.getenv("PORT")
        self.pool = await asyncpg.create_pool(user=user,
                                              password=password,
                                              database=database,
                                              host=host,
                                              port=port)

    async def execute(self, command: str, *args,
                      fetch: bool = False,
                      fetchval: bool = False,
                      fetchrow: bool = False,
                      execute: bool = False,
                      executemany: bool = False):
        async with self.pool.acquire() as connection:
            connection: Connection
            async with connection.transaction():
                if fetch:
                    result = await connection.fetch(command, *args)
                elif fetchval:
                    result = await connection.fetchval(command, *args)
                elif fetchrow:
                    result = await connection.fetchrow(command, *args)
                elif execute:
                    result = await connection.execute(command, *args)
                elif executemany:
                    result = await connection.executemany(command, *args)
        return result

    async def is_user_registered(self, user_id):
        query = """
               SELECT EXISTS(
                   SELECT 1 
                   FROM users 
                   WHERE user_tgchat_id = $1 AND user_role = 'user'
               )
           """
        try:
            result = await self.execute(query, user_id, fetchval=True)
            return bool(result)
        except Exception as e:
            logging.exception(f"Ошибка проверки регистрации: {e}")
            return False

    async def notify_channel(self, channel_name: str, payload: str):
        async with self.pool.acquire() as conn:
            await conn.execute(f"NOTIFY {channel_name}, '{payload.replace("'", "''")}'")
            logging.info(f"Отправлено уведомление на канал '{channel_name}': {payload}")

    async def listen_channel(self, channel_name: str, callback):
        if not self.pool:
            raise RuntimeError("Connection pool is not initialized. Call create_pool() first.")

        self._listen_conn = await self.pool.acquire()
        await self._listen_conn.add_listener(channel_name, callback)
        logging.info(f"Подписка на канал '{channel_name}' установлена")

    async def close(self):
        """Закрывает все соединения с базой данных"""
        if self._listen_conn:
            await self.pool.release(self._listen_conn)
            self._listen_conn = None
        if self.pool:
            await self.pool.close()
            self.pool = None
        logging.info("Все соединения с базой данных закрыты")


db = Database()


async def create_db() -> Database:
    await db.create_pool()
    return db
