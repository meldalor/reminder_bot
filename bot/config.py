"""Configuration settings for the reminder bot."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Bot configuration
API_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = DATA_DIR / "reminders.db"

# Scheduler settings
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", 60))
REMINDER_OFFSET_MINUTES = int(os.getenv("REMINDER_OFFSET_MINUTES", 15))
TEMP_REMINDER_EXPIRATION_HOURS = int(os.getenv("TEMP_REMINDER_EXPIRATION_HOURS", 1))

# Date and time formats
DATE_FORMAT = "%d.%m"
FULL_DATE_FORMAT = "%d.%m.%Y"
TIME_FORMAT = "%H:%M"
DATETIME_FORMAT = "%Y-%m-%d %H:%M"
FREQUENCY_ZERO = "0"
TEMP_YEAR = 2000

# City timezones (sorted by UTC offset descending)
CITY_TIMEZONES = {
    "Петропавловск-Камчатский (MSK+9)": "Asia/Kamchatka",
    "Магадан (MSK+8)": "Asia/Magadan",
    "Владивосток (MSK+7)": "Asia/Vladivostok",
    "Якутск (MSK+6)": "Asia/Yakutsk",
    "Иркутск (MSK+5)": "Asia/Irkutsk",
    "Красноярск (MSK+4)": "Asia/Krasnoyarsk",
    "Новосибирск (MSK+4)": "Asia/Novosibirsk",
    "Екатеринбург (MSK+2)": "Asia/Yekaterinburg",
    "Самара (MSK+1)": "Europe/Samara",
    "Москва (MSK)": "Europe/Moscow",
    "Калининград (MSK-1)": "Europe/Kaliningrad"
}
