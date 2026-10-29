import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.db import dispose_engine, get_sessionmaker
from app.models import Admin
from app.security import hash_password

BASE_DIR = Path(__file__).resolve().parent.parent


def migrate() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "migrations"))
    command.upgrade(cfg, "head")
    print("Миграции применены")


async def ensure_admin(email: str, password: str, reset_password: bool = False) -> str:
    """Создаёт админа. Пароль существующего меняется только при reset_password=True."""
    async with get_sessionmaker()() as session:
        admin = (await session.execute(select(Admin).where(Admin.email == email))).scalar_one_or_none()
        if admin is None:
            session.add(Admin(email=email, password_hash=hash_password(password)))
            result = "created"
        elif reset_password:
            admin.password_hash = hash_password(password)
            result = "password reset"
        else:
            result = "exists"
        await session.commit()
    await dispose_engine()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate")
    admin = sub.add_parser("create-admin")
    admin.add_argument("--reset-password", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "migrate":
        migrate()
        return 0

    settings = get_settings()
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        print("ADMIN_EMAIL и ADMIN_PASSWORD должны быть заданы")
        return 1
    result = asyncio.run(ensure_admin(settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD, args.reset_password))
    print(f"Админ {settings.ADMIN_EMAIL}: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
