import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


def register_and_login(client: TestClient, email: str, role: str = "customer", name: str = "Test User"):
    resp = client.post("/api/auth/register", json={
        "name": name, "email": email, "password": "TestPass123", "role": role,
    })
    assert resp.status_code == 201, resp.text
    token = resp.json()["token"]
    return token


@pytest.fixture()
def customer_token(client):
    import uuid

    email = f"cust_{uuid.uuid4().hex[:8]}@example.com"
    return register_and_login(client, email, "customer", "Test Customer")


@pytest.fixture()
def admin_token(client):
    # Admin already seeded; log in with known seed credentials.
    resp = client.post("/api/auth/login", json={"email": "admin@foodflow.pk", "password": "Password123"})
    if resp.status_code == 200:
        return resp.json()["token"]
    # Fallback: register a fresh admin if seed data isn't present.
    import uuid

    email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    return register_and_login(client, email, "admin", "Test Admin")
