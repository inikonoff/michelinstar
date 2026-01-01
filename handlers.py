from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from groq_service import GroqService
from state_manager import state_manager

async def handle_text(message: Message):
    uid = message.from_user.id
    # Исправленный вызов: GroqService.метод
    data = await GroqService.determine_intent(message.text)
    
    if data.get("intent") == "recipe":
        await send_recipe(message, uid, data.get("dish", message.text))
    else:
        state_manager.set_products(uid, message.text)
        cats = await GroqService.analyze_categories(message.text)
        state_manager.set_categories(uid, cats)
        
        btns = [[InlineKeyboardButton(text=c, callback_data=f"cat_{c}")] for c in cats]
        await message.answer("Что готовим?", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

async def send_recipe(message: Message, uid: int, dish: str):
    wait = await message.answer("⏳ Готовлю...")
    products = state_manager.get_products(uid) or "стандартный набор"
    recipe = await GroqService.generate_recipe(dish, products, message.from_user.language_code)
    await wait.delete()
    await message.answer(recipe)

async def handle_callback(cb: CallbackQuery):
    uid = cb.from_user.id
    if cb.data.startswith("cat_"):
        cat = cb.data.split("_")[1]
        dishes = await GroqService.generate_dishes_list(state_manager.get_products(uid), cat, cb.from_user.language_code)
        state_manager.set_generated_dishes(uid, dishes)
        
        btns = [[InlineKeyboardButton(text=d['display_name'], callback_data=f"dish_{i}")] for i, d in enumerate(dishes)]
        await cb.message.edit_text("Выберите блюдо:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    
    elif cb.data.startswith("dish_"):
        idx = int(cb.data.split("_")[1])
        dish = state_manager.get_generated_dish(uid, idx)
        await cb.message.delete()
        await send_recipe(cb.message, uid, dish)
    await cb.answer()

def register_handlers(dp: Dispatcher):
    dp.message.register(handle_text, F.text)
    dp.callback_query.register(handle_callback)