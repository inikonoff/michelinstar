import os
from aiogram import Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from utils import VoiceProcessor
from groq_service import GroqService
from state_manager import state_manager

# Инициализация сервисов
voice_processor = VoiceProcessor()
groq_service = GroqService()

# --- ВСПОМОГАТЕЛЬНЫЕ КЛАВИАТУРЫ ---

def get_style_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора стиля"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏠 Простое / Домашнее", callback_data="style_ordinary"),
            InlineKeyboardButton(text="🌶 Экзотическое", callback_data="style_exotic")
        ]
    ])

def get_restart_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой рестарта"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Заново", callback_data="restart")]
    ])

def get_hide_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для скрытия рецепта"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Скрыть", callback_data="delete_msg")]
    ])

# --- ХЭНДЛЕРЫ ---

async def cmd_start(message: Message):
    user_id = message.from_user.id
    state_manager.clear_history(user_id)
    state_manager.clear_state(user_id)
    await message.answer(
        "👋 Здравствуйте.\n\n"
        "🎤 <b>Отправьте</b> голосовое или текстовое сообщение с перечнем продуктов, и я подскажу, что из них можно приготовить.\n"
        '📝 Или напишите <b>"Дай рецепт [блюдо]"</b>.',
        parse_mode="HTML"
    )

async def cmd_author(message: Message):
    await message.answer(
        "👨‍💻 <b>Разработчик бота:</b> @inikonoff\n\n"
        "Пишите по вопросам и предложениям!",
        parse_mode="HTML"
    )

async def handle_easter_egg_recipe(message: Message):
    user_id = message.from_user.id
    dish_name = message.text.lower().replace("дай рецепт", "", 1).strip()
    if not dish_name:
        await message.answer("Напиши название блюда. Например: <b>Дай рецепт Пицца</b>")
        return

    wait_msg = await message.answer(f"⚡️ Ищу рецепт: {dish_name}...")
    try:
        recipe = await groq_service.generate_freestyle_recipe(dish_name)
        await wait_msg.delete()
        
        # Отправляем только текст
        await message.answer(recipe, reply_markup=get_hide_keyboard(), parse_mode="HTML")
        
        state_manager.set_state(user_id, "recipe_sent")
    except Exception as e:
        await wait_msg.delete()
        await message.answer(f"Ошибка: {e}")

async def handle_delete_msg(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()

# --- ОБРАБОТКА ПРОДУКТОВ ---

async def handle_voice(message: Message):
    user_id = message.from_user.id
    processing_msg = await message.answer("🎧 Слушаю...")
    temp_file = f"temp/voice_{user_id}_{message.voice.file_id}.ogg"
    
    try:
        await message.bot.download(message.voice, destination=temp_file)
        text = await voice_processor.process_voice(temp_file)
        await processing_msg.delete()
        
        history = state_manager.get_history(user_id)
        if not history:
            await handle_initial_products(message, user_id, text)
        else:
            await handle_user_choice(message, user_id, text)
            
    except Exception as e:
        await processing_msg.delete()
        await message.answer(f"😕 Не разобрал: {e}")
        if os.path.exists(temp_file):
            try: os.remove(temp_file)
            except: pass

async def handle_initial_products(message: Message, user_id: int, products: str):
    # 1. ВАЛИДАЦИЯ
    is_valid = await groq_service.validate_ingredients(products)
    
    if not is_valid:
        await message.answer(
            f"🤨 <b>\"{products}\"</b> — это не похоже на список продуктов для готовки.\n\n"
            "Перечислите ингредиенты, например: <i>Курица, картошка, лук</i>.",
            parse_mode="HTML"
        )
        return

    state_manager.add_message(user_id, "user", products)
    state_manager.clear_state(user_id)
    
    # ИСПРАВЛЕННАЯ СТРОКА:
    await message.answer(
        f"✅ Принято: <b>{products}</b>\n\nКакое блюдо вы хотите приготовить?",
        reply_markup=get_style_keyboard(),
        parse_mode="HTML"
    )

async def handle_style_selection_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    style_code = callback.data
    style_name = "простой, домашний" if style_code == "style_ordinary" else "экзотический, необычный"
    
    await callback.answer(f"Выбран стиль: {style_name}")
    products = state_manager.get_products(user_id)
    
    if not products:
        await callback.message.answer("Потерял список продуктов 😢 Начните заново /start")
        return

    await callback.message.edit_text(f"🍳 Подбираю {style_name}е рецепты из: {products}...")
    
    try:
        response = await groq_service.generate_dishes(products, style=style_name)
        state_manager.add_message(user_id, "bot", response)
        
        await callback.message.delete()
        await callback.message.answer(response, reply_markup=get_restart_keyboard())
        
    except Exception as e:
        await callback.message.edit_text(f"Ошибка нейросети: {e}")

# --- ВЫБОР БЛЮДА ИЛИ ДОБАВЛЕНИЕ ---

async def handle_user_choice(message: Message, user_id: int = None, text: str = None):
    # Если вызвал Aiogram (текстовое сообщение), аргументов не будет
    if user_id is None:
        user_id = message.from_user.id
    if text is None:
        text = message.text

    # --- ПРОВЕРКА НА СПАСИБО ---
    thanks_words = ["спасибо", "спс", "благодарю", "thanks", "пасиб", "от души", "мпасибо", "спасиб", "спасибр", "сиба", "сэнкью"]
    
    if text.lower().strip(" .!") in thanks_words:
        current_state = state_manager.get_state(user_id)
        if current_state == "recipe_sent":
            await message.answer("На здоровье! 👨‍🍳 Заходите ещё!")
            state_manager.clear_state(user_id)
            return

    last_bot_msg = state_manager.get_last_bot_message(user_id)
    
    if not last_bot_msg:
        await handle_initial_products(message, user_id, text)
        return

    wait_msg = await message.answer("🤔 Обрабатываю...")
    try:
        intent = await groq_service.determine_intent(text, last_bot_msg)
        await wait_msg.delete()

        if intent.get("intent") == "select_dish":
            await handle_dish_selection(message, user_id, intent.get("dish_name"))
        elif intent.get("intent") == "add_products":
            await handle_add_products(message, user_id, intent.get("products"))
        else:
            await message.answer("Не понял. Нажми на блюдо из списка или добавь продукты (например: 'добавь сыр').")
    except Exception as e:
        await wait_msg.delete()
        await message.answer(f"Ошибка: {e}")

async def handle_dish_selection(message: Message, user_id: int, dish_name: str):
    wait_msg = await message.answer(f"👨‍🍳 Пишу рецепт: {dish_name}...")
    try:
        products = state_manager.get_products(user_id)
        recipe = await groq_service.generate_recipe(dish_name, products)
        
        await wait_msg.delete()
        
        await message.answer(recipe, reply_markup=get_restart_keyboard(), parse_mode="HTML")
        
        state_manager.clear_history(user_id)
        state_manager.set_state(user_id, "recipe_sent")
        
    except Exception as e:
        await wait_msg.delete()
        await message.answer(f"Ошибка рецепта: {e}")

async def handle_add_products(message: Message, user_id: int, new_products: str):
    # ВАЛИДАЦИЯ
    is_valid = await groq_service.validate_ingredients(new_products)
    
    if not is_valid:
        await message.answer(f"🤨 <b>\"{new_products}\"</b> — не похоже на продукты. Попробуйте еще раз.")
        return

    state_manager.update_products(user_id, new_products)
    all_products = state_manager.get_products(user_id)
    wait_msg = await message.answer(f"➕ Добавил: {new_products}. Обновляю меню...")
    try:
        response = await groq_service.generate_dishes(all_products, style="с учетом новых продуктов")
        state_manager.add_message(user_id, "bot", response)
        await wait_msg.delete()
        
        await message.answer(response, reply_markup=get_restart_keyboard())
        
    except Exception as e:
        await wait_msg.delete()
        await message.answer(f"Ошибка: {e}")

async def handle_restart(callback: CallbackQuery):
    user_id = callback.from_user.id
    state_manager.clear_history(user_id)
    state_manager.clear_state(user_id)
    await callback.message.answer("Сброс! Жду список продуктов.")
    await callback.answer()

def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_author, Command("author"))
    
    dp.message.register(handle_easter_egg_recipe, F.text.lower().startswith("дай рецепт"))
    dp.message.register(handle_voice, F.voice)
    dp.message.register(handle_user_choice, F.text)
    
    dp.callback_query.register(handle_restart, F.data == "restart")
    dp.callback_query.register(handle_delete_msg, F.data == "delete_msg")
    dp.callback_query.register(handle_style_selection_callback, F.data.startswith("style_"))
