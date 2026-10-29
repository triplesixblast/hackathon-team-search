from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import select

from app import bot, cli
from app.db import get_sessionmaker
from app.models import Admin
from app.security import verify_password

from .conftest import ADMIN_EMAIL, ADMIN_PASSWORD


# ───────── CLI ─────────

async def get_admin():
    async with get_sessionmaker()() as s:
        return (await s.execute(select(Admin).where(Admin.email == "new@example.com"))).scalar_one_or_none()


async def test_create_admin_and_login(client):
    assert await cli.ensure_admin("new@example.com", "secret-1") == "created"
    admin = await get_admin()
    assert admin.password_hash != "secret-1" and verify_password("secret-1", admin.password_hash)
    r = await client.post("/api/auth/admin/login", json={"email": "new@example.com", "password": "secret-1"})
    assert r.status_code == 200


async def test_create_admin_does_not_overwrite_password_unless_asked():
    await cli.ensure_admin("new@example.com", "first")
    assert await cli.ensure_admin("new@example.com", "second") == "exists"
    assert verify_password("first", (await get_admin()).password_hash)
    assert await cli.ensure_admin("new@example.com", "second", reset_password=True) == "password reset"
    assert verify_password("second", (await get_admin()).password_hash)


def test_password_hashing():
    from app.security import hash_password
    h = hash_password("pw")
    assert h != hash_password("pw")                      # соль разная
    assert verify_password("pw", h) and not verify_password("other", h)
    assert not verify_password("pw", "garbage") and not verify_password("pw", "md5$1$2$3$4$5")


# ───────── бот ─────────

def update(user_id=42, username="vasya"):
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id, username=username),
        message=SimpleNamespace(reply_text=AsyncMock()),
    )


async def test_request_auth_code_sends_bot_secret(monkeypatch):
    seen = {}

    class FakeClient:
        def __init__(self, **kw): seen["timeout"] = kw.get("timeout")
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, json, headers):
            seen.update(url=url, json=json, headers=headers)
            return MagicMock(status_code=200)

    monkeypatch.setattr(bot.httpx, "AsyncClient", FakeClient)
    await bot.request_auth_code(42, "vasya")
    assert seen["url"].endswith("/api/auth/telegram/generate-code")
    assert seen["json"] == {"telegram_id": 42, "telegram_username": "vasya"}
    assert seen["headers"]["X-Bot-Secret"] == bot.get_settings().bot_api_secret
    assert seen["timeout"] == bot.REQUEST_TIMEOUT


async def test_bot_secret_is_accepted_by_the_api(client, monkeypatch):
    """Бот и API независимо выводят один и тот же секрет из токена"""
    async def via_asgi(telegram_id, username):
        return await client.post(
            "/api/auth/telegram/generate-code",
            json={"telegram_id": telegram_id, "telegram_username": username},
            headers={"X-Bot-Secret": bot.get_settings().bot_api_secret},
        )
    monkeypatch.setattr(bot, "request_auth_code", via_asgi)
    u = update(user_id=777, username="petya")
    await bot.start(u, None)
    text = u.message.reply_text.call_args.args[0]
    code = text.split("<b>")[1].split("</b>")[0]
    assert (await client.post("/api/auth/telegram/verify-code", json={"code": code})).status_code == 200


async def test_start_falls_back_to_generated_username(monkeypatch):
    seen = {}
    async def fake(tid, name):
        seen["name"] = name
        return MagicMock(status_code=200, json=lambda: {"code": "1"})
    monkeypatch.setattr(bot, "request_auth_code", fake)
    await bot.start(update(user_id=7, username=None), None)
    assert seen["name"] == "user_7"


async def test_start_reports_backend_error(monkeypatch):
    monkeypatch.setattr(bot, "request_auth_code", AsyncMock(return_value=MagicMock(status_code=500)))
    u = update()
    await bot.start(u, None)
    assert "Ошибка сервера" in u.message.reply_text.call_args.args[0]


async def test_start_reports_connection_error(monkeypatch):
    monkeypatch.setattr(bot, "request_auth_code", AsyncMock(side_effect=ConnectionError("down")))
    u = update()
    await bot.start(u, None)
    assert "Ошибка подключения" in u.message.reply_text.call_args.args[0]


async def test_help_command():
    u = update()
    await bot.help_command(u, None)
    assert "/start" in u.message.reply_text.call_args.args[0]
