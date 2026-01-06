import asyncio
import os
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config import TELEGRAM_TOKEN
from handlers import register_handlers
from aiohttp import web  # Для веб-сервера Render

# Настройка логирования (STDOUT важен для Render!)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# --- Веб-сервер для Render (Health Check) ---
async def health_check(request):
    return web.Response(text="Bot is running OK")

async def start_web_server():
    """Запускает заглушку веб-сервера"""
    try:
        app = web.Application()
        app.router.add_get('/', health_check)
        app.router.add_get('/health', health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        
        # Render передает порт через переменную окружения PORT
        port = int(os.environ.get("PORT", 8080))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"✅ WEB SERVER STARTED ON PORT {port}")
    except Exception as e:
        logger.error(f"❌ Error starting web server: {e}")

# --- НАСТРОЙКА МЕНЮ ---
async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="🔄 Рестарт / новые продукты"),
        BotCommand(command="/author", description="👨‍💻 Автор бота")
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception as e:
        logger.error(f"Не удалось установить команды: {e}")

# --- ГЛАВНАЯ ФУНКЦИЯ ---
async def main():
    logger.info("🤖 Инициализация...")

    # 1. САМОЕ ВАЖНОЕ: Сначала запускаем веб-сервер!
    # Это нужно сделать ДО любых запросов к Telegram, чтобы Render сразу увидел открытый порт.
    await start_web_server()

    # 2. Регистрируем обработчики
    register_handlers(dp)
    
    # 3. Настраиваем команды (может занять время, поэтому делаем после сервера)
    await setup_bot_commands(bot)
    
    logger.info("🚀 Запуск polling...")
    
    # 4. Удаляем вебхук и запускаем
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")