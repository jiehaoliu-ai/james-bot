import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Google
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")  # Full JSON string from env var
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")

# App
TIMEZONE = "Asia/Singapore"
BASE_CURRENCY = "SGD"

# Sheet names
SHEET_EXPENSES = "Expenses"
SHEET_TODOS = "Todos"
SHEET_THOUGHTS = "Thoughts"
SHEET_REFLECTIONS = "Reflections"
SHEET_REMINDERS = "Reminders"

# Claude model
CLAUDE_MODEL = "claude-sonnet-4-5"
