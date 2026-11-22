def test_health(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").status_code == 200


def test_create_get_list_delete(client):
    r = client.post("/items", json={"name": "vol-a", "description": "first"})
    assert r.status_code == 201
    item = r.json()
    assert client.get(f"/items/{item['id']}").json()["name"] == "vol-a"
    page = client.get("/items", params={"limit": 10}).json()
    assert page["total"] == 1 and page["items"][0]["id"] == item["id"]
    assert client.delete(f"/items/{item['id']}").status_code == 204
    assert client.get(f"/items/{item['id']}").status_code == 404


def test_validation_and_conflict(client):
    assert client.post("/items", json={"name": ""}).status_code == 422
    assert client.get("/items", params={"limit": 501}).status_code == 422
    assert client.post("/items", json={"name": "dup"}).status_code == 201
    assert client.post("/items", json={"name": "dup"}).status_code == 409
