import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError as PostgrestError

from app.main import app
from tests.fakes import FakeSupabase

client = TestClient(app)
AUTH = {"X-API-Key": "test-key"}
CID = "11111111-1111-4111-8111-111111111111"
CUSTOMER = {
    "id": CID,
    "name": "Acme Ltd",
    "industry": "Food",
    "contact_name": "Jo",
    "contact_email": "jo@acme.example",
    "status": "lead",
    "notes": None,
    "created_at": "2026-10-01T10:00:00+00:00",
}
INTERACTION = {
    "id": "22222222-2222-4222-8222-222222222222",
    "customer_id": CID,
    "channel": "call",
    "content": "Wants 500 pallets.",
    "occurred_at": "2026-10-02T09:00:00+00:00",
    "memory_extracted": False,
}


@pytest.fixture
def db(monkeypatch):
    fake = FakeSupabase()
    monkeypatch.setattr("app.api.customers.supabase", fake)
    return fake


def test_customers_require_api_key():
    assert client.get("/customers").status_code == 401


def test_list_customers(db):
    db.responses["customers"] = [CUSTOMER]
    response = client.get("/customers", headers=AUTH)
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Acme Ltd"


def test_list_customers_rejects_invalid_status_filter(db):
    assert client.get("/customers?status=vip", headers=AUTH).status_code == 422


def test_create_customer_returns_201(db):
    db.responses["customers"] = [CUSTOMER]
    response = client.post("/customers", json={"name": "Acme Ltd"}, headers=AUTH)
    assert response.status_code == 201
    assert response.json()["id"] == CID


def test_create_customer_duplicate_name_returns_409(db):
    db.errors["customers"] = PostgrestError({"message": "duplicate", "code": "23505", "hint": None, "details": None})
    response = client.post("/customers", json={"name": "Acme Ltd"}, headers=AUTH)
    assert response.status_code == 409


def test_create_customer_validates_input(db):
    assert client.post("/customers", json={"name": ""}, headers=AUTH).status_code == 422
    assert client.post("/customers", json={"name": "X", "status": "vip"}, headers=AUTH).status_code == 422


def test_get_customer_not_found(db):
    db.responses["customers"] = []
    assert client.get(f"/customers/{CID}", headers=AUTH).status_code == 404


def test_get_customer_rejects_bad_uuid(db):
    assert client.get("/customers/not-a-uuid", headers=AUTH).status_code == 422


def test_update_customer_needs_at_least_one_field(db):
    db.responses["customers"] = [CUSTOMER]
    assert client.patch(f"/customers/{CID}", json={}, headers=AUTH).status_code == 400


def test_update_customer(db):
    db.responses["customers"] = [{**CUSTOMER, "status": "active"}]
    response = client.patch(f"/customers/{CID}", json={"status": "active"}, headers=AUTH)
    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_log_interaction_schedules_memory_extraction(db, monkeypatch):
    db.responses["customers"] = [CUSTOMER]
    db.responses["interactions"] = [INTERACTION]
    calls = []
    monkeypatch.setattr(
        "app.api.customers.process_interaction",
        lambda interaction_id, customer_id, name, content: calls.append((customer_id, name, content)) or 1,
    )
    response = client.post(
        f"/customers/{CID}/interactions", json={"channel": "call", "content": "Wants 500 pallets."}, headers=AUTH
    )
    assert response.status_code == 201
    assert calls == [(CID, "Acme Ltd", "Wants 500 pallets.")]


def test_failed_memory_extraction_does_not_break_the_request(db, monkeypatch):
    db.responses["customers"] = [CUSTOMER]
    db.responses["interactions"] = [INTERACTION]

    def explode(*args):
        raise RuntimeError("Gemini is down")

    monkeypatch.setattr("app.api.customers.process_interaction", explode)
    response = client.post(
        f"/customers/{CID}/interactions", json={"channel": "email", "content": "Please quote 500 pallets."}, headers=AUTH
    )
    assert response.status_code == 201


def test_log_interaction_validates_input(db):
    db.responses["customers"] = [CUSTOMER]
    bad_channel = client.post(f"/customers/{CID}/interactions", json={"channel": "fax", "content": "hello there"}, headers=AUTH)
    too_short = client.post(f"/customers/{CID}/interactions", json={"channel": "call", "content": "hi"}, headers=AUTH)
    assert bad_channel.status_code == too_short.status_code == 422


def test_log_interaction_for_unknown_customer_returns_404(db):
    db.responses["customers"] = []
    response = client.post(
        f"/customers/{CID}/interactions", json={"channel": "call", "content": "hello there"}, headers=AUTH
    )
    assert response.status_code == 404


def test_list_memories_without_query(db):
    db.responses["customers"] = [CUSTOMER]
    db.responses["memories"] = [{"id": "33333333-3333-4333-8333-333333333333", "fact": "Acme wants Net 45.", "created_at": "2026-10-03T10:00:00+00:00"}]
    response = client.get(f"/customers/{CID}/memories", headers=AUTH)
    assert response.status_code == 200
    assert response.json()[0]["fact"] == "Acme wants Net 45."


def test_search_memories_uses_recall(db, monkeypatch):
    db.responses["customers"] = [CUSTOMER]
    monkeypatch.setattr(
        "app.api.customers.recall",
        lambda customer_id, query, k: [
            {"id": "33333333-3333-4333-8333-333333333333", "fact": "Acme wants Net 45.", "similarity": 0.81, "created_at": "2026-10-03T10:00:00+00:00"}
        ],
    )
    response = client.get(f"/customers/{CID}/memories?query=payment terms", headers=AUTH)
    assert response.status_code == 200
    assert response.json()[0]["similarity"] == 0.81
