from __future__ import annotations

import datetime as dt
from typing import Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, ContextTypes, ConversationHandler,
                          MessageHandler, CallbackQueryHandler, filters)

from .storage import LocalStorage
from .sheets import SheetsService

CATEGORY, AMOUNT, CURRENCY = range(3)

CATEGORIES = [
    "Еда 🍔", "Транспорт 🚕", "Жильё 🏠", "Подписки 📺",
    "Покупки 🛍️", "Медицина 💊", "Развлечения 🎮",
    "Коты 🐾", "Другое 📝",
]
CURRENCIES = ["USD", "AED", "BYN"]


def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    update.message.reply_text(
        "Добро пожаловать! Используйте /create_budget чтобы создать семью или /join_budget <code> чтобы присоединиться."  # noqa: E501
    )


def create_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    storage: LocalStorage = context.bot_data["storage"]
    sheets: SheetsService = context.bot_data["sheets"]

    if storage.get_sheet_by_user(user_id):
        update.message.reply_text("У вас уже есть семья.")
        return

    sheet = sheets.create_budget_sheet(user_id)
    storage.add_family(sheet.sheet_id, sheet.invite_code, user_id)
    update.message.reply_text(
        f"Семья создана! Код приглашения: {sheet.invite_code}"
    )


def join_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    storage: LocalStorage = context.bot_data["storage"]
    sheets: SheetsService = context.bot_data["sheets"]
    user_id = update.effective_user.id

    if storage.get_sheet_by_user(user_id):
        update.message.reply_text("Вы уже состоите в семье.")
        return

    if not context.args:
        update.message.reply_text("Использование: /join_budget <код>")
        return
    code = context.args[0].strip().upper()
    sheet_id = storage.get_sheet_by_invite(code)
    if not sheet_id:
        update.message.reply_text("Неверный код")
        return

    storage.add_user_to_family(sheet_id, user_id)
    sheets.add_member(sheet_id, user_id)
    update.message.reply_text("Вы присоединились к семье!")


async def ask_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(text=c, callback_data=c)] for c in CATEGORIES]
    await update.message.reply_text(
        "Выберите категорию:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CATEGORY


async def category_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["category"] = query.data
    await query.message.reply_text("Введите сумму:")
    return AMOUNT


async def amount_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["amount"] = update.message.text
    keyboard = [[InlineKeyboardButton(text=c, callback_data=c)] for c in CURRENCIES]
    await update.message.reply_text(
        "Выберите валюту:", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CURRENCY


async def currency_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    currency = query.data
    user = update.effective_user

    storage: LocalStorage = context.bot_data["storage"]
    sheets: SheetsService = context.bot_data["sheets"]
    sheet_id = storage.get_sheet_by_user(user.id)
    if not sheet_id:
        await query.message.reply_text("Вы не состоите в семье")
        return ConversationHandler.END

    row = [
        dt.datetime.utcnow().isoformat(),
        user.id,
        user.full_name,
        context.user_data.get("category"),
        context.user_data.get("amount"),
        currency,
    ]
    sheets.append_expense(sheet_id, row)
    await query.message.reply_text("Трата добавлена!")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено")
    return ConversationHandler.END


def monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    storage: LocalStorage = context.bot_data["storage"]
    sheets: SheetsService = context.bot_data["sheets"]
    user = update.effective_user
    sheet_id = storage.get_sheet_by_user(user.id)
    if not sheet_id:
        update.message.reply_text("Вы не состоите в семье")
        return

    records = sheets.fetch_month_records(sheet_id, dt.date.today())
    if not records:
        update.message.reply_text("Нет трат за текущий месяц")
        return

    report: Dict[str, Dict[str, float]] = {}
    for r in records:
        cat = r["category"]
        user_name = r["user_name"]
        key = f"{cat}/{user_name}/{r['currency']}"
        report[key] = report.get(key, 0) + float(r["amount"])

    lines = ["Отчёт за месяц:"]
    for key, amount in report.items():
        cat, user_name, cur = key.split("/")
        lines.append(f"{cat} - {user_name}: {amount} {cur}")
    update.message.reply_text("\n".join(lines))


def build_application(token: str, creds_path: str) -> Application:
    storage = LocalStorage()
    sheets = SheetsService(creds_path)

    application = Application.builder().token(token).build()
    application.bot_data["storage"] = storage
    application.bot_data["sheets"] = sheets

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("create_budget", create_budget))
    application.add_handler(CommandHandler("join_budget", join_budget))
    application.add_handler(CommandHandler("monthly_report", monthly_report))

    conv = ConversationHandler(
        entry_points=[CommandHandler("add_expense", ask_category)],
        states={
            CATEGORY: [CallbackQueryHandler(category_chosen)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_entered)],
            CURRENCY: [CallbackQueryHandler(currency_chosen)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv)

    return application


def main() -> None:
    import os

    token = os.environ.get("TELEGRAM_TOKEN")
    creds = os.environ.get("GOOGLE_CREDS", "service_account.json")
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN not set")
    app = build_application(token, creds)
    app.run_polling()


if __name__ == "__main__":
    main()
