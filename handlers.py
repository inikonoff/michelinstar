import os
from aiogram import Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from utils import VoiceProcessor
from groq_service import GroqService
from image_service import ImageService
from state_manager import state_manager

# Инициализация сервисов
voice_processor = VoiceProcessor()
groq_service = GroqService()
image_service = ImageService()

async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Очищаем историю при старте
    state_manager.clear_history(user_id)
    
    await message.answer(
        "Здравствуйте! 🎤\n"
        "Отправьте голосовое сообщение с перечислением продуктов из вашего холодильника."
    )

async def handle_voice(message: Message):
    """Обработчик голосовых сообщений"""
    user_id = message.from_user.id
    
    # Уведомляем о начале обработки
    processing_msg = await message.answer("🎧 Обрабатываю голосовое сообщение...")
    
    try:
        # Получаем файл голосового сообщения
        voice = message.voice
        file = await message.bot.get_file(voice.file_id)
        file_path = file.file_path
        
        # Скачиваем файл
        temp_file = f"temp/voice_{user_id}_{voice.file_id}.ogg"
        await message.bot.download_file(file_path, temp_file)
        
        # Распознаем речьimport os
from aiogram import Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from utils import VoiceProcessor
from groq_service import GroqService
from image_service import ImageService
from state_manager import state_manager

# Инициализация сервисов
voice_processor = VoiceProcessor()
groq_service = GroqService()
image_service = ImageService()

async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Очищаем историю при старте
    state_manager.clear_history(user_id)
    
    await message.answer(
        "Здравствуйте! 🎤\n"
        "Отправьте голосовое сообщение с перечислением продуктов из вашего холодильника."
    )

async def handle_voice(message: Message):
    """Обработчик голосовых сообщений"""
    user_id = message.from_user.id
    
    # Уведомляем о начале обработки
    processing_msg = await message.answer("🎧 Обрабатываю голосовое сообщение...")
    
    try:
        # Получаем файл голосового сообщения
        voice = message.voice
        file = await message.bot.get_file(voice.file_id)
        file_path = file.file_path
        
        # Скачиваем файл
        temp_file = f"temp/voice_{user_id}_{voice.file_id}.ogg"
        await message.bot.download_file(file_path, temp_file)
        
        # Распознаем речь
        recognized_text = await voice_processor.process_voice(temp_file)
        
        # Удаляем временный файл
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        await processing_msg.delete()
        
        # Проверяем, первое ли это сообщение (список продуктов) или выбор блюда
        history = state_manager.get_history(user_id)
        
        if len(history) == 0:
            # Первое сообщение - это список продуктов
            await handle_initial_products(message, user_id, recognized_text)
        else:
            # Последующее сообщение - выбор блюда или добавление продуктов
            await handle_user_choice(message, user_id, recognized_text)
            
    except Exception as e:
        await processing_msg.delete()
        await message.answer(
            f"❌ Ошибка обработки голосового сообщения: {str(e)}\n\n"
            "Попробуйте ещё раз или говорите четче."
        )

async def handle_initial_products(message: Message, user_id: int, products: str):
    """Обработка первого сообщения с продуктами"""
    # Сохраняем продукты в историю
    state_manager.add_message(user_id, "user", products)
    
    # Уведомляем
    thinking_msg = await message.answer("🔍 Ищу рецепты на основе ваших продуктов...")
    
    try:
        # Генерируем список блюд через Groq
        dishes_text = await groq_service.generate_dishes(products)
        
        # Сохраняем ответ бота в историю
        state_manager.add_message(user_id, "bot", dishes_text)
        
        await thinking_msg.delete()
        await message.answer(dishes_text)
        
    except Exception as e:
        await thinking_msg.delete()
        await message.answer(
            f"❌ Ошибка генерации рецептов: {str(e)}\n\n"
            "Попробуйте ещё раз."
        )

async def handle_user_choice(message: Message, user_id: int, user_message: str):
    """Обработка выбора пользователя (блюдо или продукты)"""
    # Получаем последний ответ бота со списком блюд
    last_bot_message = state_manager.get_last_bot_message(user_id)
    
    if not last_bot_message:
        await message.answer("❌ Ошибка: история диалога потеряна. Начните заново с /start")
        return
    
    thinking_msg = await message.answer("🤔 Обрабатываю ваш выбор...")
    
    try:
        # Определяем намерение через Groq
        intent_result = await groq_service.determine_intent(user_message, last_bot_message)
        
        await thinking_msg.delete()
        
        if intent_result["intent"] == "select_dish":
            # Пользователь выбрал блюдо
            await handle_dish_selection(message, user_id, intent_result["dish_name"])
            
        elif intent_result["intent"] == "add_products":
            # Пользователь добавляет продукты
            await handle_add_products(message, user_id, intent_result["products"])
            
        else:
            # Не удалось понять намерение
            await message.answer(
                "🤷‍♂️ Не понял ваш выбор.\n\n"
                "Пожалуйста, назовите блюдо из предложенного списка или "
                "перечислите продукты, которые хотите добавить."
            )
            
    except Exception as e:
        await thinking_msg.delete()
        await message.answer(
            f"❌ Ошибка обработки: {str(e)}\n\n"
            "Попробуйте ещё раз."
        )

async def handle_dish_selection(message: Message, user_id: int, dish_name: str):
    """Обработка выбора конкретного блюда"""
    thinking_msg = await message.answer(f"👨‍🍳 Готовлю рецепт для: {dish_name}...")
    
    try:
        # Получаем список продуктов
        products = state_manager.get_products(user_id)
        
        # Генерируем детальный рецепт
        recipe = await groq_service.generate_recipe(dish_name, products)
        
        # Ищем изображение блюда
        image_url = await image_service.search_dish_image(dish_name)
        
        await thinking_msg.delete()
        
        # Отправляем изображение, если найдено
        if image_url:
            try:
                await message.answer_photo(
                    photo=image_url,
                    caption=recipe,
                    reply_markup=get_restart_keyboard()
                )
            except:
                # Если не удалось отправить фото, отправляем только текст
                await message.answer(
                    recipe,
                    reply_markup=get_restart_keyboard()
                )
        else:
            await message.answer(
                recipe,
                reply_markup=get_restart_keyboard()
            )
        
        # Очищаем историю после выдачи рецепта
        state_manager.clear_history(user_id)
        
    except Exception as e:
        await thinking_msg.delete()
        await message.answer(
            f"❌ Ошибка генерации рецепта: {str(e)}"
        )

async def handle_add_products(message: Message, user_id: int, new_products: str):
    """Обработка добавления новых продуктов"""
    thinking_msg = await message.answer("➕ Добавляю продукты и обновляю список блюд...")
    
    try:
        # Добавляем новые продукты
        state_manager.update_products(user_id, new_products)
        
        # Получаем обновленный список продуктов
        all_products = state_manager.get_products(user_id)
        
        # Генерируем новый список блюд
        dishes_text = await groq_service.generate_dishes(all_products)
        
        # Обновляем историю
        state_manager.add_message(user_id, "bot", dishes_text)
        
        await thinking_msg.delete()
        await message.answer(
            f"✅ Добавлены продукты: {new_products}\n\n{dishes_text}"
        )
        
    except Exception as e:
        await thinking_msg.delete()
        await message.answer(
            f"❌ Ошибка обновления: {str(e)}"
        )

async def handle_restart_callback(callback: CallbackQuery):
    """Обработчик кнопки 'Приготовить ещё'"""
    user_id = callback.from_user.id
    
    # Очищаем историю
    state_manager.clear_history(user_id)
    
    await callback.message.answer(
        "🔄 Начинаем заново!\n\n"
        "🎤 Отправьте голосовое сообщение с продуктами из холодильника."
    )
    await callback.answer()

def get_restart_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой перезапуска"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Приготовить ещё", callback_data="restart")]
    ])
    return keyboard

def register_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков"""
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(handle_voice, F.voice)
    dp.callback_query.register(handle_restart_callback, F.data == "restart")
        recognized_text = await voice_processor.process_voice(temp_file)
        
        # Удаляем временный файл
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        await processing_msg.delete()
        
        # Проверяем, первое ли это сообщение (список продуктов) или выбор блюда
        history = state_manager.get_history(user_id)
        
        if len(history) == 0:
            # Первое сообщение - это список продуктов
            await handle_initial_products(message, user_id, recognized_text)
        else:
            # Последующее сообщение - выбор блюда или добавление продуктов
            await handle_user_choice(message, user_id, recognized_text)
            
    except Exception as e:
        await processing_msg.delete()
        await message.answer(
            f"❌ Ошибка обработки голосового сообщения: {str(e)}\n\n"
            "Попробуйте ещё раз или говорите четче."
        )

async def handle_initial_products(message: Message, user_id: int, products: str):
    """Обработка первого сообщения с продуктами"""
    # Сохраняем продукты в историю
    state_manager.add_message(user_id, "user", products)
    
    # Уведомляем
    thinking_msg = await message.answer("🔍 Ищу рецепты на основе ваших продуктов...")
    
    try:
        # Генерируем список блюд через Groq
        dishes_text = await groq_service.generate_dishes(products)
        
        # Сохраняем ответ бота в историю
        state_manager.add_message(user_id, "bot", dishes_text)
        
        await thinking_msg.delete()
        await message.answer(dishes_text)
        
    except Exception as e:
        await thinking_msg.delete()
        await message.answer(
            f"❌ Ошибка генерации рецептов: {str(e)}\n\n"
            "Попробуйте ещё раз."
        )

async def handle_user_choice(message: Message, user_id: int, user_message: str):
    """Обработка выбора пользователя (блюдо или продукты)"""
    # Получаем последний ответ бота со списком блюд
    last_bot_message = state_manager.get_last_bot_message(user_id)
    
    if not last_bot_message:
        await message.answer("❌ Ошибка: история диалога потеряна. Начните заново с /start")
        return
    
    thinking_msg = await message.answer("🤔 Обрабатываю ваш выбор...")
    
    try:
        # Определяем намерение через Groq
        intent_result = await groq_service.determine_intent(user_message, last_bot_message)
        
        await thinking_msg.delete()
        
        if intent_result["intent"] == "select_dish":
            # Пользователь выбрал блюдо
            await handle_dish_selection(message, user_id, intent_result["dish_name"])
            
        elif intent_result["intent"] == "add_products":
            # Пользователь добавляет продукты
            await handle_add_products(message, user_id, intent_result["products"])
            
        else:
            # Не удалось понять намерение
            await message.answer(
                "🤷‍♂️ Не понял ваш выбор.\n\n"
                "Пожалуйста, назовите блюдо из предложенного списка или "
                "перечислите продукты, которые хотите добавить."
            )
            
    except Exception as e:
        await thinking_msg.delete()
        await message.answer(
            f"❌ Ошибка обработки: {str(e)}\n\n"
            "Попробуйте ещё раз."
        )

async def handle_dish_selection(message: Message, user_id: int, dish_name: str):
    """Обработка выбора конкретного блюда"""
    thinking_msg = await message.answer(f"👨‍🍳 Готовлю рецепт для: {dish_name}...")
