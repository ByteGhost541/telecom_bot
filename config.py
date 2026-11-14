# ==========================================
# ФАЙЛ config.py
# ==========================================
from dotenv import dotenv_values

env_config = dotenv_values(".env")

BOT_TOKEN = env_config.get("BOT_TOKEN")
PAYMENT_TOKEN = env_config.get("PAYMENT_TOKEN")
DB_URL = env_config.get("DB_URL", "sqlite+aiosqlite:///db.sqlite3")
GEMINI_API_KEY = env_config.get("GEMINI_API_KEY")