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
    enter_phonenumber = State()


@router.message(StateFilter(None), Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    # проверка на валидность ссылки
    connect: ps.connect = Database.get_connection()
    try:
        with connect.cursor() as cur:
            select_chat_id = sql.SQL("SELECT 1 FROM users WHERE user_tgchat_id = {}")
            is_link_valid = cur.execute(select_chat_id.format(message.text.split()[1])).fetchone()
    except IndexError:
        await message.answer("Ссылка недействительна, пожалуйста, получите действующую у администратора")
        return

    if is_link_valid is None:
        await message.answer("Ссылка недействительна, пожалуйста, получите действующую у администратора")
    else:
        await message.answer("Введите имя в формате ФИО (отчество при наличии)")
        await state.set_state(Register.enter_name)
        await state.update_data(last_chat_id=message.text.split()[1])
        await state.update_data(chat_id=message.chat.id)
        logging.info("Введено имя")


@router.message(Register.enter_name)
async def enter_nickname(message: Message, state: FSMContext):
    await message.answer("Укажите номер телефона в формате +7(***)***-**-**")
    await state.update_data(name=message.text.split())
    await state.set_state(Register.enter_phonenumber)
    logging.info("Номер телефона введен")


@router.message(Register.enter_phonenumber)
async def enter_phonenumber(message: Message, state: FSMContext):
    pattern = re.compile(r'^\+7\(\d{3}\)\d{3}-\d{2}-\d{2}$')
    if pattern.match(message.text):
        await state.update_data(phonenumber=message.text)
        data = await state.get_data()
        await state.clear()
        await message.answer(f"Регистрация завершена. Можете приступать к работе.")
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
    update_user = (sql.SQL(
        """UPDATE users 
            SET user_tgchat_id = {}, user_name = {}, user_surname = {}, user_patronymic = {}, user_phonenumber = {} 
            WHERE user_tgchat_id = {}
            RETURNING user_id;"""
    ))
    insert_courier = (sql.SQL(
        "INSERT INTO courier (user_id) VALUES ({});"
    ))
    with connect.cursor() as cur:
        try:
            cur.execute(
                update_user.format(
                    data['chat_id'], data['name'][1], data['name'][0],
                    data['name'][2] if len(data['name']) > 2 else None, data['phonenumber'], data['last_chat_id']
                ))
            user_id = cur.fetchone()[0]
            cur.execute(insert_courier.format(
                user_id
            ))
            connect.commit()
            logging.info("Запрос выполнен")
        except ps.Error as e:
            connect.rollback()
            logging.critical(f"Запрос не выполнен. {e}")
