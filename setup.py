"""
Run once to initialize Google Sheets with correct headers.
Usage: python setup.py
"""
from dotenv import load_dotenv
load_dotenv()

from sheets_service import setup_sheets

if __name__ == "__main__":
    print("Setting up Google Sheets...")
    setup_sheets()
    print("\nDone. All sheets ready.")
    print("You can now start the bot: python bot.py")
