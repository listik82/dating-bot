import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from handlers import router

logging.basicConfig(level=logging.INFO)

WEBHOOK_HOST = os.getenv("RAILWAY_PUBLIC_DOMAIN")
WEBHOOK_PORT = int(os.getenv("PORT", "8080"))
WEBHOOK_PATH = "/webhook"

async def on_startup(bot: Bot):
    if WEBHOOK_HOST:
        webhook_url = f"https://{WEBHOOK_HOST}{WEBHOOK_PATH}"
        await bot.set_webhook(webhook_url)
        logging.info(f"Webhook set: {webhook_url}")

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    logging.info("Webhook deleted")

async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    dp.include_router(router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    if WEBHOOK_HOST:
        # Webhook mode (Railway)
        from aiohttp import web

        async def handle(request):
            return web.Response(text="Bot is running")

        async def webhook_handle(request):
            from aiogram.types import Update
            data = await request.json()
            update = Update(**data)
            await dp.feed_update(bot, update)
            return web.Response()

        app = web.Application()
        app.router.add_get("/", handle)
        app.router.add_post(WEBHOOK_PATH, webhook_handle)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", WEBHOOK_PORT)
        await site.start()
        logging.info(f"Server started on port {WEBHOOK_PORT}")

        # Keep running
        while True:
            await asyncio.sleep(3600)
    else:
        # Polling mode (local)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
