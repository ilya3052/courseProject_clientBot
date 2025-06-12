import logging

from aiogram import F
from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto, InlineKeyboardButton, \
    InlineKeyboardMarkup
from asyncpg import PostgresError

from Filters.IsRegistered import IsRegistered
from core.database import db
from keyboards import get_categories_kb, get_product_info_kb
from keyboards import get_products_list_kb
from .register import cmd_start

router = Router()

page_size = 3


class Catalog(StatesGroup):
    select_category = State()
    show_products = State()
    select_product = State()
    create_order = State()


@router.message(Command("catalog"), IsRegistered())
async def cmd_catalog(message: Message, state: FSMContext):
    select_categories = """SELECT DISTINCT product_category FROM product"""
    try:
        categories_list = await db.execute(select_categories, fetch=True)
        categories_list = [item['product_category'] for item in categories_list]
        await state.update_data(
            categories_list=categories_list,
            category_page=0,
        )
        await show_categories(state, message=message)
    except PostgresError as e:
        logging.exception(f"Произошла ошибка при выполнении запроса {e}")


@router.callback_query(F.data.startswith("category_"), StateFilter(Catalog.select_category), IsRegistered())
async def get_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("_")[1]
    select_products = """SELECT product_article, product_name FROM product WHERE product_category = $1"""

    try:
        products = await db.execute(select_products, callback.data.split("_")[1], fetch=True)
        products = [(item['product_article'], item['product_name']) for item in products]
        await state.update_data(
            products_list=products,
            product_page=0,
            category=category
        )
        await show_products(callback, state)
    except PostgresError as e:
        logging.exception(f"Произошла ошибка при выполнении запроса {e}")


@router.callback_query(F.data.startswith("action_"), StateFilter(Catalog.select_category), IsRegistered())
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


@router.callback_query(F.data.startswith("action_"), StateFilter(Catalog.show_products), IsRegistered())
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


@router.callback_query(F.data.startswith("product_"), StateFilter(Catalog.show_products), IsRegistered())
async def get_product(callback: CallbackQuery, state: FSMContext):
    select_products = """SELECT product_article FROM product WHERE product_category = $1"""

    try:
        data = await state.get_data()
        articles = await db.execute(select_products, data['category'], fetch=True)
        articles = [item['product_article'] for item in articles]
        await state.update_data(articles=articles)
        await callback.message.delete()
        await state.set_state(Catalog.select_product)

        await state.update_data(current_article=int(callback.data.split("_")[1]))
        await show_product(callback, state, True)
    except PostgresError as e:
        logging.exception(f"Произошла ошибка при выполнении запроса {e}")
    await callback.answer(show_alert=False)


@router.callback_query(F.data.startswith("action_"), StateFilter(Catalog.select_product), IsRegistered())
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
            new_index = (current_index + 1) % len(articles)
            new_article = articles[new_index]
            await state.update_data(current_article=new_article)
            await show_product(callback, state, False)
        case "previous":
            new_index = (current_index - 1) % len(articles)
            new_article = articles[new_index]
            await state.update_data(current_article=new_article)
            await show_product(callback, state, False)
        case "back":
            await state.set_state(Catalog.show_products)
            await show_products(callback, state)
        case "confirm":
            await callback.message.delete()
            await callback.message.answer("Пожалуйста укажите адрес доставки!")
            order_id = (await state.get_data()).get('order_id')
            await state.set_state(Catalog.create_order)
            await state.update_data(order_id=order_id)
        case "cancel":
            await callback.message.delete()
            await state.clear()
            await state.set_state(None)
    await callback.answer()


#
#
@router.message(F.text, StateFilter(Catalog.create_order))
async def address_input(message: Message, state: FSMContext):
    address = message.text
    await state.update_data(address=address)
    await confirm_order(message, state)
    await message.answer("Заказ создан, подождите назначения курьера!",
                         reply_markup=InlineKeyboardMarkup(
                             inline_keyboard=[
                                 [InlineKeyboardButton(text="Вернуться в профиль ↩️", callback_data="profile")]
                             ]
                         )
                         )

    await db.notify_channel('create_order', f'order_id: {(await state.get_data()).get('order_id')}')
    await state.clear()
    await state.set_state(None)


@router.callback_query(F.data.startswith("count_"), StateFilter(Catalog.select_product), IsRegistered())
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
        logging.debug(f"Поймано некритичное исключение при попытке отредактировать сообщение {TBR}")

    await callback.answer()


@router.callback_query(StateFilter(None))
async def handle_no_action(callback: CallbackQuery):
    await callback.answer()


@router.message(~IsRegistered())
@router.callback_query(~IsRegistered())
async def reg_handler(update: Message | CallbackQuery, state: FSMContext):
    message = update.message if isinstance(update, CallbackQuery) else update
    await cmd_start(message, state)


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


#
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
    except TelegramBadRequest as TBR:
        logging.info(f"Поймано некритичное исключение при попытке отредактировать сообщение {TBR}")

    await state.set_state(Catalog.show_products)


async def show_product(callback: CallbackQuery, state: FSMContext, is_new_msg: bool):
    data = await state.get_data()
    current_article = data['current_article']
    image = FSInputFile(f"product_images/{current_article}.jpg")
    await state.update_data(current_image_path=image)

    select_product_info = """SELECT product_price, product_description FROM product WHERE product_article = $1"""

    try:
        product_info = await db.execute(select_product_info, current_article, fetch=True)
        product_info = [dict(item) for item in product_info][0]

        description = f"{product_info['product_description']}\nСтоимость товара: {product_info['product_price']}"

        await state.update_data(product_description=description)
    except PostgresError as e:
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
        logging.debug(f"Поймано некритичное исключение при попытке отредактировать сообщение {TBR}")
        await callback.answer()


async def confirm_order(message: Message, state: FSMContext):
    await create_order(message, state)
    await add_products(state)


async def create_order(message: Message, state: FSMContext):
    address = (await state.get_data()).get('address')
    try:
        async with db.pool.acquire() as connection:
            async with connection.transaction():
                order_id = await db.execute("SELECT create_order($1, $2);", message.chat.id, address, fetchval=True)
                await state.update_data(order_id=order_id)
    except PostgresError as e:
        logging.exception(f"Произошла ошибка при выполнении запроса {e}")


async def add_products(state: FSMContext):
    data = await state.get_data()
    cart = data['cart']
    order_id = data.get('order_id')
    products_list = [(order_id, int(item)) for item, count in cart.items() for _ in range(count)]
    insert_product = "INSERT INTO added (order_id, product_article) VALUES ($1, $2)"

    try:
        await db.execute(insert_product, products_list, executemany=True)
    except PostgresError as e:
        logging.exception(f"Произошла ошибка при выполнении запроса {e}")
