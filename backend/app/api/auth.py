import logging
import secrets
from typing import Annotated

from fastapi import APIRouter, Header, Request

from app.config import get_settings
from app.db import SessionDep
from app.errors import Forbidden, Unauthorized
from app.ratelimit import admin_limiter, client_ip, code_limiter
from app.schemas import (
    AdminLoginRequest,
    AdminTokenResponse,
    GenerateCodeRequest,
    LoginResponse,
    VerifyCodeRequest,
)
from app.security import create_access_token
from app.services import auth as service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/admin/login", response_model=AdminTokenResponse)
async def admin_login(body: AdminLoginRequest, request: Request, session: SessionDep):
    ip = client_ip(request)
    admin_limiter.check(ip)

    admin = await service.authenticate_admin(session, body.email, body.password)
    if admin is None:
        admin_limiter.add_failure(ip)
        logger.warning("Failed admin login for email=%s ip=%s", body.email, ip)
        raise Unauthorized("Invalid email or password")

    return AdminTokenResponse(access_token=create_access_token(admin.id, "admin"), user_id=admin.id)


@router.get("/telegram/bot-link")
async def bot_link():
    username = get_settings().TELEGRAM_BOT_USERNAME.lstrip("@")
    return {"bot_username": username, "bot_link": f"https://t.me/{username}" if username else None}


@router.post("/telegram/generate-code")
async def generate_code(
    body: GenerateCodeRequest,
    session: SessionDep,
    x_bot_secret: Annotated[str | None, Header()] = None,
):
    """Код для пользователя Telegram. Только для бота (X-Bot-Secret): иначе код можно было бы получить для чужого id."""
    settings = get_settings()
    if not x_bot_secret or not secrets.compare_digest(x_bot_secret, settings.bot_api_secret):
        raise Forbidden("Forbidden")
    code = await service.create_auth_code(session, body.telegram_id, body.telegram_username)
    return {"code": code, "message": f"Ваш код: {code}\n\nВставьте этот код на сайте чтобы авторизоваться"}


@router.post("/telegram/verify-code", response_model=LoginResponse)
async def verify_code(body: VerifyCodeRequest, request: Request, session: SessionDep):
    ip = client_ip(request)
    code_limiter.check(ip)

    user = await service.verify_auth_code(session, body.code)
    if user is None:
        code_limiter.add_failure(ip)
        logger.warning("Auth code verification failed, ip=%s", ip)
        raise Unauthorized("Неверный или истекший код")

    return LoginResponse(
        access_token=create_access_token(user.id, "user"),
        # id и user_id: фронтенд читает любое из двух
        user={
            "id": user.id, "user_id": user.id, "telegram_id": user.telegram_id,
            "telegram_username": user.telegram_username, "full_name": user.full_name,
        },
    )
