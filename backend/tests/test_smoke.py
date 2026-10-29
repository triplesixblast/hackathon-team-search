async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


async def test_admin_flow_smoke(client, admin_headers, make_hackathon):
    hid = await make_hackathon()
    r = await client.get("/api/admin/hackathons", headers=admin_headers)
    assert [h["id"] for h in r.json()] == [hid]
