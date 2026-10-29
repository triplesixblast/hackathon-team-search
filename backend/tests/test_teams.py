async def test_create_team_makes_captain_the_only_member(client, make_user, make_hackathon, register):
    cap, hid = await make_user(full_name="Cap"), await make_hackathon(max_team_size=4)
    await register(cap, hid)
    r = await client.post("/api/teams", json={"hackathon_id": hid, "name": "Alpha", "description": "d"}, headers=cap.headers)
    assert r.status_code == 200
    team = r.json()
    assert (team["captain_id"], team["status"], team["max_team_size"]) == (cap.id, "open", 4)
    assert [m["id"] for m in team["members"]] == [cap.id]
    assert team["captain"]["id"] == cap.id and "telegram_id" not in team["captain"]
    assert (await client.get(f"/api/hackathons/{hid}", headers=cap.headers)).json()["team_id"] == team["id"]


async def test_create_team_rules(client, make_user, make_hackathon, register, make_team):
    u, hid = await make_user(), await make_hackathon()
    create = lambda **kw: client.post("/api/teams", json={"hackathon_id": hid, "name": "T", **kw}, headers=u.headers)  # noqa: E731

    assert (await create()).status_code == 400                                     # не зарегистрирован
    assert (await client.post("/api/teams", json={"hackathon_id": 999999, "name": "T"}, headers=u.headers)).status_code == 404
    await register(u, hid)
    assert (await create(name="")).status_code == 422
    assert (await create(name="x" * 201)).status_code == 422
    assert (await create()).status_code == 200
    assert (await create()).status_code == 400                                     # вторая команда


async def test_can_create_reasons(client, make_user, make_hackathon, register):
    u, hid = await make_user(), await make_hackathon()
    url = f"/api/teams/can-create/{hid}"
    assert (await client.get(url, headers=u.headers)).json()["can_create"] is False
    assert (await client.get("/api/teams/can-create/999999", headers=u.headers)).json()["reason"] == "Hackathon not found"
    await register(u, hid)
    assert (await client.get(url, headers=u.headers)).json() == {"can_create": True, "reason": None}
    await client.post("/api/teams", json={"hackathon_id": hid, "name": "T"}, headers=u.headers)
    assert (await client.get(url, headers=u.headers)).json()["can_create"] is False


async def test_my_teams_and_listing(client, make_user, make_hackathon, make_team):
    cap, other, hid = await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid, name="Mine")

    mine = (await client.get("/api/teams/my", headers=cap.headers)).json()
    assert [(t["id"], t["name"], t["hackathon_id"]) for t in mine] == [(tid, "Mine", hid)]
    assert mine[0]["hackathon_name"].startswith("Hack ")
    assert (await client.get("/api/teams/my", headers=other.headers)).json() == []

    listed = (await client.get(f"/api/teams/hackathons/{hid}", headers=other.headers)).json()
    assert [(t["id"], t["max_team_size"], len(t["members"])) for t in listed] == [(tid, 5, 1)]
    assert (await client.get(f"/api/teams/hackathons/{hid}?status_filter=closed", headers=other.headers)).json() == []
    assert (await client.get(f"/api/teams/hackathons/{hid}?status_filter=bogus", headers=other.headers)).status_code == 422


async def test_team_detail(client, make_user, make_hackathon, make_team):
    cap, hid = await make_user(), await make_hackathon(max_team_size=4)
    tid = await make_team(cap, hid)
    d = (await client.get(f"/api/teams/{tid}", headers=cap.headers)).json()
    assert d["max_team_size"] == 4 and d["hackathon"]["id"] == hid
    assert (await client.get("/api/teams/999999", headers=cap.headers)).status_code == 404


# ───────── заявки ─────────

async def test_application_flow(client, make_user, make_hackathon, make_team, register, apply, members):
    cap, joiner, hid = await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await register(joiner, hid)
    inv = await apply(tid, joiner)

    apps = (await client.get("/api/invitations/applications", headers=cap.headers)).json()
    assert [(a["id"], a["kind"], a["user"]["id"]) for a in apps] == [(inv, "application", joiner.id)]
    assert "telegram_id" not in apps[0]["user"]

    assert (await client.post(f"/api/invitations/{inv}/approve", headers=joiner.headers)).status_code == 403
    assert (await client.post(f"/api/invitations/{inv}/approve", headers=cap.headers)).status_code == 200
    assert await members(tid, cap.headers) == {cap.id, joiner.id}
    assert (await client.get(f"/api/hackathons/{hid}", headers=joiner.headers)).json()["team_id"] == tid
    # повторная обработка запрещена
    assert (await client.post(f"/api/invitations/{inv}/approve", headers=cap.headers)).status_code == 400
    assert (await client.post(f"/api/invitations/{inv}/reject", headers=cap.headers)).status_code == 400


async def test_apply_validations(client, make_user, make_hackathon, make_team, register, apply):
    cap, other, hid = await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)

    assert (await client.post(f"/api/teams/{tid}/apply", headers=cap.headers)).status_code == 400    # капитан
    assert (await client.post(f"/api/teams/{tid}/apply", headers=other.headers)).status_code == 400  # не зарегистрирован
    assert (await client.post("/api/teams/999999/apply", headers=other.headers)).status_code == 404
    await register(other, hid)
    await apply(tid, other)
    assert (await client.post(f"/api/teams/{tid}/apply", headers=other.headers)).status_code == 409  # дубль


async def test_apply_to_full_or_closed_team(client, make_user, make_hackathon, make_team, register):
    cap, other, hid = await make_user(), await make_user(), await make_hackathon(max_team_size=1)
    tid = await make_team(cap, hid)
    await register(other, hid)
    r = await client.post(f"/api/teams/{tid}/apply", headers=other.headers)
    assert r.status_code == 400 and "full" in r.json()["detail"].lower()

    hid2 = await make_hackathon()
    cap2, other2 = await make_user(), await make_user()
    tid2 = await make_team(cap2, hid2)
    await register(other2, hid2)
    await client.patch(f"/api/teams/{tid2}", json={"status": "closed"}, headers=cap2.headers)
    assert (await client.post(f"/api/teams/{tid2}/apply", headers=other2.headers)).status_code == 400


async def test_cannot_apply_when_already_in_another_team(client, make_user, make_hackathon, make_team):
    cap1, cap2, hid = await make_user(), await make_user(), await make_hackathon()
    await make_team(cap1, hid)
    t2 = await make_team(cap2, hid)
    assert (await client.post(f"/api/teams/{t2}/apply", headers=cap1.headers)).status_code == 400


async def test_approve_respects_team_size_limit(client, make_user, make_hackathon, make_team, register, apply, members):
    cap, a, b, hid = await make_user(), await make_user(), await make_user(), await make_hackathon(max_team_size=2)
    tid = await make_team(cap, hid)
    await register(a, hid)
    await register(b, hid)
    inv_a, inv_b = await apply(tid, a), await apply(tid, b)
    assert (await client.post(f"/api/invitations/{inv_a}/approve", headers=cap.headers)).status_code == 200
    r = await client.post(f"/api/invitations/{inv_b}/approve", headers=cap.headers)
    assert r.status_code == 400 and "full" in r.json()["detail"].lower()
    assert await members(tid, cap.headers) == {cap.id, a.id}


async def test_reject_application(client, make_user, make_hackathon, make_team, register, apply, members):
    cap, joiner, hid = await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await register(joiner, hid)
    inv = await apply(tid, joiner)
    assert (await client.post(f"/api/invitations/{inv}/reject", headers=joiner.headers)).status_code == 403
    assert (await client.post(f"/api/invitations/{inv}/reject", headers=cap.headers)).status_code == 200
    assert await members(tid, cap.headers) == {cap.id}
    assert (await client.post("/api/invitations/999999/reject", headers=cap.headers)).status_code == 404


# ───────── приглашения ─────────

async def test_invite_accept_flow(client, make_user, make_hackathon, make_team, register, invite, members):
    cap, invitee, hid = await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await register(invitee, hid)
    inv = await invite(cap, tid, invitee)

    mine = (await client.get("/api/invitations", headers=invitee.headers)).json()
    assert [(i["id"], i["kind"], i["status"], i["sent_by_id"]) for i in mine] == [(inv, "invite", "pending", cap.id)]
    assert mine[0]["team"]["members"][0]["id"] == cap.id

    pending = (await client.get(f"/api/invitations/team/{tid}/pending", headers=cap.headers)).json()
    assert [i["id"] for i in pending] == [inv] and pending[0]["user"]["id"] == invitee.id
    assert (await client.get(f"/api/invitations/team/{tid}/pending", headers=invitee.headers)).status_code == 403

    accept = lambda who, flag=True: client.post(f"/api/invitations/{inv}/accept", json={"accept": flag}, headers=who.headers)  # noqa: E731
    assert (await accept(cap)).status_code == 403          # чужое приглашение
    assert (await accept(invitee)).status_code == 200
    assert await members(tid, cap.headers) == {cap.id, invitee.id}
    assert (await accept(invitee)).status_code == 400      # уже обработано
    assert (await client.get("/api/invitations", headers=invitee.headers)).json() == []


async def test_accept_without_body_means_accept(client, make_user, make_hackathon, make_team, register, invite, members):
    cap, invitee, hid = await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await register(invitee, hid)
    inv = await invite(cap, tid, invitee)
    assert (await client.post(f"/api/invitations/{inv}/accept", headers=invitee.headers)).status_code == 200
    assert invitee.id in await members(tid, cap.headers)


async def test_decline_invitation(client, make_user, make_hackathon, make_team, register, invite, members):
    cap, invitee, hid = await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await register(invitee, hid)
    inv = await invite(cap, tid, invitee)
    assert (await client.post(f"/api/invitations/{inv}/accept", json={"accept": False}, headers=invitee.headers)).status_code == 200
    assert await members(tid, cap.headers) == {cap.id}
    assert (await client.get("/api/invitations", headers=invitee.headers)).json() == []


async def test_invite_validations(client, make_user, make_hackathon, make_team, register, invite):
    cap, other, stranger, hid = await make_user(), await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await register(other, hid)
    post = lambda who, team=tid, uid=None: client.post(f"/api/teams/{team}/invite", params={"user_id": uid or other.id}, headers=who.headers)  # noqa: E731

    assert (await post(other)).status_code == 403                    # не капитан
    assert (await post(cap, uid=999999)).status_code == 404
    assert (await post(cap, team=999999)).status_code == 404
    assert (await post(cap, uid=stranger.id)).status_code == 400     # не зарегистрирован на хакатон
    await invite(cap, tid, other)
    assert (await post(cap)).status_code == 409                      # дубль


async def test_invite_user_already_in_team(client, make_user, make_hackathon, make_team):
    cap1, cap2, hid = await make_user(), await make_user(), await make_hackathon()
    t1 = await make_team(cap1, hid)
    await make_team(cap2, hid)
    r = await client.post(f"/api/teams/{t1}/invite", params={"user_id": cap2.id}, headers=cap1.headers)
    assert r.status_code == 400


async def test_invite_to_full_or_closed_team(client, make_user, make_hackathon, make_team, register):
    cap, other, hid = await make_user(), await make_user(), await make_hackathon(max_team_size=1)
    tid = await make_team(cap, hid)
    await register(other, hid)
    assert (await client.post(f"/api/teams/{tid}/invite", params={"user_id": other.id}, headers=cap.headers)).status_code == 400

    hid2 = await make_hackathon()
    cap2, other2 = await make_user(), await make_user()
    tid2 = await make_team(cap2, hid2)
    await register(other2, hid2)
    await client.patch(f"/api/teams/{tid2}", json={"status": "closed"}, headers=cap2.headers)
    assert (await client.post(f"/api/teams/{tid2}/invite", params={"user_id": other2.id}, headers=cap2.headers)).status_code == 400


async def test_accepting_invite_respects_team_size_limit(client, make_user, make_hackathon, make_team, register, invite, members):
    cap, a, b, hid = await make_user(), await make_user(), await make_user(), await make_hackathon(max_team_size=2)
    tid = await make_team(cap, hid)
    await register(a, hid)
    await register(b, hid)
    inv_a, inv_b = await invite(cap, tid, a), await invite(cap, tid, b)
    accept = lambda inv, who: client.post(f"/api/invitations/{inv}/accept", json={"accept": True}, headers=who.headers)  # noqa: E731
    assert (await accept(inv_a, a)).status_code == 200
    assert (await accept(inv_b, b)).status_code == 400
    assert len(await members(tid, cap.headers)) == 2


# ───────── выход, исключение, передача, удаление, статус ─────────

async def test_leave_team(client, make_user, make_hackathon, make_team, join, members):
    cap, m, hid = await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await join(cap, m, tid, hid)

    assert (await client.post(f"/api/teams/{tid}/leave", headers=cap.headers)).status_code == 400   # капитан
    assert (await client.post(f"/api/teams/{tid}/leave", headers=m.headers)).status_code == 200
    assert await members(tid, cap.headers) == {cap.id}
    assert (await client.get(f"/api/hackathons/{hid}", headers=m.headers)).json()["team_id"] is None
    assert (await client.post(f"/api/teams/{tid}/leave", headers=m.headers)).status_code == 404
    assert (await client.post("/api/teams/999999/leave", headers=m.headers)).status_code == 404
    # после выхода можно создать свою команду
    assert (await client.post("/api/teams", json={"hackathon_id": hid, "name": "Own"}, headers=m.headers)).status_code == 200


async def test_remove_member_permissions(client, make_user, make_hackathon, make_team, join, members):
    cap, m1, m2, hid = await make_user(), await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await join(cap, m1, tid, hid)
    await join(cap, m2, tid, hid)
    delete = lambda who, uid, team=tid: client.delete(f"/api/teams/{team}/members/{uid}", headers=who.headers)  # noqa: E731

    assert (await delete(m1, m2.id)).status_code == 403             # участник не исключает других
    assert (await delete(cap, m2.id)).status_code == 200
    assert await members(tid, cap.headers) == {cap.id, m1.id}
    assert (await client.get(f"/api/hackathons/{hid}", headers=m2.headers)).json()["team_id"] is None
    assert (await delete(cap, m2.id)).status_code == 404            # уже нет в команде
    assert (await delete(cap, m1.id, team=999999)).status_code == 404
    assert (await delete(m1, m1.id)).status_code == 200             # сам себя — можно


async def test_captain_cannot_be_removed(client, make_user, make_hackathon, make_team, members):
    cap, hid = await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    assert (await client.delete(f"/api/teams/{tid}/members/{cap.id}", headers=cap.headers)).status_code == 400
    assert await members(tid, cap.headers) == {cap.id}


async def test_transfer_captaincy(client, make_user, make_hackathon, make_team, join):
    cap, m, outsider, hid = await make_user(), await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await join(cap, m, tid, hid)
    url = f"/api/teams/{tid}/transfer-captain"

    assert (await client.post(url, params={"user_id": m.id}, headers=m.headers)).status_code == 403
    assert (await client.post(url, params={"user_id": cap.id}, headers=cap.headers)).status_code == 400
    assert (await client.post(url, params={"user_id": outsider.id}, headers=cap.headers)).status_code == 400
    assert (await client.post(url, params={"user_id": m.id}, headers=cap.headers)).status_code == 200

    assert (await client.get(f"/api/teams/{tid}", headers=m.headers)).json()["captain_id"] == m.id
    assert (await client.post(f"/api/teams/{tid}/leave", headers=cap.headers)).status_code == 200   # бывший капитан может выйти


async def test_delete_team_frees_members(client, make_user, make_hackathon, make_team, join):
    cap, m, hid = await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await join(cap, m, tid, hid)

    assert (await client.delete(f"/api/teams/{tid}", headers=m.headers)).status_code == 403
    assert (await client.delete(f"/api/teams/{tid}", headers=cap.headers)).status_code == 200
    assert (await client.get(f"/api/teams/{tid}", headers=cap.headers)).status_code == 404
    for u in (cap, m):
        d = (await client.get(f"/api/hackathons/{hid}", headers=u.headers)).json()
        assert d["is_registered"] is True and d["team_id"] is None
    assert (await client.post("/api/teams", json={"hackathon_id": hid, "name": "New"}, headers=m.headers)).status_code == 200
    assert (await client.delete("/api/teams/999999", headers=cap.headers)).status_code == 404


async def test_update_team_and_close(client, make_user, make_hackathon, make_team, register):
    cap, a, hid = await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await register(a, hid)
    patch = lambda who, **kw: client.patch(f"/api/teams/{tid}", json=kw, headers=who.headers)  # noqa: E731

    assert (await patch(a, status="closed")).status_code == 403
    assert (await patch(cap, status="bogus")).status_code == 422
    r = await patch(cap, status="closed", name="Renamed")
    assert r.status_code == 200 and (r.json()["status"], r.json()["name"]) == ("closed", "Renamed")
    assert (await client.get(f"/api/teams/hackathons/{hid}", headers=a.headers)).json() == []   # закрытые не в списке по умолчанию

    assert (await patch(cap, status="open")).status_code == 200
    assert (await client.post(f"/api/teams/{tid}/apply", headers=a.headers)).status_code == 200
