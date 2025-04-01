import logging
import os
import sys

import psycopg as ps
from dotenv import load_dotenv

load_dotenv()


class Database:
    _connect: ps.connect = None

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
    def close_connection():
        if Database._connect is not None:
            Database._connect.close()
