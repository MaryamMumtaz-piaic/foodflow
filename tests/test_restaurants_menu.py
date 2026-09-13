def test_list_restaurants(client):
    resp = client.get("/api/restaurants")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 8
    assert len(data["items"]) > 0


def test_get_restaurant_detail(client):
    resp = client.get("/api/restaurants")
    first_id = resp.json()["items"][0]["id"]
    detail = client.get(f"/api/restaurants/{first_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == first_id


def test_get_restaurant_not_found(client):
    resp = client.get("/api/restaurants/does-not-exist")
    assert resp.status_code == 404


def test_get_menu(client):
    resp = client.get("/api/restaurants")
    first_id = resp.json()["items"][0]["id"]
    menu = client.get(f"/api/restaurants/{first_id}/menu")
    assert menu.status_code == 200
    body = menu.json()
    assert "items" in body and "categories" in body
    assert len(body["items"]) > 0


def test_role_protected_route_requires_role(client, customer_token):
    # Customers cannot create restaurants
    resp = client.post(
        "/api/restaurants",
        json={"name": "Unauthorized Restaurant", "address": "Somewhere"},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert resp.status_code == 403
