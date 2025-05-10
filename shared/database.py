import logging
import os
import sys

import psycopg as ps
from dotenv import load_dotenv
from psycopg import AsyncConnection

load_dotenv()


class Database:
    _connect: ps.connect = None
    _async_connect: AsyncConnection.connect = None

    @staticmethod
    def get_connection():
        if Database._connect is None:
            try:
                Database._connect = ps.connect(
                    dbname=os.getenv("DB_NAME"),
                    user=os.getenv("USER"),
                    password=os.getenv("PASSWORD"),
                    host=os.getenv("HOST"),
                    port=os.getenv("PORT")
                )
            except ps.Error:
                logging.critical("Соединение не установлено!")
                sys.exit(1)
        return Database._connect

    @staticmethod
    async def get_async_connection():
        if Database._async_connect is None:
            try:
                Database._async_connect = await AsyncConnection.connect(
                    dbname=os.getenv("DB_NAME"),
                    user=os.getenv("USER"),
                    password=os.getenv("PASSWORD"),
                    host=os.getenv("HOST"),
                    port=os.getenv("PORT")
                )
                logging.info("Асинхронное соединение установлено")
            except ps.Error:
                logging.critical("Асинхронное соединение не установлено!")
                sys.exit(1)
            return Database._async_connect

    @staticmethod
    def close_connection():
        if Database._connect is not None:
            Database._connect.close()
        if Database._async_connect is not None:
            Database._async_connect.close()
