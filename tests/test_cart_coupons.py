def _get_available_item(client):
    resp = client.get("/api/restaurants")
    for r in resp.json()["items"]:
        menu = client.get(f"/api/restaurants/{r['id']}/menu").json()
        for item in menu["items"]:
            if item["is_available"]:
                return item
    raise AssertionError("No available menu item found in mock data.")


def test_add_to_cart_and_totals(client, customer_token):
    item = _get_available_item(client)
    headers = {"Authorization": f"Bearer {customer_token}"}

    resp = client.post("/api/cart/items", json={"menu_item_id": item["id"], "quantity": 2}, headers=headers)
    assert resp.status_code == 200
    cart = resp.json()
    expected_unit_price = item.get("promotional_price") or item["price"]
    assert cart["subtotal"] == round(expected_unit_price * 2, 2)
    assert cart["final_total"] > cart["subtotal"]  # delivery fee + tax added

    get_resp = client.get("/api/cart", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["subtotal"] == cart["subtotal"]


def test_client_cannot_override_price(client, customer_token):
    """Server must recompute totals -- a client cannot smuggle a custom price."""
    item = _get_available_item(client)
    headers = {"Authorization": f"Bearer {customer_token}"}
    resp = client.post(
        "/api/cart/items",
        json={"menu_item_id": item["id"], "quantity": 1, "unit_price": 1, "total_price": 1},
        headers=headers,
    )
    assert resp.status_code == 200
    cart = resp.json()
    expected_unit_price = item.get("promotional_price") or item["price"]
    assert cart["subtotal"] == expected_unit_price


def test_invalid_coupon(client, customer_token):
    headers = {"Authorization": f"Bearer {customer_token}"}
    resp = client.post("/api/coupons/validate", json={"code": "DOES-NOT-EXIST", "subtotal": 1000}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["valid"] is False


def test_valid_coupon(client, customer_token):
    headers = {"Authorization": f"Bearer {customer_token}"}
    resp = client.post("/api/coupons/validate", json={"code": "WELCOME10", "subtotal": 1000}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    assert body["discount_amount"] > 0
