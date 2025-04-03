from aiogram import Router
from aiogram.filters import StateFilter, Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message


catalog_router = Router()


class Catalog(StatesGroup):
    select_category = State()
    show_products = State()
    select_product = State()


categories_list = ['Сумки и аксессуары', 'Кухонные принадлежности', 'Гигиена и уход', 'Электроника', 'Освещение',
                   'Книги и журналы', 'Товары для спорта', 'Товары для дома']


@catalog_router.message(StateFilter(None), Command("catalog"))
async def cmd_catalog(message: Message):
    from keyboards.categories import get_categories_kb
    await message.answer(
        "Выберите категорию",
        reply_markup=get_categories_kb(categories_list)
    )
