"""AI routes must gracefully fall back to deterministic logic (and still
return a structurally valid response) whenever OpenAI is unavailable.
We force this by disabling settings.ai_enabled for the duration of each
test, regardless of whether a real key happens to be configured in the
environment (e.g. a developer's local .env)."""
import pytest


@pytest.fixture(autouse=True)
def force_fallback_mode(monkeypatch):
    # call_json_agent is the single choke point every agent uses to reach
    # OpenAI; forcing it to return None deterministically exercises each
    # agent's rule-based fallback path regardless of ambient env config.
    monkeypatch.setattr("app.agents.base.call_json_agent", lambda *a, **k: None)
    monkeypatch.setattr("app.agents.preference_agent.call_json_agent", lambda *a, **k: None)
    monkeypatch.setattr("app.agents.menu_agent.call_json_agent", lambda *a, **k: None)
    monkeypatch.setattr("app.agents.support_agent.call_json_agent", lambda *a, **k: None)
    monkeypatch.setattr("app.agents.insights_agent.call_json_agent", lambda *a, **k: None)
    yield


def test_food_search_fallback(client):
    resp = client.post("/api/ai/food-search", json={"query": "vegetarian dinner for two under Rs. 2000"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["criteria"]["source"] == "fallback"
    assert body["criteria"]["dietary_preference"] == "vegetarian"
    assert body["criteria"]["servings"] == 2
    assert body["criteria"]["budget"] == 2000
    assert isinstance(body["recommendations"], list)


def test_recommendations_only_include_available_items(client):
    resp = client.post("/api/ai/recommendations", json={"query": "spicy chicken"})
    assert resp.status_code == 200
    recs = resp.json()["recommendations"]
    for r in recs:
        assert "menu_item_id" in r and "restaurant_name" in r


def test_menu_analysis_fallback(client):
    resp = client.post("/api/ai/menu-analysis", json={"name": "Chicken Karahi", "ingredients": ["chicken", "tomato", "milk", "flour"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "fallback"
    assert "dairy" in body["detected_allergens"]
    assert "gluten" in body["detected_allergens"]
    assert "disclaimer" in body


def test_delivery_estimate_fallback(client):
    resp = client.get("/api/restaurants")
    rid = resp.json()["items"][0]["id"]
    est = client.post("/api/ai/delivery-estimate", json={"restaurant_id": rid})
    assert est.status_code == 200
    body = est.json()
    assert body["estimated_delivery_minutes_max"] >= body["estimated_delivery_minutes_min"]


def test_customer_support_never_claims_fake_refund(client):
    resp = client.post("/api/ai/customer-support", json={"message": "Please refund my order right now"})
    assert resp.status_code == 200
    body = resp.json()
    answer = body["answer"].lower()
    assert "refund has been processed" not in answer
    assert "your refund is complete" not in answer


def test_ai_invalid_payload_rejected(client):
    resp = client.post("/api/ai/food-search", json={})
    assert resp.status_code == 422
