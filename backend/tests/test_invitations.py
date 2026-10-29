"""Приглашение (отвечает приглашённый) и заявка (отвечает капитан) — разные сущности"""


async def test_applicant_cannot_accept_own_application(client, make_user, make_hackathon, make_team, register, apply, members):
    cap, joiner, hid = await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await register(joiner, hid)
    inv = await apply(tid, joiner)

    r = await client.post(f"/api/invitations/{inv}/accept", json={"accept": True}, headers=joiner.headers)
    assert r.status_code == 400
    assert await members(tid, cap.headers) == {cap.id}


async def test_captain_cannot_approve_an_invitation(client, make_user, make_hackathon, make_team, register, invite):
    cap, invitee, hid = await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await register(invitee, hid)
    inv = await invite(cap, tid, invitee)
    assert (await client.post(f"/api/invitations/{inv}/approve", headers=cap.headers)).status_code == 400
    assert (await client.post(f"/api/invitations/{inv}/reject", headers=cap.headers)).status_code == 400


async def test_invites_are_not_listed_as_applications_and_vice_versa(client, make_user, make_hackathon, make_team, register, invite, apply):
    cap, invitee, joiner, hid = await make_user(), await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await register(invitee, hid)
    await register(joiner, hid)
    inv = await invite(cap, tid, invitee)
    app = await apply(tid, joiner)

    assert [a["id"] for a in (await client.get("/api/invitations/applications", headers=cap.headers)).json()] == [app]
    assert [i["id"] for i in (await client.get("/api/invitations", headers=invitee.headers)).json()] == [inv]
    assert (await client.get("/api/invitations", headers=joiner.headers)).json() == []  # своя заявка в ожидании — не уведомление
    assert (await client.get("/api/invitations/applications", headers=invitee.headers)).json() == []


async def test_applicant_sees_result_of_own_application(client, make_user, make_hackathon, make_team, register, apply):
    cap, joiner, other, hid = await make_user(), await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await register(joiner, hid)
    await register(other, hid)
    ok, no = await apply(tid, joiner), await apply(tid, other)
    await client.post(f"/api/invitations/{ok}/approve", headers=cap.headers)
    await client.post(f"/api/invitations/{no}/reject", headers=cap.headers)

    got = (await client.get("/api/invitations", headers=joiner.headers)).json()
    assert [(i["id"], i["kind"], i["status"]) for i in got] == [(ok, "application", "accepted")]
    got = (await client.get("/api/invitations", headers=other.headers)).json()
    assert [(i["id"], i["status"]) for i in got] == [(no, "declined")]


async def test_joining_a_team_cancels_other_pending(client, make_user, make_hackathon, make_team, register, apply, invite):
    cap1, cap2, u, hid = await make_user(), await make_user(), await make_user(), await make_hackathon()
    t1, t2 = await make_team(cap1, hid), await make_team(cap2, hid)
    await register(u, hid)
    app_t2 = await apply(t2, u)
    inv_t1 = await invite(cap1, t1, u)

    assert (await client.post(f"/api/invitations/{inv_t1}/accept", json={"accept": True}, headers=u.headers)).status_code == 200
    assert (await client.get("/api/invitations/applications", headers=cap2.headers)).json() == []
    assert (await client.post(f"/api/invitations/{app_t2}/approve", headers=cap2.headers)).status_code == 400


async def test_creating_a_team_cancels_own_pending_applications(client, make_user, make_hackathon, make_team, register, apply):
    cap, u, hid = await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await register(u, hid)
    inv = await apply(tid, u)
    assert (await client.post("/api/teams", json={"hackathon_id": hid, "name": "Mine"}, headers=u.headers)).status_code == 200
    assert (await client.post(f"/api/invitations/{inv}/approve", headers=cap.headers)).status_code == 400


async def test_cancel_invitation_permissions(client, make_user, make_hackathon, make_team, register, invite):
    cap, u, stranger, hid = await make_user(), await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await register(u, hid)
    inv = await invite(cap, tid, u)
    delete = lambda who, i=inv: client.delete(f"/api/invitations/{i}", headers=who.headers)  # noqa: E731

    assert (await delete(u)).status_code == 403          # приглашённый отказывается через accept=false
    assert (await delete(stranger)).status_code == 403
    assert (await delete(cap)).status_code == 200
    assert (await delete(cap)).status_code == 400        # уже обработано
    assert (await client.post(f"/api/invitations/{inv}/accept", json={"accept": True}, headers=u.headers)).status_code == 400
    assert (await delete(cap, 999999)).status_code == 404
    # после отзыва можно пригласить заново
    assert (await client.post(f"/api/teams/{tid}/invite", params={"user_id": u.id}, headers=cap.headers)).status_code == 200


async def test_applicant_can_withdraw_application(client, make_user, make_hackathon, make_team, register, apply):
    cap, u, hid = await make_user(), await make_user(), await make_hackathon()
    tid = await make_team(cap, hid)
    await register(u, hid)
    inv = await apply(tid, u)
    assert (await client.delete(f"/api/invitations/{inv}", headers=cap.headers)).status_code == 403
    assert (await client.delete(f"/api/invitations/{inv}", headers=u.headers)).status_code == 200
    assert (await client.post(f"/api/invitations/{inv}/approve", headers=cap.headers)).status_code == 400
    assert (await client.post(f"/api/teams/{tid}/apply", headers=u.headers)).status_code == 200   # можно подать заново
