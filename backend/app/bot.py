import logging
import sys

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10  # секунд


async def request_auth_code(telegram_id: int, telegram_username: str) -> httpx.Response:
    """Запросить у API код авторизации"""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        return await client.post(
            f"{settings.BACKEND_URL.rstrip('/')}/api/auth/telegram/generate-code",
            json={"telegram_id": telegram_id, "telegram_username": telegram_username},
            headers={"X-Bot-Secret": settings.bot_api_secret},
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start — выдать код"""
    settings = get_settings()
    user = update.effective_user
    username = user.username or f"user_{user.id}"

    try:
        response = await request_auth_code(user.id, username)
        if response.status_code != 200:
            logger.error("generate-code вернул %s", response.status_code)
            await update.message.reply_text("Ошибка сервера. Попробуйте позже.")
            return

        code = response.json()["code"]
        await update.message.reply_text(
            f"Ваш код авторизации:\n\n"
            f"<b>{code}</b>\n\n"
            f"Код действителен {settings.CODE_EXPIRY_MINUTES} минут\n\n"
            f"Вставьте этот код на сайте:\n"
            f"<a href='{settings.FRONTEND_URL}'>Перейти на сайт</a>",
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("Ошибка при обработке команды /start")
        await update.message.reply_text("Ошибка подключения. Попробуйте позже.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Помощь\n\n"
        "/start - Получить код авторизации\n"
        "/help - Показать эту справку\n\n"
        "Вставьте полученный код на сайте, чтобы авторизоваться."
    )


def main() -> None:
    settings = get_settings()
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен")
        sys.exit(1)

    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    logger.info("Бот запущен (API: %s)", settings.BACKEND_URL)
    app.run_polling()


if __name__ == "__main__":
    main()
