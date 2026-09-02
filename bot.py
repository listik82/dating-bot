import asyncio
import os
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.memory import MemoryStorage

from handlers import router
import database as db

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан! Добавьте переменную BOT_TOKEN в Railway.")

# --- FSM ХРАНИЛИЩЕ ---
if REDIS_URL:
    storage = RedisStorage.from_url(REDIS_URL)
    logging.info("FSM: используется Redis — сессии сохраняются при перезапуске!")
else:
    storage = MemoryStorage()
    logging.warning("FSM: используется MemoryStorage — сессии будут теряться при перезапуске!")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=storage)

async def main():
    db.init_db()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
