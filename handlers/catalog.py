
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext

from aiogram import Router
from aiogram.filters import StateFilter, Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram import F

import psycopg as ps
from psycopg import sql

from keyboards.products import get_products
from shared.database import Database

import logging

router = Router()

page_size = 3


class Catalog(StatesGroup):
    select_category = State()
    show_products = State()
    select_product = State()


categories_list = ['Сумки и аксессуары', 'Кухонные принадлежности', 'Гигиена и уход', 'Электроника', 'Освещение',
                   'Книги и журналы', 'Товары для спорта', 'Товары для дома']


@router.message(StateFilter(None), Command("catalog"))
async def cmd_catalog(message: Message, state: FSMContext):
    from keyboards.categories import get_categories_kb
    await message.answer(
        "Выберите категорию товаров",
        reply_markup=get_categories_kb(categories_list)
    )
    await state.set_state(Catalog.select_category)


@router.callback_query(F.data.startswith("category_"))
async def get_category(callback: CallbackQuery, state: FSMContext):
    connect: ps.connect = Database.get_connection()
    category = callback.data.split("_")[1]
    select_products = (sql.SQL(
        """SELECT * FROM product WHERE product_category = {}"""
    ))
    with connect.cursor() as cur:
        try:
            products = cur.execute(select_products.format(callback.data.split("_")[1])).fetchall()
            await state.update_data(
                products_list=products,
                page=0,
                category=category
            )
            await show_products(callback, state)
        except ps.Error as e:
            pass


@router.callback_query(F.data.startswith("action_"), StateFilter(Catalog.show_products))
async def action(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    page = data['page']
    match callback.data.split("_")[1]:
        case "next":
            if (page + 1) * page_size < len(data['products_list']):
                await state.update_data(page=page+1)
        case "previous":
            if page > 0:
                await state.update_data(page=page-1)

    await show_products(callback, state)
    await callback.answer()

async def show_products(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    products = data['products_list']
    page = data['page']
    category = data['category']
    try:
        await callback.message.edit_text(
            f"Товары категории {category}\n",
            reply_markup=get_products(products[page_size * page:page_size * (page + 1)])
        )
        await state.set_state(Catalog.show_products)
    except TelegramBadRequest as TBR:
        logging.info(TBR)


# @router.callback_query(F.data.startswith("product_"))
# async def show_products(message: Message, state: FSMContext):
#     print("Показываем продукты")
