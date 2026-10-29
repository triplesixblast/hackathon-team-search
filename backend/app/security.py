import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt

from app.config import get_settings

Role = Literal["user", "admin"]

# Параметры scrypt (OWASP: N=2^15, r=8, p=1)
_N, _R, _P = 2**15, 8, 1
_MAXMEM = 128 * 1024 * 1024


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, maxmem=_MAXMEM)
    b64 = lambda b: base64.b64encode(b).decode()  # noqa: E731
    return f"scrypt${_N}${_R}${_P}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(
            password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
            maxmem=_MAXMEM, dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


# Хэш для выравнивания времени ответа, когда админа с таким email нет
DUMMY_HASH = hash_password("dummy-password-for-timing")


@dataclass(frozen=True)
class TokenPayload:
    subject: int
    role: Role


def create_access_token(subject: int, role: Role, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return jwt.encode(
        {"sub": str(subject), "role": role, "iat": now, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(token: str) -> TokenPayload | None:
    """Payload токена либо None, если токен просрочен, подделан или без обязательных полей"""
    settings = get_settings()
    try:
        data = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": ["exp", "sub", "role"]},
        )
        role = data["role"]
        if role not in ("user", "admin"):
            return None
        return TokenPayload(subject=int(data["sub"]), role=role)
    except (jwt.InvalidTokenError, ValueError):
        return None
