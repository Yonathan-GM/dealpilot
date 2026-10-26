from fastapi.testclient import TestClient
from google.genai import errors as genai_errors

from app.core.config import settings
from app.main import app
from app.services.rag import RagAnswer

client = TestClient(app)
AUTH = {"X-API-Key": "test-key"}
SOURCE = {
    "id": "6f1d3c1e-0000-4000-8000-000000000001",
    "filename": "catalog.md",
    "chunk_index": 0,
    "content": "Plastic pallet minimum order: 20 units.",
    "score": 0.03,
}


def test_health_is_public():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["auth"] == "enabled"


def test_ask_requires_api_key():
    response = client.post("/ask", json={"question": "hello there"})
    assert response.status_code == 401


def test_ask_rejects_wrong_api_key():
    response = client.post("/ask", json={"question": "hello there"}, headers={"X-API-Key": "nope"})
    assert response.status_code == 401


def test_ask_returns_answer_and_sources(monkeypatch):
    monkeypatch.setattr(
        "app.api.ask.answer_question",
        lambda question, k, mode: RagAnswer(answer="20 units [1]", sources=[SOURCE]),
    )
    response = client.post("/ask", json={"question": "Minimum order for pallets?"}, headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "20 units [1]"
    assert body["sources"][0]["filename"] == "catalog.md"


def test_ask_validates_input():
    too_short = client.post("/ask", json={"question": "hi"}, headers=AUTH)
    bad_k = client.post("/ask", json={"question": "valid question", "k": 99}, headers=AUTH)
    bad_mode = client.post("/ask", json={"question": "valid question", "mode": "magic"}, headers=AUTH)
    assert too_short.status_code == bad_k.status_code == bad_mode.status_code == 422


def test_gemini_errors_become_502(monkeypatch):
    def boom(question, k, mode):
        raise genai_errors.APIError(429, {"error": {"message": "quota"}})

    monkeypatch.setattr("app.api.ask.answer_question", boom)
    response = client.post("/ask", json={"question": "valid question"}, headers=AUTH)
    assert response.status_code == 502


def test_upload_rejects_unsupported_file_type():
    response = client.post(
        "/documents", headers=AUTH, files={"file": ("virus.exe", b"abc", "application/octet-stream")}
    )
    assert response.status_code == 415


def test_upload_rejects_empty_document():
    response = client.post("/documents", headers=AUTH, files={"file": ("empty.txt", b"   ", "text/plain")})
    assert response.status_code == 422


def test_upload_rejects_oversized_file(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 0)
    response = client.post("/documents", headers=AUTH, files={"file": ("a.txt", b"x", "text/plain")})
    assert response.status_code == 413


def test_upload_success(monkeypatch):
    monkeypatch.setattr("app.api.documents.ingest_text", lambda filename, text, doc_type: 3)
    response = client.post(
        "/documents",
        headers=AUTH,
        files={"file": ("notes.txt", b"# Notes\n\nSome real text.", "text/plain")},
        data={"doc_type": "faq"},
    )
    assert response.status_code == 200
    assert response.json() == {"filename": "notes.txt", "doc_type": "faq", "chunks": 3}


def test_upload_strips_folder_from_filename(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        "app.api.documents.ingest_text",
        lambda filename, text, doc_type: seen.setdefault("name", filename) and 1,
    )
    client.post("/documents", headers=AUTH, files={"file": ("../../etc/notes.txt", b"hello world", "text/plain")})
    assert seen["name"] == "notes.txt"
