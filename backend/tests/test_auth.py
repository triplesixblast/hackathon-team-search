import asyncio
import datetime as dt

import jwt
import pytest
from sqlalchemy import update
from starlette.requests import Request

from app.config import get_settings
from app.db import get_sessionmaker
from app.models import AuthCode
from app.ratelimit import client_ip
from app.security import create_access_token, decode_access_token

from .conftest import ADMIN_EMAIL, ADMIN_PASSWORD, bearer

VERIFY = "/api/auth/telegram/verify-code"
GENERATE = "/api/auth/telegram/generate-code"


async def gen_code(client, headers, telegram_id=5_000_000_111, username="tester"):
    r = await client.post(GENERATE, json={"telegram_id": telegram_id, "telegram_username": username}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["code"]


async def test_generate_code_requires_bot_secret(client, bot_headers):
    body = {"telegram_id": 111}
    assert (await client.post(GENERATE, json=body)).status_code == 403
    assert (await client.post(GENERATE, json=body, headers={"X-Bot-Secret": "nope"})).status_code == 403
    assert (await client.post(GENERATE, json=body, headers=bot_headers)).status_code == 200


async def test_code_login_flow(client, bot_headers):
    code = await gen_code(client, bot_headers, telegram_id=5_000_000_111, username="vasya")
    assert len(code) == 6 and code.isdigit()

    r = await client.post(VERIFY, json={"code": code})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["id"] == body["user"]["user_id"]  # фронтенд читает любое из двух
    assert body["user"]["telegram_username"] == "vasya"

    me = await client.get("/api/users/me", headers=bearer(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["telegram_id"] == 5_000_000_111  # > int32


async def test_code_is_single_use(client, bot_headers):
    code = await gen_code(client, bot_headers)
    assert (await client.post(VERIFY, json={"code": code})).status_code == 200
    assert (await client.post(VERIFY, json={"code": code})).status_code == 401


async def test_new_code_invalidates_previous(client, bot_headers):
    old = await gen_code(client, bot_headers, 5_000_000_222)
    new = await gen_code(client, bot_headers, 5_000_000_222)
    assert (await client.post(VERIFY, json={"code": old})).status_code == 401
    assert (await client.post(VERIFY, json={"code": new})).status_code == 200


async def test_expired_code_is_rejected(client, bot_headers):
    code = await gen_code(client, bot_headers)
    async with get_sessionmaker()() as s:
        await s.execute(update(AuthCode).values(expires_at=dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)))
        await s.commit()
    assert (await client.post(VERIFY, json={"code": code})).status_code == 401


async def test_repeat_login_keeps_user_and_refreshes_username(client, bot_headers):
    first = (await client.post(VERIFY, json={"code": await gen_code(client, bot_headers, 5_000_000_333, "old")})).json()
    second = (await client.post(VERIFY, json={"code": await gen_code(client, bot_headers, 5_000_000_333, "new")})).json()
    assert first["user"]["id"] == second["user"]["id"]
    me = await client.get("/api/users/me", headers=bearer(second["access_token"]))
    assert me.json()["telegram_username"] == "new"


async def test_concurrent_verify_succeeds_only_once(client, bot_headers):
    code = await gen_code(client, bot_headers)
    results = await asyncio.gather(*[client.post(VERIFY, json={"code": code}) for _ in range(6)])
    assert sorted(r.status_code for r in results).count(200) == 1


async def test_verify_code_is_rate_limited(client):
    for _ in range(10):
        assert (await client.post(VERIFY, json={"code": "000000"})).status_code == 401
    assert (await client.post(VERIFY, json={"code": "000000"})).status_code == 429


async def test_bot_link(client):
    r = await client.get("/api/auth/telegram/bot-link")
    assert r.json() == {"bot_username": "itam_test_bot", "bot_link": "https://t.me/itam_test_bot"}


# ───────── админ ─────────

async def test_admin_login(client, admin_headers):
    ok = await client.post("/api/auth/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert ok.status_code == 200 and ok.json()["token_type"] == "bearer"
    bad = await client.post("/api/auth/admin/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
    assert bad.status_code == 401
    unknown = await client.post("/api/auth/admin/login", json={"email": "no@example.com", "password": "x"})
    assert unknown.status_code == 401 and unknown.json() == bad.json()


async def test_admin_login_is_rate_limited(client, admin_headers):
    for _ in range(10):
        await client.post("/api/auth/admin/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
    r = await client.post("/api/auth/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 429


# ───────── токены и доступ ─────────

async def test_endpoints_require_auth(client):
    for path in ("/api/users/me", "/api/hackathons", "/api/teams/my", "/api/invitations", "/api/admin/hackathons"):
        assert (await client.get(path)).status_code == 401, path
        assert (await client.get(path, headers=bearer("garbage"))).status_code == 401, path


async def test_participant_token_cannot_use_admin_endpoints(client, make_user):
    u = await make_user()
    body = {"name": "X", "start_date": "2030-01-01T00:00:00Z", "end_date": "2030-01-02T00:00:00Z"}
    assert (await client.post("/api/hackathons", json=body, headers=u.headers)).status_code == 403
    assert (await client.get("/api/admin/hackathons", headers=u.headers)).status_code == 403


async def test_admin_token_is_not_a_participant(client, admin_headers):
    assert (await client.get("/api/users/me", headers=admin_headers)).status_code == 401


async def test_token_for_deleted_user_is_rejected(client):
    assert (await client.get("/api/users/me", headers=bearer(create_access_token(999999, "user")))).status_code == 401


def test_token_validation():
    s = get_settings()
    now = dt.datetime.now(dt.UTC)
    forged = [
        jwt.encode({"sub": "1", "role": "user"}, s.SECRET_KEY, algorithm="HS256"),                      # без exp
        jwt.encode({"role": "user", "exp": now + dt.timedelta(hours=1)}, s.SECRET_KEY, algorithm="HS256"),  # без sub
        jwt.encode({"sub": "1", "exp": now + dt.timedelta(hours=1)}, s.SECRET_KEY, algorithm="HS256"),     # без role
        jwt.encode({"sub": "1", "role": "root", "exp": now + dt.timedelta(hours=1)}, s.SECRET_KEY, algorithm="HS256"),
        jwt.encode({"sub": "1", "role": "user", "exp": now + dt.timedelta(hours=1)}, "other-key-" + "y" * 32, algorithm="HS256"),
        create_access_token(1, "user", dt.timedelta(seconds=-5)),                                      # просрочен
        "not-a-token",
    ]
    for token in forged:
        assert decode_access_token(token) is None
    payload = decode_access_token(create_access_token(7, "admin"))
    assert (payload.subject, payload.role) == (7, "admin")


# ───────── IP клиента за прокси ─────────

def make_request(xff=None, host="9.9.9.9"):
    headers = [(b"x-forwarded-for", xff.encode())] if xff else []
    return Request({"type": "http", "headers": headers, "client": (host, 1234)})


@pytest.mark.parametrize(
    ("hops", "xff", "expected"),
    [
        (1, "6.6.6.6, 1.2.3.4", "1.2.3.4"),     # левое подделано клиентом — берём дописанное прокси
        (1, "1.2.3.4", "1.2.3.4"),
        (1, None, "9.9.9.9"),
        (2, "6.6.6.6, 1.2.3.4, 10.0.0.1", "1.2.3.4"),
        (2, "6.6.6.6", "9.9.9.9"),              # короче цепочки: запрос мимо прокси
        (0, "6.6.6.6", "9.9.9.9"),              # прямое подключение: заголовок игнорируется
    ],
)
def test_client_ip(monkeypatch, hops, xff, expected):
    monkeypatch.setattr(get_settings(), "TRUSTED_PROXY_HOPS", hops)
    assert client_ip(make_request(xff)) == expected


async def test_rate_limit_cannot_be_bypassed_with_spoofed_header(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "TRUSTED_PROXY_HOPS", 0)
    for i in range(10):
        await client.post(VERIFY, json={"code": "000000"}, headers={"X-Forwarded-For": f"10.0.0.{i}"})
    r = await client.post(VERIFY, json={"code": "000000"}, headers={"X-Forwarded-For": "10.9.9.9"})
    assert r.status_code == 429


# ───────── прочее ─────────

async def test_internal_error_hides_details():
    import httpx
    from app.main import app

    @app.get("/_boom")
    async def boom():
        raise RuntimeError("secret internals")

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/_boom")
    assert r.status_code == 500 and "secret" not in r.text


async def test_debug_endpoints_do_not_exist(client):
    assert (await client.get("/api/debug/db-info")).status_code == 404
    assert (await client.get("/api/auth/admin/debug")).status_code == 404
