import asyncio
import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand # Импорт для команд
from config import TELEGRAM_TOKEN
from handlers import register_handlers
from aiohttp import web

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# --- Веб-сервер для Render (Health Check) ---
async def health_check(request):
    return web.Response(text="Bot is running OK")

async def start_web_server():
    """Запускает заглушку веб-сервера"""
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🌍 Web server started on port {port}")

# --- НАСТРОЙКА МЕНЮ ---
async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="🔄 Рестарт / Новые продукты"),
        BotCommand(command="/author", description="👨‍💻 Автор бота")
    ]
    await bot.set_my_commands(commands)

async def main():
    # Регистрация хэндлеров
    register_handlers(dp)
    
    # Установка команд в меню
    await setup_bot_commands(bot)
    
    logger.info("🤖 Бот запускается...")
    
    # Запускаем веб-сервер фоновой задачей
    await start_web_server()
    
    # Удаляем вебхук и запускаем поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
