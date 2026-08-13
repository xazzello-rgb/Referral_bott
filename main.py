import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from database.database import engine, Base

# Jadval yaratish uchun modellarni chaqiramiz
import database.models 

from utils.logger import logger

async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Baza muvaffaqiyatli yaratildi va ulandi.")

async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    # Boshlang'ich sozlamalarni bajaramiz
    await on_startup()
    
    # Routerni ulash
    from handlers.start import router as start_router
    from handlers.user import router as user_router
    from handlers.admin import router as admin_router

    dp.include_router(start_router)
    dp.include_router(user_router)
    dp.include_router(admin_router)
    
    logger.info("Bot ishga tushdi...")
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), drop_pending_updates=True)
    finally:
        await bot.session.close()
        await engine.dispose()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")