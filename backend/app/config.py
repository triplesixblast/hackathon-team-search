import hashlib
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # База данных
    DATABASE_URL: str = "postgresql://itam:itam@localhost:5432/itam_hack"

    # JWT
    SECRET_KEY: str = ""
    ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = ""

    # Админ (создаётся командой `python -m app.cli create-admin`)
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""

    # Адреса сервисов
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    # Авторизация по коду
    CODE_EXPIRY_MINUTES: int = 10

    # CORS: список через запятую
    ALLOWED_ORIGINS: str = (
        "http://localhost:3000,http://localhost:3001,http://localhost:5173,http://localhost:8000"
    )

    # Сколько доверенных прокси стоит перед API (для определения IP клиента).
    # 0 — прямое подключение: X-Forwarded-For игнорируется, его можно подделать.
    TRUSTED_PROXY_HOPS: int = 1

    # Swagger / ReDoc / openapi.json
    ENABLE_DOCS: bool = True

    @field_validator("DATABASE_URL")
    @classmethod
    def _async_driver(cls, url: str) -> str:
        """postgres:// и postgresql://  -> драйвер asyncpg"""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+asyncpg://" + url[len(prefix):]
        return url

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def bot_api_secret(self) -> str:
        """Общий секрет бот <-> API (заголовок X-Bot-Secret), выводится из токена бота"""
        return hashlib.sha256(f"bot-api:{self.TELEGRAM_BOT_TOKEN}".encode()).hexdigest()

    def validate_for_api(self) -> None:
        """Обязательные настройки API (боту они не нужны)"""
        if len(self.SECRET_KEY) < MIN_SECRET_KEY_LENGTH:
            raise RuntimeError(
                f"SECRET_KEY должен содержать не менее {MIN_SECRET_KEY_LENGTH} символов "
                "(например: openssl rand -hex 32)"
            )
        if not self.TELEGRAM_BOT_TOKEN:
            raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")


@lru_cache
def get_settings() -> Settings:
    return Settings()
