async def test_update_profile_normalizes_skills(client, make_user):
    u = await make_user()
    r = await client.put(
        "/api/users/me",
        json={"full_name": "Иван", "skills": [" python ", "Python", "sql", "   ", "SQL"], "role_preference": "backend"},
        headers=u.headers,
    )
    assert r.status_code == 200
    me = (await client.get("/api/users/me", headers=u.headers)).json()
    assert me["full_name"] == "Иван" and me["role_preference"] == "backend"
    assert me["skills"] == ["python", "sql"]  # без дублей, первое написание сохраняется


async def test_partial_update_keeps_other_fields(client, make_user):
    u = await make_user()
    await client.put("/api/users/me", json={"bio": "hi", "skills": ["go"]}, headers=u.headers)
    await client.put("/api/users/me", json={"experience_level": "senior"}, headers=u.headers)
    me = (await client.get("/api/users/me", headers=u.headers)).json()
    assert (me["bio"], me["skills"], me["experience_level"]) == ("hi", ["go"], "senior")


async def test_profile_input_limits(client, make_user):
    u = await make_user()
    put = lambda **kw: client.put("/api/users/me", json=kw, headers=u.headers)  # noqa: E731
    assert (await put(bio="x" * 5001)).status_code == 422
    assert (await put(full_name="")).status_code == 422
    assert (await put(full_name="x" * 201)).status_code == 422
    assert (await put(skills=["a"] * 31)).status_code == 422
    assert (await put(skills=["x" * 51])).status_code == 422
    assert (await put(avatar_url="javascript:alert(1)")).status_code == 422
    assert (await put(avatar_url="https://example.com/a.png")).status_code == 200


async def test_telegram_id_only_in_own_profile(client, make_user):
    a, b = await make_user(), await make_user()
    assert (await client.get("/api/users/me", headers=a.headers)).json()["telegram_id"] == a.telegram_id
    other = (await client.get(f"/api/users/{a.id}", headers=b.headers)).json()
    assert other["id"] == a.id and "telegram_id" not in other
    assert (await client.get("/api/users/999999", headers=b.headers)).status_code == 404


# ───────── участники хакатона ─────────

async def ids(client, viewer, hid, **params):
    r = await client.get(f"/api/users/hackathons/{hid}/participants", params=params, headers=viewer.headers)
    assert r.status_code == 200, r.text
    return [u["id"] for u in r.json()]


async def test_participants_visible_only_to_registered(client, make_user, make_hackathon, register):
    a, b, outsider, hid = await make_user(), await make_user(), await make_user(), await make_hackathon()
    await register(a, hid)
    await register(b, hid)
    r = await client.get(f"/api/users/hackathons/{hid}/participants", headers=outsider.headers)
    assert r.status_code == 403
    assert await ids(client, a, hid) == [b.id]  # без себя


async def test_participants_response_has_no_private_fields(client, make_user, make_hackathon, register):
    a, b, hid = await make_user(), await make_user(), await make_hackathon()
    await register(a, hid)
    await register(b, hid)
    item = (await client.get(f"/api/users/hackathons/{hid}/participants", headers=a.headers)).json()[0]
    assert set(item) == {"id", "full_name", "skills", "role_preference", "experience_level", "avatar_url"}


async def test_skill_filter_is_case_insensitive_and_supports_cyrillic(client, make_user, make_hackathon, register):
    a, hid = await make_user(), await make_hackathon()
    b = await make_user(skills=["Питон", "FastAPI"])
    c = await make_user(skills=["go"])
    for u in (a, b, c):
        await register(u, hid)
    assert await ids(client, a, hid, skill="питон") == [b.id]
    assert await ids(client, a, hid, skill="ПИТОН") == [b.id]
    assert await ids(client, a, hid, skill="fastapi") == [b.id]
    assert await ids(client, a, hid, skill="java") == []


async def test_filters_treat_like_wildcards_literally(client, make_user, make_hackathon, register):
    a, hid = await make_user(), await make_hackathon()
    b = await make_user(full_name="Boris", skills=["python"])
    await register(a, hid)
    await register(b, hid)
    assert await ids(client, a, hid, skill="%") == []
    assert await ids(client, a, hid, search="%") == []
    assert await ids(client, a, hid, search="_") == []
    assert await ids(client, a, hid, search="bOR") == [b.id]


async def test_role_and_experience_filters_and_pagination(client, make_user, make_hackathon, register):
    a, hid = await make_user(), await make_hackathon()
    await register(a, hid)
    others = [await make_user(role_preference="backend" if i % 2 else "frontend", experience_level="senior" if i < 2 else "junior") for i in range(4)]
    for u in others:
        await register(u, hid)
    assert await ids(client, a, hid, role_preference="backend") == [others[1].id, others[3].id]
    assert await ids(client, a, hid, experience_level="senior") == [others[0].id, others[1].id]
    assert await ids(client, a, hid, limit=2) == [others[0].id, others[1].id]
    assert await ids(client, a, hid, limit=2, skip=2) == [others[2].id, others[3].id]


async def test_list_limits(client, make_user, make_hackathon, register):
    u, hid = await make_user(), await make_hackathon()
    await register(u, hid)
    url = f"/api/users/hackathons/{hid}/participants"
    assert (await client.get(url, params={"limit": 10**6}, headers=u.headers)).status_code == 422
    assert (await client.get(url, params={"limit": 0}, headers=u.headers)).status_code == 422
    assert (await client.get(url, params={"skip": -1}, headers=u.headers)).status_code == 422
    assert (await client.get("/api/hackathons", params={"limit": 101}, headers=u.headers)).status_code == 422
