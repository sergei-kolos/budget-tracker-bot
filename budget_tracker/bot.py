from __future__ import annotations

import logging
from enum import Enum, auto

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from .google_sheets import SheetsManager

logger = logging.getLogger(__name__)

CATEGORIES = [
    "Еда 🍔",
    "Транспорт 🚕",
    "Жильё 🏠",
    "Подписки 📺",
    "Покупки 🛍️",
    "Медицина 💊",
    "Развлечения 🎮",
    "Коты 🐾",
    "Другое 📝",
]

CURRENCIES = ["USD", "AED", "BYN"]

class ExpenseState(Enum):
    CATEGORY = auto()
    AMOUNT = auto()
    CURRENCY = auto()


class BudgetBot:
    def __init__(self, token: str, index_sheet_id: str) -> None:
        self.app = Application.builder().token(token).build()
        self.sheets = SheetsManager(index_sheet_id)
        self._register_handlers()

    def _register_handlers(self) -> None:
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("create_budget", self.create_budget))
        self.app.add_handler(CommandHandler("join_budget", self.join_budget))
        self.app.add_handler(CommandHandler("monthly_report", self.monthly_report))

        add_expense_conv = ConversationHandler(
            entry_points=[CommandHandler("add_expense", self.add_expense_start)],
            states={
                ExpenseState.CATEGORY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_expense_category)
                ],
                ExpenseState.AMOUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_expense_amount)
                ],
                ExpenseState.CURRENCY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_expense_currency)
                ],
            },
            fallbacks=[],
        )
        self.app.add_handler(add_expense_conv)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "Привет! Я бот для ведения семейного бюджета. "
            "Используйте /create_budget чтобы создать бюджет или /join_budget <code> чтобы присоединиться."
        )

    async def create_budget(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        sheet_id, invite_code = self.sheets.create_family(user.id, user.first_name)
        await update.message.reply_text(
            f"Создан новый бюджет! Код приглашения: {invite_code}"
        )
        logger.info("Created budget %s for user %s", sheet_id, user.id)

    async def join_budget(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not context.args:
            await update.message.reply_text("Укажите код: /join_budget <code>")
            return
        code = context.args[0].strip().upper()
        sheet_id = self.sheets.find_family_by_invite(code)
        if not sheet_id:
            await update.message.reply_text("Код не найден")
            return
        self.sheets.add_member(sheet_id, update.effective_user.id)
        await update.message.reply_text("Вы присоединились к бюджету!")

    # ----- Add expense conversation -----
    async def add_expense_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ExpenseState:
        keyboard = [[c] for c in CATEGORIES]
        await update.message.reply_text(
            "Выберите категорию:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return ExpenseState.CATEGORY

    async def add_expense_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ExpenseState:
        context.user_data["category"] = update.message.text
        await update.message.reply_text("Введите сумму:")
        return ExpenseState.AMOUNT

    async def add_expense_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> ExpenseState:
        try:
            amount = float(update.message.text)
        except ValueError:
            await update.message.reply_text("Введите число")
            return ExpenseState.AMOUNT
        context.user_data["amount"] = amount
        keyboard = [[c] for c in CURRENCIES]
        await update.message.reply_text(
            "Выберите валюту:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return ExpenseState.CURRENCY

    async def add_expense_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        currency = update.message.text
        user_id = update.effective_user.id
        sheet_id = self.sheets.find_family_by_user(user_id)
        if not sheet_id:
            await update.message.reply_text("Вы не присоединились к бюджету")
            return ConversationHandler.END
        self.sheets.append_expense(
            sheet_id,
            user_id,
            update.effective_user.first_name,
            context.user_data["category"],
            context.user_data["amount"],
            currency,
        )
        await update.message.reply_text("Трата добавлена")
        return ConversationHandler.END

    async def monthly_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        sheet_id = self.sheets.find_family_by_user(user_id)
        if not sheet_id:
            await update.message.reply_text("Вы не присоединились к бюджету")
            return
        report = self.sheets.monthly_report(sheet_id)
        await update.message.reply_text(report)

    def run(self) -> None:
        self.app.run_polling()
