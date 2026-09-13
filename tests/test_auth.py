import uuid


def test_register_and_login(client):
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/api/auth/register", json={
        "name": "New User", "email": email, "password": "SecurePass1", "role": "customer",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["user"]["email"] == email
    assert "token" in data

    login_resp = client.post("/api/auth/login", json={"email": email, "password": "SecurePass1"})
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["role"] == "customer"


def test_login_invalid_password(client):
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={
        "name": "New User", "email": email, "password": "SecurePass1", "role": "customer",
    })
    resp = client.post("/api/auth/login", json={"email": email, "password": "WrongPassword"})
    assert resp.status_code == 401


def test_register_validation_error(client):
    resp = client.post("/api/auth/register", json={
        "name": "X", "email": "not-an-email", "password": "123", "role": "customer",
    })
    assert resp.status_code == 422


def test_me_requires_auth(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_token(client, customer_token):
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {customer_token}"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "customer"
