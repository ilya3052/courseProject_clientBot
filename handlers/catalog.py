import logging

import psycopg as ps
from aiogram import F
from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from psycopg import sql

from keyboards.categories_list import get_categories_kb
from keyboards.product_list import get_products_list_kb
from shared.database import Database

router = Router()

page_size = 3


class Catalog(StatesGroup):
    select_category = State()
    show_products = State()
    select_product = State()


@router.message(StateFilter(None), Command("catalog"))
async def cmd_catalog(message: Message, state: FSMContext):
    connect: ps.connect = Database.get_connection()
    select_categories = """SELECT DISTINCT product_category FROM product"""
    with connect.cursor() as cur:
        try:
            categories_list = cur.execute(select_categories).fetchall()
            await state.update_data(
                categories_list=categories_list,
                category_page=0,
            )
            await show_categories(state, message=message)
        except ps.Error as e:
            logging.error(f"Произошла ошибка при выполнении запроса",
                          extra={
                              'chat_id': message.chat.id,
                              'user_id': message.from_user.id,
                              'state': state,
                              'error': e,
                          }
                          )


@router.callback_query(F.data.startswith("category_"), StateFilter(Catalog.select_category))
async def get_category(callback: CallbackQuery, state: FSMContext):
    connect: ps.connect = Database.get_connection()
    category = callback.data.split("_")[1]
    select_products = (sql.SQL(
        """SELECT product_article, product_name FROM product WHERE product_category = {}"""
    ))
    with connect.cursor() as cur:
        try:
            products = cur.execute(select_products.format(callback.data.split("_")[1])).fetchall()
            await state.update_data(
                products_list=products,
                product_page=0,
                category=category
            )
            await show_products(callback, state)
        except ps.Error as e:
            logging.error(f"Произошла ошибка при выполнении запроса",
                          extra={
                              'chat_id': callback.message.chat.id,
                              'user_id': callback.message.from_user.id,
                              'state': state,
                              'error': e,
                          }
                          )


@router.callback_query(F.data.startswith("action_"), StateFilter(Catalog.select_category))
async def category_action(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    page = data.get('category_page', 0)
    match callback.data.split("_")[1]:
        case "next":
            if (page + 1) * page_size < len(data['categories_list']):
                await state.update_data(category_page=page + 1)
        case "previous":
            if page > 0:
                await state.update_data(category_page=page - 1)
        case "close":
            await state.clear()
            await callback.message.delete()
            await callback.answer()
            return

    await show_categories(state, callback=callback)
    await callback.answer()


@router.callback_query(F.data.startswith("action_"), StateFilter(Catalog.show_products))
async def product_action(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    page = data['product_page']
    match callback.data.split("_")[1]:
        case "next":
            if (page + 1) * page_size < len(data['products_list']):
                await state.update_data(product_page=page + 1)
            await show_products(callback, state)
        case "previous":
            if page > 0:
                await state.update_data(product_page=page - 1)
            await show_products(callback, state)
        case "back":
            await state.set_state(Catalog.select_category)
            await show_categories(state, callback)
            return

    await callback.answer()


async def show_categories(state: FSMContext, callback: CallbackQuery = None, message: Message = None):
    data = await state.get_data()
    page = data['category_page']
    categories = data['categories_list']
    context: CallbackQuery | Message = None
    try:
        if callback:
            context = callback.message
            await callback.message.edit_text(
                "Выберите категорию товаров",
                reply_markup=get_categories_kb(categories[page_size * page:page_size * (page + 1)])
            )
        else:
            context = message
            await message.answer(
                "Выберите категорию товаров",
                reply_markup=get_categories_kb(categories[page_size * page:page_size * (page + 1)])
            )
        await state.set_state(Catalog.select_category)
    except TelegramBadRequest as TBR:
        logging.info(f"Произошла ошибка при выполнении запроса",
                      extra={
                          'chat_id': context.chat.id,
                          'user_id': context.from_user.id,
                          'state': state,
                          'error': TBR,
                      }
                      )


async def show_products(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    products = data['products_list']
    page = data.get('product_page', 0)
    category = data['category']
    try:
        await callback.message.edit_text(
            f"Товары категории {category}.\nВсего в категории {len(products)} товаров",
            reply_markup=get_products_list_kb(products[page_size * page:page_size * (page + 1)])
        )
        await state.set_state(Catalog.show_products)
    except TelegramBadRequest as TBR:
        logging.info(f"Произошла ошибка при выполнении запроса",
                     extra={
                         'chat_id': callback.message.chat.id,
                         'user_id': callback.message.from_user.id,
                         'state': state,
                         'error': TBR,
                     }
                     )


@router.callback_query(F.data.startswith("product_"), StateFilter(Catalog.show_products))
async def show_product(callback: CallbackQuery, state: FSMContext):
    """
        Выборка данных по артикулу, к сообщению добавляется изображение товара, изображения хранятся в папке в корне проекта, их имена совпадают с артикулом, возможно изображения будут разнесены по подпапкам каждой категории для большего удобства
        Клавиатура трехрядная
        1 ряд: по умолчанию "Добавить в корзину", при нажатии меняется на набор из двух кнопок (-/+), а в конец сообщения добавляется строка "количество в заказе: 1"
        2 ряд: переход по карточкам продукта
        3 ряд: возврат в каталог
    """
    connect: ps.connect = Database.get_connection()
    category = callback.data.split("_")[1]
    select_products = (sql.SQL(
        """SELECT product_article, product_name FROM product WHERE product_article = {}"""
    ))
    with connect.cursor() as cur:
        try:
            products = cur.execute(select_products.format(callback.data.split("_")[1])).fetchall()
            await state.update_data(
                products_list=products,
                product_page=0,
                category=category
            )
            await show_products(callback, state)
        except ps.Error as e:
            logging.error(f"Произошла ошибка при выполнении запроса",
                          extra={
                              'chat_id': callback.message.chat.id,
                              'user_id': callback.message.from_user.id,
                              'state': state,
                              'error': e,
                          }
                          )
    await callback.answer()


@router.callback_query(StateFilter(None))
async def handle_no_action(callback: CallbackQuery):
    await callback.answer()
