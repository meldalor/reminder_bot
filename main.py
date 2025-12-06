"""Main entry point for the Telegram reminder bot."""

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import API_TOKEN, CHECK_INTERVAL_SECONDS
from bot.database import create_db
from bot.handlers import start_router, reminders_router, timezone_router
from bot.services import send_reminders

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Execute on bot startup."""
    logger.info("Starting reminder bot...")
    await create_db()
    logger.info("Database initialized")

    # Start scheduler for sending reminders
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_reminders,
        "interval",
        seconds=CHECK_INTERVAL_SECONDS,
        args=[bot]
    )
    scheduler.start()
    logger.info(f"Scheduler started (check interval: {CHECK_INTERVAL_SECONDS}s)")


async def main():
    """Main function to run the bot."""
    # Validate configuration
    if not API_TOKEN:
        logger.error("BOT_TOKEN is not set in .env file!")
        return

    # Initialize bot and dispatcher
    bot = Bot(token=API_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register routers
    dp.include_router(start_router)
    dp.include_router(timezone_router)
    dp.include_router(reminders_router)

    # Register startup handler
    async def startup_wrapper():
        await on_startup(bot)

    dp.startup.register(startup_wrapper)

    try:
        logger.info("Bot is running...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error occurred: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
