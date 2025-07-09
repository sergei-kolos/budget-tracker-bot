import logging
import os

from budget_tracker.bot import BudgetBot

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
INDEX_SHEET_ID = os.getenv("INDEX_SHEET_ID")

if not TOKEN or not INDEX_SHEET_ID:
    raise RuntimeError("TELEGRAM_BOT_TOKEN and INDEX_SHEET_ID must be set")

bot = BudgetBot(TOKEN, INDEX_SHEET_ID)
bot.run()
