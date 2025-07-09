# Budget Tracker Bot

This project implements a Telegram bot for managing a family budget. The bot stores all data in Google Sheets and allows multiple family members to track expenses together.

## Features

- Create a new family budget and generate an invite code
- Join an existing family by invite code
- Add expenses via an interactive conversation
- View a monthly report grouped by categories, users, and currencies

The bot is built with `python-telegram-bot` and uses the Google Sheets API via `gspread`.

## Running the Bot

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Place your Google API credentials in `credentials.json` and ensure the bot has access to the target spreadsheets.
3. Set the `TELEGRAM_BOT_TOKEN` environment variable with your bot token and `INDEX_SHEET_ID` with the ID of the index spreadsheet.
4. Run:
   ```bash
   python main.py
   ```

The first time you create a budget, OAuth authorization will be required to allow the bot to create and edit spreadsheets on your behalf.
