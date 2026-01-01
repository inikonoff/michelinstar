import asyncio
import os
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage # Важно для хранения продуктов
from aiohttp import web  # Для Health Check на Render

from config import TELEGRAM_TOKEN
from handlers import register_handlers

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# --- ИНИЦИАЛИЗАЦИЯ ---
# MemoryStorage хранит данные в ОЗУ. Идеально для Render.
storage = MemoryStorage()
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(storage=storage)

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (HEALTH CHECK) ---
async def health_check(request):
    """Render будет пинговать этот адрес, чтобы знать, что бот жив"""
    return web.Response(text="Bot is running OK", status=200)

async def start_web_server():
    """Запускает фоновый веб-сервер на порту, который выдает Render"""
    try:
        app = web.Application()
        app.router.add_get('/', health_check)
        app.router.add_get('/health', health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        
        # Порт берется из переменной окружения Render, по умолчанию 8080
        port = int(os.environ.get("PORT", 8080))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"✅ WEB SERVER STARTED ON PORT {port}")
    except Exception as e:
        logger.error(f"❌ Error starting web server: {e}")

# --- НАСТРОЙКА МЕНЮ КОМАНД ---
async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="🔄 Новые продукты / Рестарт"),
        BotCommand(command="/author", description="👨‍💻 Об авторе")
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("✅ Команды меню установлены")
    except Exception as e:
        logger.error(f"❌ Не удалось установить команды: {e}")

# --- ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА ---
async def main():
    logger.info("🤖 Starting bot initialization...")

    # 1. Запуск Health Check сервера (критично для Render)
    # Делаем это первым, чтобы Render зафиксировал открытый порт
    await start_web_server()

    # 2. Регистрация всех хэндлеров (импорт из вашего файла handlers.py)
    register_handlers(dp)
    
    # 3. Установка команд меню в интерфейсе Telegram
    await setup_bot_commands(bot)
    
    logger.info("🚀 Starting polling...")
    
    # 4. Сброс накопившихся обновлений и запуск бесконечного цикла (polling)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Polling error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
