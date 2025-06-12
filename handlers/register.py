import logging
import re

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from asyncpg import PostgresError

from core.database import db

router = Router()


class Register(StatesGroup):
    enter_name = State()
    enter_nickname = State()
    enter_phonenumber = State()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    select_nickname = """SELECT c.client_nickname 
        FROM users u JOIN client c ON u.user_id = c.user_id 
        WHERE u.user_tgchat_id = $1;"""

    try:
        nickname = await db.execute(select_nickname, message.chat.id, fetchval=True)
    except PostgresError as e:
        logging.critical(f"Запрос не выполнен. {e}")

    if not nickname:
        await message.answer(
            "Добрый день! Похоже, вы не зарегистрированы в системе, давайте пройдем быструю регистрацию.\n"
            "Укажите имя в формате ФИО (отчество при наличии)\n"
        )
        await state.set_state(Register.enter_name)
        await state.update_data(tgchat_id=message.chat.id, username=message.from_user.username)
        logging.info("Имя введено")
    else:
        await message.answer(f"Добро пожаловать, {nickname}!")
        logging.info("Осуществлен вход в систему")


@router.message(Register.enter_name, F.text)
async def enter_name(message: Message, state: FSMContext):
    await message.answer("Как к вам обращаться?")
    await state.set_state(Register.enter_nickname)
    await state.update_data(
        fullname=message.text.split()
    )
    logging.info("Обращение введено")


@router.message(Register.enter_nickname, F.text)
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
        if await insert_data(data):
            await message.answer(f"Регистрация завершена. Добро пожаловать, {data['nickname']}")
            logging.info("Регистрация завершена")
        else:
            await message.answer("Регистрация не завершена, попробуйте еще раз!")
            await cmd_start(message, state)
    else:
        await message.answer("Неправильный формат ввода, попробуйте еще раз!")


async def insert_data(data: dict) -> bool:
    data['phonenumber'] = (data['phonenumber'].replace('(', '')
                           .replace(')', '')
                           .replace('-', '')
                           .replace('+', ''))
    insert_user = """INSERT INTO users 
            (user_tgchat_id, user_name, user_surname, user_patronymic, user_role, user_phonenumber, user_tg_username) 
            VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING user_id;"""

    insert_client = "INSERT INTO client (user_id, client_nickname) VALUES ($1, $2);"

    try:
        user_id = await db.execute(
            insert_user, data['tgchat_id'], data['fullname'][1], data['fullname'][0],
            data['fullname'][2] if len(data['fullname']) > 2 else None, 'user',
            data['phonenumber'], data['username'], fetchval=True)
        await db.execute(insert_client, user_id, data['nickname'], execute=True)
        logging.info("Запрос выполнен")
        return True
    except PostgresError as e:
        logging.critical(f"Запрос не выполнен. {e}")
        return False
    except Exception as e:
        logging.exception(f"При выполнении запроса произошла ошибка: {e}")
        return False
