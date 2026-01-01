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

# --- КЛАВИАТУРЫ ---
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

def get_recipe_error_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Попробовать другой рецепт", callback_data="back_to_categories")],
        [InlineKeyboardButton(text="🗑 Сброс", callback_data="restart")]
    ])

# --- ОСНОВНЫЕ ХЭНДЛЕРЫ ---

async def cmd_start(message: Message):
    """Команда /start - начало работы с ботом"""
    state_manager.clear_session(message.from_user.id)
    text = (
        "👋 <b>Я ваш ИИ-шеф!</b>\n\n"
        "1️⃣ Пришлите список продуктов (текстом или голосом).\n"
        "2️⃣ Или просто напишите: <i>'Хочу лазанью'</i> или <i>'Как приготовить плов?'</i>\n\n"
        "Я подберу идеальный рецепт и дам советы по вкусу и текстуре."
    )
    await message.answer(text, parse_mode="HTML")

async def cmd_author(message: Message):
    """Команда /author - информация об авторе"""
    text = (
        "👨‍💻 <b>Об авторе</b>\n\n"
        "Этот бот создан с использованием:\n"
        "• Telegram Bot API (aiogram)\n"
        "• Groq API с моделью Llama 3.3\n"
        "• Python асинхронное программирование\n\n"
        "Бот умеет:\n"
        "🎤 Распознавать голосовые сообщения\n"
        "🧠 Анализировать ингредиенты\n"
        "🍳 Предлагать рецепты по категориям\n"
        "📊 Рассчитывать пищевую ценность\n\n"
        "Приятного аппетита! 👨‍🍳"
    )
    await message.answer(text, parse_mode="HTML")

async def handle_voice(message: Message):
    """Обработка голосовых сообщений"""
    user_id = message.from_user.id
    processing_msg = await message.answer("🎧 Слушаю и перевожу в текст...")
    temp_file = f"temp/voice_{user_id}.ogg"
    
    try:
        await message.bot.download(message.voice, destination=temp_file)
        text = await voice_processor.process_voice(temp_file)
        await processing_msg.delete()
        await process_smart_logic(message, user_id, text)
    except Exception as e:
        logger.error(f"Voice processing error for user {user_id}: {e}")
        await processing_msg.edit_text("😕 Не удалось распознать голос. Попробуйте отправить текстом.")
    finally:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception as e:
                logger.error(f"Error removing temp file {temp_file}: {e}")

async def handle_text(message: Message):
    """Обработка текстовых сообщений"""
    await process_smart_logic(message, message.from_user.id, message.text)

# --- УМНАЯ ЛОГИКА (ЦЕНТРАЛЬНЫЙ ХАБ) ---

async def process_smart_logic(message: Message, user_id: int, text: str):
    """Центральный хаб для обработки всех запросов пользователя"""
    # 1. Проверка на вежливость (пасхалка)
    polite_words = ["спасибо", "спс", "благодарю", "thanks", "thank you"]
    if text.lower().strip(" .!?,") in polite_words:
        responses = ["На здоровье! Приходите еще 👩‍🍳", 
                    "Рад был помочь! 🍳", 
                    "Всегда пожалуйста! 😊"]
        import random
        await message.answer(random.choice(responses))
        return

    # 2. Определяем намерение через Groq
    intent_data = await GroqService.determine_intent(text)
    
    # СЦЕНАРИЙ А: Запрос конкретного рецепта
    if intent_data.get("intent") == "recipe":
        dish_name = intent_data.get("dish", text).strip()
        if len(dish_name) < 2:
            await message.answer("Пожалуйста, укажите название блюда более конкретно.")
            return
        await generate_and_send_recipe(message, user_id, dish_name)
        return

    # СЦЕНАРИЙ Б: Работа с продуктами
    products_in_mem = state_manager.get_products(user_id)
    
    if not products_in_mem:
        # Валидация первой порции продуктов
        if not await GroqService.validate_ingredients(text):
            await message.answer(f"🧐 <b>'{text[:50]}...'</b> не похоже на продукты. Попробуйте еще раз.\n\nПример: <i>курица, рис, морковь, лук</i>", 
                                 parse_mode="HTML")
            return
        
        state_manager.set_products(user_id, text)
        await message.answer(f"✅ <b>Продукты записаны!</b>\n\n<i>{text}</i>\n\nВ каком стиле будем готовить?", 
                             reply_markup=get_style_keyboard(), parse_mode="HTML")
    else:
        # Дополнение списка продуктов
        state_manager.append_products(user_id, text)
        new_list = state_manager.get_products(user_id)
        await message.answer(f"➕ <b>Добавил к вашим продуктам!</b>\n\nТеперь у нас: <i>{new_list}</i>\n\nМожете добавить ещё или нажмите кнопку стиля выше.", 
                             parse_mode="HTML")

# --- ПРОЦЕСС ГЕНЕРАЦИИ ---

async def start_category_flow(message: Message, user_id: int, products: str, style: str):
    """Запуск потока выбора категории"""
    wait_msg = await message.answer("🧪 Анализирую сочетания продуктов...")
    categories = await GroqService.analyze_categories(products)
    await wait_msg.delete()
    
    if not categories:
        await message.answer("❓ <b>Не могу определить категории</b>\n\nИз этого набора сложно что-то предложить. Добавьте больше продуктов?",
                            parse_mode="HTML")
        return

    state_manager.set_categories(user_id, categories)
    state_manager.set_state(user_id, f"style_{style}")
    
    categories_text = "\n".join([f"• {CATEGORY_MAP.get(cat, cat.capitalize())}" for cat in categories])
    await message.answer(f"📂 <b>Выберите категорию блюда:</b>\n\nДоступные категории:\n{categories_text}", 
                         reply_markup=get_categories_keyboard(categories), parse_mode="HTML")

async def generate_and_send_recipe(message: Message, user_id: int, dish_name: str):
    """Генерация и отправка рецепта"""
    if len(dish_name) < 2:
        await message.answer("Пожалуйста, укажите более конкретное название блюда.")
        return
    
    wait_msg = await message.answer(f"👨‍🍳 <b>Составляю рецепт:</b> {dish_name}...", parse_mode="HTML")
    
    # Берем продукты из памяти, если они есть, иначе - пустая строка
    products = state_manager.get_products(user_id) or ""
    
    recipe = await GroqService.generate_recipe(dish_name, products)
    await wait_msg.delete()
    
    # Проверяем, не отказал ли AI (есть ли ⛔ в начале)
    if recipe.startswith("⛔") or recipe.startswith("🍳"):
        # Это отказ или пустой рецепт - отправляем без кнопки повтора
        await message.answer(recipe, reply_markup=get_recipe_error_keyboard(), parse_mode="HTML")
        return
    
    # Сохраняем информацию о текущем блюде
    state_manager.set_current_dish(user_id, dish_name)
    state_manager.set_state(user_id, "recipe_sent")
    
    # Отправляем рецепт с кнопками навигации
    await message.answer(recipe, reply_markup=get_recipe_back_keyboard(), parse_mode="HTML")

# --- CALLBACKS ---

async def handle_callback(callback: CallbackQuery):
    """Обработка всех inline-кнопок"""
    user_id = callback.from_user.id
    data = callback.data
    
    try:
        if data == "restart":
            # Сброс сессии
            state_manager.clear_session(user_id)
            await callback.message.edit_text(
                "🗑 <b>Сессия сброшена</b>\n\nВсе продукты удалены. Жду новый список!",
                parse_mode="HTML"
            )
        
        elif data.startswith("style_"):
            # Выбор стиля готовки
            style = "домашний" if "ordinary" in data else "экзотический"
            products = state_manager.get_products(user_id)
            if not products:
                await callback.answer("Сначала отправьте продукты!")
                return
                
            await callback.message.delete()
            await start_category_flow(callback.message, user_id, products, style)
        
        elif data.startswith("cat_"):
            # Выбор категории
            category = data.split("_")[1]
            products = state_manager.get_products(user_id)
            category_name = CATEGORY_MAP.get(category, category.capitalize())
            
            await callback.message.edit_text(
                f"🔍 <b>Подбираю рецепты в категории:</b> {category_name}...",
                parse_mode="HTML"
            )
            
            # Получаем стиль из состояния
            style_state = state_manager.get_state(user_id)
            style = "домашний" if "ordinary" in str(style_state) else "экзотический"
            
            dishes = await GroqService.generate_dishes_list(products, category, style)
            
            if not dishes:
                await callback.message.edit_text(
                    f"😕 <b>Не нашёл рецептов в категории {category_name}</b>\n\nПопробуйте другую категорию или добавьте больше продуктов.",
                    reply_markup=get_categories_keyboard(state_manager.get_categories(user_id)),
                    parse_mode="HTML"
                )
                return
            
            state_manager.set_generated_dishes(user_id, dishes)
            
            # Красивый вывод меню
            menu_text = f"📋 <b>Предлагаю приготовить ({category_name}):</b>\n\n"
            for i, d in enumerate(dishes, 1):
                display_name = d.get('display_name', d['name'])
                desc = d.get('desc', '')
                menu_text += f"{i}. <b>{display_name}</b>\n{desc}\n\n"
            
            await callback.message.edit_text(
                menu_text, 
                reply_markup=get_dishes_keyboard(dishes), 
                parse_mode="HTML"
            )
        
        elif data.startswith("dish_"):
            # Выбор конкретного блюда
            try:
                index = int(data.split("_")[1])
                dish_name = state_manager.get_generated_dish(user_id, index)
                if not dish_name:
                    await callback.answer("Блюдо не найдено, выберите другое")
                    return
                    
                await callback.message.delete()
                await generate_and_send_recipe(callback.message, user_id, dish_name)
            except (ValueError, IndexError) as e:
                logger.error(f"Error parsing dish index: {e}")
                await callback.answer("Ошибка выбора блюда")
        
        elif data == "back_to_categories":
            # Возврат к категориям
            categories = state_manager.get_categories(user_id)
            if categories:
                categories_text = "\n".join([f"• {CATEGORY_MAP.get(cat, cat.capitalize())}" for cat in categories])
                await callback.message.edit_text(
                    f"📂 <b>Выберите категорию блюда:</b>\n\nДоступные категории:\n{categories_text}",
                    reply_markup=get_categories_keyboard(categories), 
                    parse_mode="HTML"
                )
            else:
                await callback.message.edit_text(
                    "📝 <b>Сессия устарела</b>\n\nНачните заново, отправив список продуктов.",
                    parse_mode="HTML"
                )
        
        elif data == "repeat_recipe":
            # Повторная генерация рецепта
            dish_name = state_manager.get_current_dish(user_id)
            if dish_name:
                await callback.message.delete()
                await generate_and_send_recipe(callback.message, user_id, dish_name)
            else:
                await callback.answer("Сначала выберите блюдо")
        
        else:
            await callback.answer("Неизвестная команда")
        
    except Exception as e:
        logger.error(f"Callback error for user {user_id}, data {data}: {e}")
        await callback.answer("Произошла ошибка, попробуйте позже")
    
    await callback.answer()

def register_handlers(dp: Dispatcher):
    """Регистрация всех хэндлеров"""
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_author, Command("author"))
    dp.message.register(handle_voice, F.voice)
    dp.message.register(handle_text, F.text)
    dp.callback_query.register(handle_callback)
