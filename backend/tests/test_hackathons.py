import uuid

from .conftest import bearer  # noqa: F401


def body(**kw):
    return {
        "name": f"H {uuid.uuid4().hex}", "start_date": "2030-01-01T10:00:00Z",
        "end_date": "2030-01-02T10:00:00Z", **kw,
    }


async def test_list_and_detail(client, make_user, make_hackathon):
    u = await make_user()
    h1, h2 = await make_hackathon(), await make_hackathon()
    listed = (await client.get("/api/hackathons", headers=u.headers)).json()
    assert [h["id"] for h in listed] == [h1, h2]
    detail = (await client.get(f"/api/hackathons/{h1}", headers=u.headers)).json()
    assert detail["status"] == "upcoming" and detail["is_registered"] is False and detail["team_id"] is None
    assert (await client.get("/api/hackathons/999999", headers=u.headers)).status_code == 404


async def test_register(client, make_user, make_hackathon):
    u, hid = await make_user(), await make_hackathon()
    assert (await client.post(f"/api/hackathons/{hid}/register", headers=u.headers)).status_code == 200
    assert (await client.post(f"/api/hackathons/{hid}/register", headers=u.headers)).status_code == 409
    assert (await client.get(f"/api/hackathons/{hid}", headers=u.headers)).json()["is_registered"] is True
    assert (await client.post("/api/hackathons/999999/register", headers=u.headers)).status_code == 404


async def test_dates_are_utc_with_z_suffix(client, admin_headers):
    r = await client.post("/api/hackathons", json=body(start_date="2030-01-01T10:00:00+03:00", end_date="2030-01-02T10:00:00"), headers=admin_headers)
    assert r.status_code == 200
    h = r.json()
    assert h["start_date"] == "2030-01-01T07:00:00Z"   # +03:00 приведено к UTC
    assert h["end_date"] == "2030-01-02T10:00:00Z"     # без пояса — UTC
    assert h["created_at"].endswith("Z")


async def test_create_validation(client, admin_headers):
    async def create(**kw):
        return (await client.post("/api/hackathons", json=body(**kw), headers=admin_headers)).status_code

    assert await create(max_team_size=0) == 422
    assert await create(max_team_size=101) == 422
    assert await create(name="") == 422
    assert await create(name="x" * 201) == 422
    assert await create(end_date="2029-12-31T10:00:00Z") == 422
    assert await create(end_date="2030-01-01T10:00:00Z") == 422
    assert await create() == 200


async def test_duplicate_name(client, admin_headers):
    b = body()
    assert (await client.post("/api/hackathons", json=b, headers=admin_headers)).status_code == 200
    assert (await client.post("/api/hackathons", json=b, headers=admin_headers)).status_code == 409


async def test_update_rules(client, admin_headers, make_hackathon):
    h1, h2 = await make_hackathon(), await make_hackathon()
    name1 = next(h["name"] for h in (await client.get("/api/admin/hackathons", headers=admin_headers)).json() if h["id"] == h1)
    put = lambda hid, **kw: client.put(f"/api/hackathons/{hid}", json=kw, headers=admin_headers)  # noqa: E731

    assert (await put(h2, name=name1)).status_code == 409                       # имя занято
    assert (await put(h1, name=name1)).status_code == 200                       # своё же имя
    assert (await put(h1, status="bogus")).status_code == 422
    assert (await put(h1, max_team_size=0)).status_code == 422
    assert (await put(h1, end_date="2000-01-01T00:00:00Z")).status_code == 400  # конец раньше начала
    r = await put(h1, status="active", max_team_size=3)
    assert r.status_code == 200 and (r.json()["status"], r.json()["max_team_size"]) == ("active", 3)
    assert (await put(999999, status="active")).status_code == 404


async def test_cannot_shrink_max_team_size_below_existing_team(client, admin_headers, make_user, make_hackathon, make_team, join):
    cap, joiner, hid = await make_user(), await make_user(), await make_hackathon(max_team_size=3)
    tid = await make_team(cap, hid)
    await join(cap, joiner, tid, hid)
    put = lambda size: client.put(f"/api/hackathons/{hid}", json={"max_team_size": size}, headers=admin_headers)  # noqa: E731
    assert (await put(1)).status_code == 400
    assert (await put(2)).status_code == 200


async def test_finished_hackathon_is_frozen(client, admin_headers, make_user, make_hackathon, make_team, register, apply):
    cap, other, late, hid = await make_user(), await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await register(other, hid)
    pending = await apply(tid, other)

    await client.put(f"/api/hackathons/{hid}", json={"status": "finished"}, headers=admin_headers)

    assert (await client.post(f"/api/hackathons/{hid}/register", headers=late.headers)).status_code == 400
    assert (await client.post(f"/api/invitations/{pending}/approve", headers=cap.headers)).status_code == 400
    assert (await client.post(f"/api/teams/{tid}/invite", params={"user_id": other.id}, headers=cap.headers)).status_code == 400
    assert (await client.get(f"/api/teams/can-create/{hid}", headers=late.headers)).json()["can_create"] is False


async def test_finished_hackathon_blocks_new_teams(client, admin_headers, make_user, make_hackathon, register):
    u, hid = await make_user(), await make_hackathon()
    await register(u, hid)
    await client.put(f"/api/hackathons/{hid}", json={"status": "finished"}, headers=admin_headers)
    r = await client.post("/api/teams", json={"hackathon_id": hid, "name": "T"}, headers=u.headers)
    assert r.status_code == 400
