def _get_available_item_and_restaurant(client):
    resp = client.get("/api/restaurants")
    for r in resp.json()["items"]:
        if not r.get("is_open"):
            continue
        menu = client.get(f"/api/restaurants/{r['id']}/menu").json()
        for item in menu["items"]:
            if item["is_available"]:
                return item, r
    raise AssertionError("No available menu item found in mock data.")


def _create_order(client, customer_token):
    item, restaurant = _get_available_item_and_restaurant(client)
    headers = {"Authorization": f"Bearer {customer_token}"}
    payload = {
        "items": [{"menu_item_id": item["id"], "quantity": 1}],
        "delivery_address": {
            "recipient_name": "Test Customer",
            "phone": "+923001234567",
            "street_address": "123 Test Street",
            "city": "Karachi",
        },
        "contact_phone": "+923001234567",
        "payment_method": "cash_on_delivery",
    }
    resp = client.post("/api/orders", json=payload, headers=headers)
    return resp


def test_create_order_success(client, customer_token):
    resp = _create_order(client, customer_token)
    assert resp.status_code == 201, resp.text
    order = resp.json()
    assert order["status"] == "pending"
    assert order["final_total"] > 0


def test_create_order_missing_address(client, customer_token):
    item, restaurant = _get_available_item_and_restaurant(client)
    headers = {"Authorization": f"Bearer {customer_token}"}
    resp = client.post(
        "/api/orders",
        json={"items": [{"menu_item_id": item["id"], "quantity": 1}]},
        headers=headers,
    )
    assert resp.status_code == 422


def test_malformed_order_payload_rejected(client, customer_token):
    headers = {"Authorization": f"Bearer {customer_token}"}
    # quantity must be > 0 -- this should fail pydantic validation (422)
    resp = client.post(
        "/api/orders",
        json={
            "items": [{"menu_item_id": "item1", "quantity": -5}],
            "delivery_address": {"recipient_name": "X", "phone": "123", "street_address": "Y", "city": "Karachi"},
        },
        headers=headers,
    )
    assert resp.status_code == 422


def test_invalid_status_transition_rejected(client, customer_token, admin_token):
    order_resp = _create_order(client, customer_token)
    assert order_resp.status_code == 201
    order_id = order_resp.json()["id"]

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    # pending -> delivered directly is not a valid transition
    resp = client.patch(f"/api/orders/{order_id}/status", json={"status": "delivered"}, headers=admin_headers)
    assert resp.status_code == 400

    # valid transition should succeed
    ok = client.patch(f"/api/orders/{order_id}/status", json={"status": "accepted"}, headers=admin_headers)
    assert ok.status_code == 200
    assert ok.json()["status"] == "accepted"
