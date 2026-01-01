import os
import logging
from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from utils import VoiceProcessor
from groq_service import GroqService
from state_manager import state_manager

# Инициализация
voice_processor = VoiceProcessor()
# GroqService теперь используется статически или через экземпляр
logger = logging.getLogger(__name__)

CATEGORY_MAP = {
    "breakfast": "🍳 Завтраки",
    "soup": "🍲 Супы",
    "main": "🍝 Вторые блюда",
    "salad": "🥗 Салаты",
    "snack": "🥪 Закуски",
    "dessert": "🍰 Десерты",
    "drink": "🥤 Напитки",
}

# --- КЛАВИАТУРЫ --- (Без изменений, они у тебя отличные)
def get_style_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Классический / Домашний", callback_data="style_ordinary")],
        [InlineKeyboardButton(text="🌶 Экзотический / Необычный", callback_data="style_exotic")]
    ])

def get_categories_keyboard(categories: list):
    builder = []
    row = []
    for cat_key in categories:
        text = CATEGORY_MAP.get(cat_key, cat_key.capitalize())
        row.append(InlineKeyboardButton(text=text, callback_data=f"cat_{cat_key}"))
        if len(row) == 2:
            builder.append(row)
            row = []
    if row: builder.append(row)
    builder.append([InlineKeyboardButton(text="🗑 Сброс", callback_data="restart")])
    return InlineKeyboardMarkup(inline_keyboard=builder)

def get_dishes_keyboard(dishes_list: list):
    builder = []
    for i, dish in enumerate(dishes_list):
        btn_text = f"{dish.get('display_name', dish['name'])[:40]}"
        builder.append([InlineKeyboardButton(text=btn_text, callback_data=f"dish_{i}")])
    builder.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_categories")])
    return InlineKeyboardMarkup(inline_keyboard=builder)

def get_recipe_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Другой вариант", callback_data="repeat_recipe")],
        [InlineKeyboardButton(text="⬅️ К категориям", callback_data="back_to_categories")]
    ])

# --- ОСНОВНЫЕ ХЭНДЛЕРЫ ---

async def cmd_start(message: Message):
    state_manager.clear_session(message.from_user.id)
    text = (
        "👋 <b>Я ваш ИИ-шеф!</b>\n\n"
        "1️⃣ Пришлите список продуктов (текстом или голосом).\n"
        "2️⃣ Или просто напишите: <i>'Хочу лазанью'</i> или <i>'Как приготовить плов?'</i>\n\n"
        "Я подберу идеальный рецепт и дам советы по вкусу и текстуре."
    )
    await message.answer(text, parse_mode="HTML")

async def handle_voice(message: Message):
    user_id = message.from_user.id
    processing_msg = await message.answer("🎧 Слушаю и перевожу в текст...")
    temp_file = f"temp/voice_{user_id}.ogg"
    
    try:
        await message.bot.download(message.voice, destination=temp_file)
        text = await voice_processor.process_voice(temp_file)
        await processing_msg.delete()
        await process_smart_logic(message, user_id, text)
    except Exception as e:
        await processing_msg.edit_text(f"😕 Не удалось распознать голос: {e}")
    finally:
        if os.path.exists(temp_file): os.remove(temp_file)

async def handle_text(message: Message):
    await process_smart_logic(message, message.from_user.id, message.text)

# --- УМНАЯ ЛОГИКА (ЦЕНТРАЛЬНЫЙ ХАБ) ---

async def process_smart_logic(message: Message, user_id: int, text: str):
    # 1. Проверка на вежливость (пасхалка)
    if text.lower().strip(" .!") in ["спасибо", "спс", "благодарю"]:
        await message.answer("На здоровье! Приходите еще 👩‍🍳")
        return

    # 2. Определяем намерение через Groq
    intent_data = await GroqService.determine_intent(text)
    
    # СЦЕНАРИЙ А: Запрос конкретного рецепта
    if intent_data.get("intent") == "recipe":
        dish_name = intent_data.get("dish", text)
        await generate_and_send_recipe(message, user_id, dish_name)
        return

    # СЦЕНАРИЙ Б: Работа с продуктами
    products_in_mem = state_manager.get_products(user_id)
    
    if not products_in_mem:
        # Валидация первой порции продуктов
        if not await GroqService.validate_ingredients(text):
            await message.answer(f"🧐 <b>'{text}'</b> не похоже на продукты. Попробуйте еще раз.")
            return
        
        state_manager.set_products(user_id, text)
        await message.answer(f"🥬 Продукты записаны. В каком стиле будем готовить?", 
                             reply_markup=get_style_keyboard(), parse_mode="HTML")
    else:
        # Дополнение списка
        state_manager.append_products(user_id, text)
        new_list = state_manager.get_products(user_id)
        await message.answer(f"➕ Добавил. Теперь у нас: <i>{new_list}</i>", parse_mode="HTML")
        await start_category_flow(message, user_id, new_list, "обычный")

# --- ПРОЦЕСС ГЕНЕРАЦИИ ---

async def start_category_flow(message: Message, user_id: int, products: str, style: str):
    wait = await message.answer("🧪 Анализирую сочетания...")
    categories = await GroqService.analyze_categories(products)
    await wait.delete()
    
    if not categories:
        await message.answer("Из этого набора сложно что-то предложить. Добавьте продуктов?")
        return

    state_manager.set_categories(user_id, categories)
    await message.answer("📂 <b>Выберите категорию блюда:</b>", 
                         reply_markup=get_categories_keyboard(categories), parse_mode="HTML")

async def generate_and_send_recipe(message: Message, user_id: int, dish_name: str):
    wait = await message.answer(f"👨‍🍳 Составляю рецепт: <b>{dish_name}</b>...", parse_mode="HTML")
    
    # Берем продукты из памяти, если они есть, иначе - пустая строка
    products = state_manager.get_products(user_id) or "базовый набор"
    
    recipe = await GroqService.generate_recipe(dish_name, products)
    await wait.delete()
    
    state_manager.set_current_dish(user_id, dish_name)
    state_manager.set_state(user_id, "recipe_sent")
    
    # Используем HTML для поддержки жирного текста и эмодзи
    await message.answer(recipe, reply_markup=get_recipe_back_keyboard(), parse_mode="HTML")

# --- CALLBACKS --- (Оптимизированы)

async def handle_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    
    if data == "restart":
        state_manager.clear_session(user_id)
        await callback.message.edit_text("🗑 Все продукты удалены. Жду новый список!")
        await callback.answer()

    elif data.startswith("style_"):
        style = "домашний" if "ordinary" in data else "экзотический"
        products = state_manager.get_products(user_id)
        await callback.message.delete()
        await start_category_flow(callback.message, user_id, products, style)

    elif data.startswith("cat_"):
        category = data.split("_")[1]
        products = state_manager.get_products(user_id)
        await callback.message.edit_text(f"🔍 Подбираю рецепты в категории: {CATEGORY_MAP.get(category, category)}...")
        
        dishes = await GroqService.generate_dishes_list(products, category)
        state_manager.set_generated_dishes(user_id, dishes)
        
        # Красивый вывод меню
        menu_text = "📋 <b>Предлагаю приготовить:</b>\n\n"
        for d in dishes:
            menu_text += f"▪️ <b>{d.get('display_name', d['name'])}</b>\n{d['desc']}\n\n"
        
        await callback.message.edit_text(menu_text, reply_markup=get_dishes_keyboard(dishes), parse_mode="HTML")

    elif data.startswith("dish_"):
        index = int(data.split("_")[1])
        dish_name = state_manager.get_generated_dish(user_id, index)
        await callback.message.delete()
        await generate_and_send_recipe(callback.message, user_id, dish_name)

    elif data == "back_to_categories":
        categories = state_manager.get_categories(user_id)
        if categories:
            await callback.message.edit_text("📂 <b>Выберите категорию:</b>", 
                                             reply_markup=get_categories_keyboard(categories), parse_mode="HTML")
        else:
            await callback.answer("Сессия устарела, начните заново.")

    await callback.answer()

def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(handle_voice, F.voice)
    # Один текстовый хэндлер для всего
    dp.message.register(handle_text, F.text)
    dp.callback_query.register(handle_callback)
