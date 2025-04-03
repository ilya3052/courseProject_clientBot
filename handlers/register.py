import logging
import re

import psycopg as ps
from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from psycopg import sql

from shared.database import Database

router = Router()


class Register(StatesGroup):
    enter_name = State()
    enter_nickname = State()
    enter_phonenumber = State()


@router.message(StateFilter(None), Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    connect: ps.connect = Database.get_connection()
    select_nickname = (sql.SQL(
        """SELECT c.client_nickname 
        FROM users u JOIN client c ON u.user_id = c.user_id 
        WHERE u.user_tgchat_id = {};"""
    ))
    with connect.cursor() as cur:
        try:
            nickname = cur.execute(select_nickname.format(message.chat.id)).fetchone()
            connect.commit()
            logging.info("Запрос выполнен")
        except ps.Error as e:
            connect.rollback()
            logging.critical(f"Запрос не выполнен. {e}")
    if nickname is None:
        await message.answer(
            "Добрый день! Похоже, вы не зарегестрированы в системе, давайте пройдем быструю регистрацию.\n"
            "Укажите имя в формате ФИО (отчество при наличии)\n"
        )
        await state.set_state(Register.enter_name)
        await state.update_data(tgchat_id=message.chat.id)
        logging.info("Имя введено")
    else:
        await message.answer(f"Добро пожаловать, {nickname[0]}!")
        logging.info(f"Осуществлен вход в систему, tgchat_id = {message.chat.id}")


@router.message(Register.enter_name)
async def enter_name(message: Message, state: FSMContext):
    await message.answer("Как к вам обращаться?")
    await state.set_state(Register.enter_nickname)
    await state.update_data(
        fullname=message.text.split()
    )
    logging.info("Обращение введено")


@router.message(Register.enter_nickname)
async def enter_nickname(message: Message, state: FSMContext):
    await message.answer("Укажите номер телефона в формате +7(***)***-**-**")
    await state.set_state(Register.enter_phonenumber)
    await state.update_data(nickname=message.text)
    logging.info("Номер телефона введен")


@router.message(Register.enter_phonenumber)
async def enter_phonenumber(message: Message, state: FSMContext):
    pattern = re.compile(r'^\+7\(\d{3}\)\d{3}-\d{2}-\d{2}$')
    if pattern.match(message.text):
        await state.update_data(phonenumber=message.text)
        data = await state.get_data()
        await state.clear()
        await message.answer(f"Регистрация завершена. Добро пожаловать, {data['nickname']}")
        insert_data(data)
        logging.info("Регистрация завершена")

    else:
        await message.answer("Неправильный формат ввода, попробуйте еще раз!")


def insert_data(data: dict):
    connect: ps.connect = Database.get_connection()
    data['phonenumber'] = (data['phonenumber'].replace('(', '')
                           .replace(')', '')
                           .replace('-', '')
                           .replace('+', ''))
    insert_user = (sql.SQL(
        """INSERT INTO users 
            (user_tgchat_id, user_name, user_surname, user_patronymic, user_role, user_phonenumber) 
            VALUES ({}, {}, {}, {}, {}, {})
            RETURNING user_id;"""
    ))
    insert_client = (sql.SQL(
        "INSERT INTO client (user_id, client_nickname) VALUES ({}, {});"
    ))
    with connect.cursor() as cur:
        try:
            cur.execute(
                insert_user.format(data['tgchat_id'], data['fullname'][1], data['fullname'][0],
                                   data['fullname'][2] if len(data['fullname']) > 2 else None, 'user',
                                   data['phonenumber']))
            user_id = cur.fetchone()[0]
            cur.execute(insert_client.format(
                user_id, data['nickname']
            ))
            connect.commit()
            logging.info("Запрос выполнен")
        except ps.Error as e:
            connect.rollback()
            logging.critical(f"Запрос не выполнен. {e}")
