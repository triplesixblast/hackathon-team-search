"""
Тесты идут на настоящем PostgreSQL: без TEST_DATABASE_URL поднимается одноразовый контейнер
(нужен Docker). Схема создаётся теми же миграциями Alembic, что и в проде.
"""
import atexit
import os
import secrets
import subprocess
import time
from types import SimpleNamespace


def _start_postgres() -> str:
    """Одноразовый postgres в Docker; возвращает DATABASE_URL"""
    container = subprocess.run(
        ["docker", "run", "-d", "--rm", "-p", "127.0.0.1::5432",
         "-e", "POSTGRES_PASSWORD=test", "-e", "POSTGRES_DB=itam_test", "postgres:16-alpine"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    atexit.register(lambda: subprocess.run(["docker", "stop", container], capture_output=True))

    # Образ стартует дважды (init-сервер, затем боевой): ждём второго «ready»
    for _ in range(60):
        logs = subprocess.run(["docker", "logs", container], capture_output=True, text=True)
        if (logs.stdout + logs.stderr).count("ready to accept connections") >= 2:
            break
        time.sleep(0.5)
    port = subprocess.run(
        ["docker", "port", container, "5432/tcp"], check=True, capture_output=True, text=True
    ).stdout.split(":")[-1].strip()
    return f"postgresql://postgres:test@127.0.0.1:{port}/itam_test"


# Окружение должно быть задано до импорта приложения
os.environ.update(
    SECRET_KEY="test-secret-key-" + "x" * 32,
    TELEGRAM_BOT_TOKEN="123456:TEST",
    TELEGRAM_BOT_USERNAME="itam_test_bot",
    ENABLE_DOCS="true",
    TRUSTED_PROXY_HOPS="1",
    DATABASE_URL=os.environ.get("TEST_DATABASE_URL") or _start_postgres(),
)

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import ratelimit  # noqa: E402
from app.cli import migrate  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import dispose_engine, get_engine, get_sessionmaker  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Admin, User  # noqa: E402
from app.security import create_access_token, hash_password  # noqa: E402

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin-pass"
_ADMIN_HASH = hash_password(ADMIN_PASSWORD)  # хэшируем один раз: scrypt намеренно медленный

TABLES = "users, admins, auth_codes, hackathons, teams, registrations, invitations"


@pytest.fixture(scope="session", autouse=True)
def _schema():
    migrate()  # синхронная фикстура: asyncio.run внутри env.py не конфликтует с loop тестов


@pytest_asyncio.fixture(autouse=True)
async def _clean_db():
    async with get_engine().begin() as conn:
        await conn.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    ratelimit.code_limiter.reset()
    ratelimit.admin_limiter.reset()
    yield


@pytest_asyncio.fixture(scope="session", autouse=True, loop_scope="session")
async def _dispose():
    yield
    await dispose_engine()


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def bot_headers():
    return {"X-Bot-Secret": get_settings().bot_api_secret}


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers():
    async with get_sessionmaker()() as session:
        admin = Admin(email=ADMIN_EMAIL, password_hash=_ADMIN_HASH)
        session.add(admin)
        await session.commit()
        return bearer(create_access_token(admin.id, "admin"))


@pytest.fixture
def make_user():
    """Пользователь (запись в БД + токен). Полный вход по коду проверяется в test_auth."""
    async def factory(**fields):
        async with get_sessionmaker()() as session:
            tg_id = 5_000_000_000 + secrets.randbelow(10**9)  # > int32, как настоящие Telegram ID
            user = User(
                telegram_id=tg_id, telegram_username=f"user{tg_id}",
                full_name=fields.pop("full_name", f"User {tg_id}"), **fields,
            )
            session.add(user)
            await session.commit()
            return SimpleNamespace(
                id=user.id, telegram_id=tg_id, headers=bearer(create_access_token(user.id, "user"))
            )
    return factory


@pytest.fixture
def make_hackathon(client, admin_headers):
    async def factory(max_team_size=5, **fields):
        r = await client.post(
            "/api/hackathons",
            json={
                "name": f"Hack {secrets.token_hex(4)}",
                "start_date": "2030-01-01T10:00:00Z",
                "end_date": "2030-01-03T10:00:00Z",
                "max_team_size": max_team_size,
                **fields,
            },
            headers=admin_headers,
        )
        assert r.status_code == 200, r.text
        return r.json()["id"]
    return factory


@pytest.fixture
def register(client):
    async def do(user, hackathon_id):
        r = await client.post(f"/api/hackathons/{hackathon_id}/register", headers=user.headers)
        assert r.status_code == 200, r.text
    return do


@pytest.fixture
def make_team(client, register):
    """Регистрирует капитана на хакатон и создаёт команду. Возвращает id команды."""
    async def factory(captain, hackathon_id, name="Team"):
        await register(captain, hackathon_id)
        r = await client.post(
            "/api/teams", json={"hackathon_id": hackathon_id, "name": name}, headers=captain.headers
        )
        assert r.status_code == 200, r.text
        return r.json()["id"]
    return factory


@pytest.fixture
def apply(client):
    async def do(team_id, user):
        r = await client.post(f"/api/teams/{team_id}/apply", headers=user.headers)
        assert r.status_code == 200, r.text
        return r.json()["invitation_id"]
    return do


@pytest.fixture
def invite(client):
    async def do(captain, team_id, user):
        r = await client.post(
            f"/api/teams/{team_id}/invite", params={"user_id": user.id}, headers=captain.headers
        )
        assert r.status_code == 200, r.text
        return r.json()["invitation_id"]
    return do


@pytest.fixture
def join(client, register, apply):
    """Пользователь регистрируется, подаёт заявку и капитан её одобряет"""
    async def do(captain, user, team_id, hackathon_id):
        await register(user, hackathon_id)
        inv = await apply(team_id, user)
        r = await client.post(f"/api/invitations/{inv}/approve", headers=captain.headers)
        assert r.status_code == 200, r.text
    return do


@pytest_asyncio.fixture
async def members(client):
    async def get(team_id, headers):
        r = await client.get(f"/api/teams/{team_id}", headers=headers)
        assert r.status_code == 200, r.text
        return {m["id"] for m in r.json()["members"]}
    return get
