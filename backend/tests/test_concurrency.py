"""Гонки: ограничения БД и блокировки должны сохранять инварианты при параллельных запросах"""
import asyncio

import pytest
from sqlalchemy.exc import IntegrityError

from app.db import get_sessionmaker
from app.models import Invitation, Registration, Team


async def test_concurrent_accepts_never_exceed_team_size(client, make_user, make_hackathon, make_team, register, invite, members):
    cap, hid = await make_user(), await make_hackathon(max_team_size=3)
    tid = await make_team(cap, hid)
    users = [await make_user() for _ in range(8)]
    invs = []
    for u in users:
        await register(u, hid)
        invs.append(await invite(cap, tid, u))

    results = await asyncio.gather(*[
        client.post(f"/api/invitations/{inv}/accept", json={"accept": True}, headers=u.headers)
        for u, inv in zip(users, invs, strict=True)
    ])
    codes = [r.status_code for r in results]
    assert codes.count(200) == 2 and codes.count(400) == 6      # капитан + 2 = лимит 3
    assert len(await members(tid, cap.headers)) == 3


async def test_concurrent_approvals_never_exceed_team_size(client, make_user, make_hackathon, make_team, register, apply, members):
    cap, hid = await make_user(), await make_hackathon(max_team_size=2)
    tid = await make_team(cap, hid)
    users = [await make_user() for _ in range(5)]
    invs = []
    for u in users:
        await register(u, hid)
        invs.append(await apply(tid, u))

    results = await asyncio.gather(*[client.post(f"/api/invitations/{i}/approve", headers=cap.headers) for i in invs])
    assert sorted(r.status_code for r in results).count(200) == 1
    assert len(await members(tid, cap.headers)) == 2


async def test_user_cannot_join_two_teams_concurrently(client, make_user, make_hackathon, make_team, register, invite):
    cap1, cap2, u, hid = await make_user(), await make_user(), await make_user(), await make_hackathon()
    t1, t2 = await make_team(cap1, hid), await make_team(cap2, hid)
    await register(u, hid)
    i1, i2 = await invite(cap1, t1, u), await invite(cap2, t2, u)

    results = await asyncio.gather(*[
        client.post(f"/api/invitations/{i}/accept", json={"accept": True}, headers=u.headers) for i in (i1, i2)
    ])
    assert sorted(r.status_code for r in results) == [200, 400]
    teams = (await client.get("/api/teams/my", headers=u.headers)).json()
    assert len(teams) == 1


async def test_concurrent_registration_happens_once(client, make_user, make_hackathon):
    u, hid = await make_user(), await make_hackathon()
    results = await asyncio.gather(*[client.post(f"/api/hackathons/{hid}/register", headers=u.headers) for _ in range(6)])
    assert sorted(r.status_code for r in results) == [200] + [409] * 5


async def test_concurrent_team_creation_creates_one_team(client, make_user, make_hackathon, register):
    u, hid = await make_user(), await make_hackathon()
    await register(u, hid)
    results = await asyncio.gather(*[
        client.post("/api/teams", json={"hackathon_id": hid, "name": f"T{i}"}, headers=u.headers) for i in range(5)
    ])
    assert [r.status_code for r in results].count(200) == 1
    assert all(r.status_code in (200, 400, 409) for r in results)
    assert len((await client.get("/api/teams/my", headers=u.headers)).json()) == 1


async def test_concurrent_duplicate_invitations(client, make_user, make_hackathon, make_team, register):
    cap, u, hid = await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await register(u, hid)
    results = await asyncio.gather(*[
        client.post(f"/api/teams/{tid}/invite", params={"user_id": u.id}, headers=cap.headers) for _ in range(5)
    ])
    assert sorted(r.status_code for r in results) == [200] + [409] * 4


# ───────── ограничения БД (последняя линия защиты) ─────────

async def _insert(obj):
    async with get_sessionmaker()() as s:
        s.add(obj)
        await s.commit()


async def test_db_rejects_duplicate_registration(make_user, make_hackathon, register):
    u, hid = await make_user(), await make_hackathon()
    await register(u, hid)
    with pytest.raises(IntegrityError):
        await _insert(Registration(user_id=u.id, hackathon_id=hid))


async def test_db_rejects_second_team_for_same_captain(make_user, make_hackathon, make_team):
    cap, hid = await make_user(), await make_hackathon()
    await make_team(cap, hid)
    with pytest.raises(IntegrityError):
        await _insert(Team(hackathon_id=hid, captain_id=cap.id, name="dup"))


async def test_db_rejects_second_pending_invitation_for_same_pair(make_user, make_hackathon, make_team, register, invite):
    from app.models import InvitationKind
    cap, u, hid = await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await register(u, hid)
    await invite(cap, tid, u)
    with pytest.raises(IntegrityError):
        await _insert(Invitation(team_id=tid, user_id=u.id, sent_by_id=u.id, kind=InvitationKind.APPLICATION))


async def test_db_rejects_invalid_hackathon_values():
    from datetime import UTC, datetime
    from app.models import Hackathon
    now = datetime.now(UTC)
    with pytest.raises(IntegrityError):
        await _insert(Hackathon(name="bad-size", start_date=now, end_date=now.replace(year=now.year + 1), max_team_size=0))
    with pytest.raises(IntegrityError):
        await _insert(Hackathon(name="bad-dates", start_date=now, end_date=now))


async def test_mixed_operations_keep_invariants_and_never_fail(
    client, make_user, make_hackathon, make_team, register, invite, apply
):
    """Приглашения, заявки, одобрения и выходы одновременно: нет 500 (deadlock), инварианты целы"""
    hid = await make_hackathon(max_team_size=3)
    captains = [await make_user() for _ in range(3)]
    teams = [await make_team(c, hid) for c in captains]
    users = [await make_user() for _ in range(9)]
    for u in users:
        await register(u, hid)

    # каждому — приглашения во все три команды и заявки в две
    invites, applications = [], []
    for u in users:
        for cap, tid in zip(captains, teams, strict=True):
            invites.append((u, await invite(cap, tid, u)))
        # приглашение и заявка на одну пару (команда, пользователь) одновременно запрещены,
        # поэтому заявки подаём только в команды, где ещё нет ожидающего приглашения
    applicants = [await make_user() for _ in range(6)]
    for u in applicants:
        await register(u, hid)
        for tid in teams[:2]:
            applications.append((tid, await apply(tid, u)))

    calls = [
        client.post(f"/api/invitations/{inv}/accept", json={"accept": True}, headers=u.headers) for u, inv in invites
    ]
    for (tid, inv) in applications:
        cap = captains[teams.index(tid)]
        calls.append(client.post(f"/api/invitations/{inv}/approve", headers=cap.headers))
    results = await asyncio.gather(*calls)

    assert all(r.status_code in (200, 400) for r in results), [r.text for r in results if r.status_code >= 500]

    seen: dict[int, int] = {}
    for tid in teams:
        data = (await client.get(f"/api/teams/{tid}", headers=captains[0].headers)).json()
        assert len(data["members"]) <= 3
        for m in data["members"]:
            assert m["id"] not in seen, "пользователь состоит в двух командах"
            seen[m["id"]] = tid
