import csv
import io

from .conftest import ADMIN_EMAIL


def rows(response):
    text = response.content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


async def test_admin_endpoints_require_admin(client, make_user, make_hackathon):
    u, hid = await make_user(), await make_hackathon()
    for path in (f"/api/admin/{hid}/analytics", f"/api/admin/{hid}/participants/export", f"/api/admin/{hid}/teams/export"):
        assert (await client.get(path)).status_code == 401
        assert (await client.get(path, headers=u.headers)).status_code == 403
    r = await client.post(f"/api/admin/hackathons/{hid}/assign-user", json={"user_id": u.id}, headers=u.headers)
    assert r.status_code == 403


async def test_unknown_hackathon_is_404(client, admin_headers):
    for path in ("analytics", "participants/export", "teams/export"):
        assert (await client.get(f"/api/admin/999999/{path}", headers=admin_headers)).status_code == 404


async def test_analytics(client, admin_headers, make_user, make_hackathon, make_team, register, join):
    hid = await make_hackathon()
    cap = await make_user(skills=["Python", "sql"], experience_level="senior")
    joiner = await make_user(skills=["python"])
    solo = await make_user(skills=["PYTHON", "go"])
    tid = await make_team(cap, hid)
    await join(cap, joiner, tid, hid)
    await register(solo, hid)

    a = (await client.get(f"/api/admin/{hid}/analytics", headers=admin_headers)).json()
    assert a["total_participants"] == 3 and a["total_teams"] == 1
    assert a["participants_in_team"] == 2 and a["participants_without_team"] == 1
    assert a["average_team_size"] == 2.0                                   # участники в командах / команды
    assert a["skills_frequency"] == {"python": 3, "go": 1, "sql": 1}       # без учёта регистра
    assert a["experience_distribution"] == {"senior": 1, "junior": 2}


async def test_analytics_of_empty_hackathon(client, admin_headers, make_hackathon):
    hid = await make_hackathon()
    a = (await client.get(f"/api/admin/{hid}/analytics", headers=admin_headers)).json()
    assert a["total_participants"] == 0 and a["average_team_size"] == 0 and a["skills_frequency"] == {}


async def test_participants_export(client, admin_headers, make_user, make_hackathon, make_team, register):
    hid = await make_hackathon()
    cap, solo = await make_user(full_name="Капитан", skills=["python", "sql"]), await make_user()
    await make_team(cap, hid, name="Alpha")
    await register(solo, hid)

    r = await client.get(f"/api/admin/{hid}/participants/export", headers=admin_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert f"participants_{hid}.csv" in r.headers["content-disposition"]
    data = rows(r)
    assert data[0] == ["ID", "Full Name", "Telegram Username", "Skills", "Role Preference", "Experience Level", "Team Name", "Team Status"]
    by_id = {int(row[0]): row for row in data[1:]}
    assert by_id[cap.id][1] == "Капитан" and by_id[cap.id][3] == "python, sql"   # кириллица читается (BOM)
    assert by_id[cap.id][-2:] == ["Alpha", "open"]
    assert by_id[solo.id][-2:] == ["", ""]


async def test_exports_escape_formulas(client, admin_headers, make_user, make_hackathon, make_team):
    hid = await make_hackathon()
    cap = await make_user(full_name='=HYPERLINK("http://evil","x")')
    await make_team(cap, hid, name="@SUM(A1)")

    users = rows(await client.get(f"/api/admin/{hid}/participants/export", headers=admin_headers))
    assert users[1][1].startswith("'=") and users[1][6] == "'@SUM(A1)"
    teams = rows(await client.get(f"/api/admin/{hid}/teams/export", headers=admin_headers))
    assert teams[1][1] == "'@SUM(A1)" and teams[1][3].startswith("'=") and teams[1][5].startswith("'=")


async def test_teams_export(client, admin_headers, make_user, make_hackathon, make_team, join):
    hid = await make_hackathon()
    cap, joiner = await make_user(full_name="Cap"), await make_user(full_name="Joiner")
    tid = await make_team(cap, hid, name="Alpha")
    await join(cap, joiner, tid, hid)

    data = rows(await client.get(f"/api/admin/{hid}/teams/export", headers=admin_headers))
    assert data[0] == ["Team ID", "Team Name", "Team Status", "Captain Name", "Member Count", "Members"]
    assert data[1][:5] == [str(tid), "Alpha", "open", "Cap", "2"]
    assert set(data[1][5].split(", ")) == {"Cap", "Joiner"}


async def test_assign_and_unassign(client, admin_headers, make_user, make_hackathon, make_team, members):
    cap, u, hid = await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    url = f"/api/admin/hackathons/{hid}/assign-user"
    post = lambda **kw: client.post(url, json=kw, headers=admin_headers)  # noqa: E731

    assert (await post(user_id=u.id, team_id=tid)).status_code == 200        # без регистрации — создаётся
    assert (await client.get(f"/api/hackathons/{hid}", headers=u.headers)).json()["team_id"] == tid
    assert await members(tid, cap.headers) == {cap.id, u.id}

    assert (await post(user_id=u.id, team_id=tid)).status_code == 400        # уже в команде
    assert (await post(user_id=999999, team_id=tid)).status_code == 404
    assert (await post(user_id=u.id, team_id=999999)).status_code == 400

    assert (await post(user_id=u.id, team_id=None)).status_code == 200
    assert (await client.get(f"/api/hackathons/{hid}", headers=u.headers)).json()["team_id"] is None
    assert await members(tid, cap.headers) == {cap.id}


async def test_assign_ignores_team_limit_but_not_membership_rules(client, admin_headers, make_user, make_hackathon, make_team, register, members):
    cap, a, b, hid = await make_user(), await make_user(), await make_user(), await make_hackathon(max_team_size=1)
    t1 = await make_team(cap, hid)
    cap2 = await make_user()
    t2 = await make_team(cap2, hid)
    url = f"/api/admin/hackathons/{hid}/assign-user"
    # админ может превысить лимит (ручное распределение)
    assert (await client.post(url, json={"user_id": a.id, "team_id": t1}, headers=admin_headers)).status_code == 200
    assert len(await members(t1, cap.headers)) == 2
    # но не может держать человека в двух командах
    assert (await client.post(url, json={"user_id": a.id, "team_id": t2}, headers=admin_headers)).status_code == 400


async def test_captain_cannot_be_unassigned(client, admin_headers, make_user, make_hackathon, make_team):
    cap, hid = await make_user(), await make_hackathon()
    await make_team(cap, hid)
    r = await client.post(f"/api/admin/hackathons/{hid}/assign-user", json={"user_id": cap.id, "team_id": None}, headers=admin_headers)
    assert r.status_code == 400


async def test_unassign_requires_registration(client, admin_headers, make_user, make_hackathon):
    u, hid = await make_user(), await make_hackathon()
    r = await client.post(f"/api/admin/hackathons/{hid}/assign-user", json={"user_id": u.id, "team_id": None}, headers=admin_headers)
    assert r.status_code == 400


async def test_assign_cancels_pending_application(client, admin_headers, make_user, make_hackathon, make_team, register, apply):
    cap1, cap2, u, hid = await make_user(), await make_user(), await make_user(), await make_hackathon()
    t1, t2 = await make_team(cap1, hid), await make_team(cap2, hid)
    await register(u, hid)
    inv = await apply(t2, u)
    await client.post(f"/api/admin/hackathons/{hid}/assign-user", json={"user_id": u.id, "team_id": t1}, headers=admin_headers)
    assert (await client.post(f"/api/invitations/{inv}/approve", headers=cap2.headers)).status_code == 400


async def test_list_all_hackathons_newest_first(client, admin_headers, make_hackathon):
    h1, h2 = await make_hackathon(), await make_hackathon()
    assert [h["id"] for h in (await client.get("/api/admin/hackathons", headers=admin_headers)).json()] == [h2, h1]
