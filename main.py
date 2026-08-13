import asyncio
import logging

from aiogram import Bot, Dispatcher
from app.config import Settings
from app.db import init_db, create_tables
from app.handlers import router, setup_services

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

async def main():
    settings = Settings.from_env()
    init_db(settings)
    await create_tables()

    bot = Bot(settings.telegram_token)
    # Store owner ID on the bot instance for permission checks.
    bot._app_owner_id = settings.owner_id
    dp = Dispatcher()
    setup_services(settings)
    dp.include_router(router)

    logging.getLogger(__name__).info(
        "Bot started. Main Gemini model: %s", settings.gemini_model
    )
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
