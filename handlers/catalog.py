import asyncio
import logging

import psycopg as ps
from aiogram import F
from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto
from psycopg import sql

from keyboards.categories_list_kb import get_categories_kb
from keyboards.product_info_kb import get_product_info_kb
from keyboards.product_list_kb import get_products_list_kb
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
            logging.exception(f"Произошла ошибка при выполнении запроса {e}")


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
            logging.exception(f"Произошла ошибка при выполнении запроса {e}")


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
async def product_list_action(callback: CallbackQuery, state: FSMContext):
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
    try:
        if callback:
            await callback.message.edit_text(
                "Выберите категорию товаров",
                reply_markup=get_categories_kb(categories[page_size * page:page_size * (page + 1)])
            )
        else:
            await message.answer(
                "Выберите категорию товаров",
                reply_markup=get_categories_kb(categories[page_size * page:page_size * (page + 1)])
            )
        await state.set_state(Catalog.select_category)
    except TelegramBadRequest as TBR:
        logging.exception(f"Произошла ошибка при выполнении запроса {TBR}")


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
        logging.exception(f"Произошла ошибка при выполнении запроса {TBR}")
        loading_msg = await callback.message.answer("⌛ Загружаем товары...")
        await callback.message.delete()
        await loading_msg.edit_text(
            f"Товары категории {category}.\nВсего в категории {len(products)} товаров",
            reply_markup=get_products_list_kb(products[page_size * page:page_size * (page + 1)])
        )
        await state.set_state(Catalog.show_products)


@router.callback_query(F.data.startswith("product_"), StateFilter(Catalog.show_products))
async def get_product(callback: CallbackQuery, state: FSMContext):
    """
        Выборка данных по артикулу, к сообщению добавляется изображение товара, изображения хранятся в папке в корне проекта, их имена совпадают с артикулом, возможно изображения будут разнесены по подпапкам каждой категории для большего удобства
        Клавиатура трехрядная
        1 ряд: по умолчанию "Добавить в корзину", при нажатии меняется на набор из двух кнопок (-/+), а в конец сообщения добавляется строка "количество в заказе: 1"
        2 ряд: переход по карточкам продукта
        3 ряд: возврат в каталог
    """
    connect: ps.connect = Database.get_connection()
    select_products = (sql.SQL(
        """SELECT product_article FROM product WHERE product_category = {}"""
    ))
    with connect.cursor() as cur:
        try:
            data = await state.get_data()
            if 'articles' not in data:
                articles = cur.execute(select_products.format(data['category'])).fetchall()
                articles = [str(item[0]) for item in articles]
                await state.update_data(articles=articles)
            await callback.message.delete()
            await state.set_state(Catalog.select_product)

            await state.update_data(current_article=callback.data.split("_")[1])
            await show_product(callback, state, True)
        except ps.Error as e:
            logging.exception(f"Произошла ошибка при выполнении запроса {e}")
    await callback.answer(show_alert=False)


async def show_product(callback: CallbackQuery, state: FSMContext, is_new_msg: bool):
    data = await state.get_data()
    current_article = data['current_article']
    image = FSInputFile(f"product_images/{current_article}.jpg")
    await state.update_data(current_image_path=image)

    connect: ps.connect = Database.get_connection()
    select_product_info = sql.SQL(
        """SELECT product_price, product_description FROM product WHERE product_article = {}"""
    )

    try:
        with connect.cursor() as cur:
            product_info = cur.execute(select_product_info.format(current_article)).fetchone()
            description = product_info[1]
            await state.update_data(product_description=description)
    except ps.Error as e:
        logging.exception(f"Произошла ошибка при выполнении запроса {e}")
        return

    cart = data.get('cart', {})
    count = cart.get(current_article, 0)

    caption = description
    if count > 0:
        caption += f"\nКоличество товаров в корзине: {count}"

    keyboard = get_product_info_kb(bool(count))

    try:
        if is_new_msg:
            await callback.message.answer_photo(
                image,
                caption=caption,
                reply_markup=keyboard,
            )
        else:
            await callback.message.edit_media(
                InputMediaPhoto(
                    media=image,
                    caption=caption
                ),
                reply_markup=keyboard,
            )
    except TelegramBadRequest as TBR:
        logging.exception(f"Произошла ошибка при выполнении запроса {TBR}")
        await callback.answer()


@router.callback_query(F.data.startswith("action_"), StateFilter(Catalog.select_product))
async def product_action(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_article = data['current_article']
    articles = data['articles']
    current_index = articles.index(current_article)
    match callback.data.split("_")[1]:
        case "addToCart":
            cart = data.get('cart', {})
            cart[current_article] = cart.get(current_article, 0) + 1
            await state.update_data(cart=cart)
            await callback.message.edit_caption(
                caption=f"{callback.message.caption}\nКоличество товаров в корзине: {cart[current_article]}",
            )
            await callback.message.edit_reply_markup(reply_markup=get_product_info_kb(True))
        case "next":
            new_index = (current_index + 1) % len(articles)  # Циклический переход
            new_article = articles[new_index]
            await state.update_data(current_article=new_article)
            await show_product(callback, state, False)
        case "previous":
            new_index = (current_index - 1) % len(articles)  # Циклический переход
            new_article = articles[new_index]
            await state.update_data(current_article=new_article)
            await show_product(callback, state, False)
        case "back":
            await state.set_state(Catalog.show_products)
            await show_products(callback, state)
        case "confirm":
            # создать заказ, добавить товары
            await confirm_order(callback, state)
        case "cancel":
            # переход в профиль
            await callback.message.delete()
            await state.clear()
            await state.set_state(None)
    await callback.answer()


async def confirm_order(callback: CallbackQuery, state: FSMContext):
    await create_order(callback, state)
    await add_products(state)
    await callback.message.delete()
    await callback.message.answer("Заказ создан, подождите назначения курьера!")
    await state.clear()
    await state.set_state(None)
    # показываем профиль


async def create_order(callback: CallbackQuery, state: FSMContext):
    connect: ps.connect = Database.get_connection()
    select_client_id = (sql.SQL(
        "SELECT client_id FROM client c JOIN users u on c.user_id = u.user_id WHERE user_tgchat_id = {};"
    ))
    get_new_order_id = (sql.SQL(
        'INSERT INTO "order" (client_id) VALUES ({}) RETURNING order_id;'
    ))

    with connect.cursor() as cur:
        try:
            client_id = cur.execute(select_client_id.format(callback.message.chat.id)).fetchone()[0]
            order_id = cur.execute(get_new_order_id.format(client_id)).fetchone()[0]
            await state.update_data(order_id=order_id)
            connect.commit()
        except ps.Error as e:
            logging.exception(f"Произошла ошибка при выполнении запроса {e}")
            connect.rollback()


async def add_products(state: FSMContext):
    data = await state.get_data()
    cart = data['cart']
    order_id = data.get('order_id')
    products_list = [(order_id, int(item)) for item, count in cart.items() for _ in range(count)]
    insert_product = (sql.SQL(
        "INSERT INTO added (order_id, product_article) VALUES (%s, %s)"
    ))
    connect: ps.connect = Database.get_connection()
    with connect.cursor() as cur:
        try:
            cur.executemany(insert_product, products_list)
            connect.commit()
        except ps.Error as e:
            logging.exception(f"Произошла ошибка при выполнении запроса {e}")
            connect.rollback()


@router.callback_query(F.data.startswith("count_"), StateFilter(Catalog.select_product))
async def count_change(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    image = data['current_image_path']
    product_info = data['product_description']
    current_article = data.get('current_article')
    cart = data.get('cart', {})
    count = cart.get(current_article, 1)

    try:
        match callback.data.split("_")[1]:
            case "inc":
                count += 1
                cart[current_article] = count
            case "dec":
                count = max(0, count - 1)
                if count:
                    cart[current_article] = count
                else:
                    cart.pop(current_article, None)
        await state.update_data(cart=cart)
        caption = product_info if count == 0 else f"{product_info}\nКоличество товаров в корзине: {count}"
        keyboard = get_product_info_kb(bool(count))
        await callback.message.edit_media(
            InputMediaPhoto(media=image, caption=caption),
            reply_markup=keyboard,
        )
    except TelegramBadRequest as TBR:
        logging.exception(f"Произошла ошибка при выполнении запроса {TBR}")

    await callback.answer()


@router.callback_query(StateFilter(None))
async def handle_no_action(callback: CallbackQuery):
    await callback.answer()
