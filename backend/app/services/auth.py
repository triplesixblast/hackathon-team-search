import secrets
import string
from datetime import timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Admin, AuthCode, User, utcnow
from app.security import DUMMY_HASH, verify_password

CODE_LENGTH = 6


def _generate_code() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(CODE_LENGTH))


async def create_auth_code(session: AsyncSession, telegram_id: int, username: str | None) -> str:
    """Выдать код. Предыдущие неиспользованные коды этого пользователя гасятся."""
    now = utcnow()
    expires_at = now + timedelta(minutes=get_settings().CODE_EXPIRY_MINUTES)

    await session.execute(delete(AuthCode).where(AuthCode.expires_at < now))
    await session.execute(
        update(AuthCode)
        .where(AuthCode.telegram_id == telegram_id, AuthCode.used.is_(False))
        .values(used=True)
    )

    # Среди активных кодов значение уникально (частичный индекс) — при коллизии пробуем снова
    for _ in range(10):
        code = _generate_code()
        try:
            async with session.begin_nested():
                session.add(AuthCode(
                    code=code,
                    telegram_id=telegram_id,
                    telegram_username=username or f"user_{telegram_id}",
                    expires_at=expires_at,
                ))
        except IntegrityError:
            continue
        await session.commit()
        return code
    raise RuntimeError("Не удалось сгенерировать уникальный код авторизации")


async def verify_auth_code(session: AsyncSession, code: str) -> User | None:
    """Погасить код и вернуть пользователя (создаётся при первом входе). None — код не подошёл."""
    auth_code = (await session.execute(
        select(AuthCode)
        .where(AuthCode.code == code, AuthCode.used.is_(False), AuthCode.expires_at > utcnow())
        .with_for_update()  # код одноразовый и при параллельных запросах
    )).scalar_one_or_none()
    if auth_code is None:
        return None

    auth_code.used = True

    user = (await session.execute(
        select(User).where(User.telegram_id == auth_code.telegram_id)
    )).scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=auth_code.telegram_id,
            telegram_username=auth_code.telegram_username,
            full_name=auth_code.telegram_username or f"User_{auth_code.telegram_id}",
        )
        session.add(user)
    elif auth_code.telegram_username and user.telegram_username != auth_code.telegram_username:
        user.telegram_username = auth_code.telegram_username  # пользователь сменил username в Telegram

    await session.commit()
    return user


async def authenticate_admin(session: AsyncSession, email: str, password: str) -> Admin | None:
    admin = (await session.execute(select(Admin).where(Admin.email == email))).scalar_one_or_none()
    if admin is None:
        verify_password(password, DUMMY_HASH)  # время ответа не выдаёт, существует ли email
        return None
    return admin if verify_password(password, admin.password_hash) else None
