"""Database operations for the reminder bot."""

import aiosqlite
from bot.config import DB_PATH


async def create_db():
    """Create database tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name_reminder TEXT NOT NULL,
            frequency TEXT NOT NULL,
            dates TEXT NOT NULL,
            times TEXT NOT NULL,
            active INTEGER NOT NULL,
            expiration_time TEXT,
            last_message_id INTEGER,
            created_at TEXT,
            completed_at TEXT
        )
        ''')
        await db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            timezone TEXT NOT NULL,
            onboarding_completed INTEGER DEFAULT 0
        )
        ''')
        await db.execute('''
        CREATE TABLE IF NOT EXISTS reminder_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reminder_id INTEGER,
            user_id INTEGER NOT NULL,
            name_reminder TEXT NOT NULL,
            frequency TEXT NOT NULL,
            dates TEXT NOT NULL,
            times TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            action TEXT NOT NULL
        )
        ''')
        await db.commit()


async def get_user_timezone(user_id: int) -> str | None:
    """
    Get user's timezone from database.

    Args:
        user_id: Telegram user ID

    Returns:
        Timezone string or None if not set
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT timezone FROM users WHERE user_id = ?',
            (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None
