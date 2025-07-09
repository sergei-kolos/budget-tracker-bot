# Budget Tracker Bot

Пример Telegram-бота для ведения семейного бюджета. Бот создаёт Google таблицы для семей,
позволяет присоединяться по коду, добавлять траты и получать месячные отчёты.

## Запуск

```bash
export TELEGRAM_TOKEN=...  # токен бота
export GOOGLE_CREDS=service_account.json  # путь к credentials
python -m budget_tracker.bot
```

Требования описаны в `requirements.txt`.
