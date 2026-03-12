"""
Tests for the briefing API endpoints and service layer.
Uses an in-memory SQLite database — no running Postgres required.
conftest.py handles DB setup before this file is imported.
"""
from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import SessionLocal, get_db
from app.main import app
from tests.conftest import test_engine


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


VALID_PAYLOAD: dict[str, object] = {
    "companyName": "Acme Holdings",
    "ticker": "acme",
    "sector": "Industrial Technology",
    "analystName": "Jane Doe",
    "summary": "Acme is benefiting from strong enterprise demand.",
    "recommendation": "Monitor for margin expansion before increasing exposure.",
    "keyPoints": ["Revenue grew 18% YoY.", "Management raised full-year guidance."],
    "risks": ["Top two customers account for 41% of revenue."],
    "metrics": [
        {"name": "Revenue Growth", "value": "18%"},
        {"name": "Operating Margin", "value": "22.4%"},
    ],
}


def test_create_briefing_success(client: TestClient):
    resp = client.post("/briefings", json=VALID_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["ticker"] == "ACME"
    assert data["is_generated"] is False
    assert len(data["points"]) == 3
    assert len(data["metrics"]) == 2


def test_create_briefing_ticker_normalised(client: TestClient):
    payload: dict[str, object] = {**VALID_PAYLOAD, "ticker": "  msft  "}
    resp = client.post("/briefings", json=payload)
    assert resp.status_code == 201
    assert resp.json()["ticker"] == "MSFT"


def test_create_briefing_requires_two_key_points(client: TestClient):
    payload: dict[str, object] = {**VALID_PAYLOAD, "keyPoints": ["Only one point."]}
    resp = client.post("/briefings", json=payload)
    assert resp.status_code == 422


def test_create_briefing_requires_at_least_one_risk(client: TestClient):
    payload: dict[str, object] = {**VALID_PAYLOAD, "risks": []}
    resp = client.post("/briefings", json=payload)
    assert resp.status_code == 422


def test_create_briefing_rejects_duplicate_metric_names(client: TestClient):
    payload: dict[str, object] = {
        **VALID_PAYLOAD,
        "metrics": [
            {"name": "Revenue Growth", "value": "18%"},
            {"name": "revenue growth", "value": "20%"},
        ],
    }
    resp = client.post("/briefings", json=payload)
    assert resp.status_code == 422


def test_create_briefing_missing_required_field(client: TestClient):
    payload: dict[str, object] = {**VALID_PAYLOAD}
    del payload["companyName"]
    resp = client.post("/briefings", json=payload)
    assert resp.status_code == 422


def test_get_briefing_success(client: TestClient):
    created = client.post("/briefings", json=VALID_PAYLOAD).json()
    resp = client.get(f"/briefings/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_briefing_not_found(client: TestClient):
    resp = client.get("/briefings/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_generate_report(client: TestClient):
    created = client.post("/briefings", json=VALID_PAYLOAD).json()
    resp = client.post(f"/briefings/{created['id']}/generate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_generated"] is True
    assert data["generated_at"] is not None


def test_generate_report_not_found(client: TestClient):
    resp = client.post("/briefings/00000000-0000-0000-0000-000000000000/generate")
    assert resp.status_code == 404


def test_get_html_not_generated_yet(client: TestClient):
    created = client.post("/briefings", json=VALID_PAYLOAD).json()
    resp = client.get(f"/briefings/{created['id']}/html")
    assert resp.status_code == 409


def test_get_html_after_generate(client: TestClient):
    created = client.post("/briefings", json=VALID_PAYLOAD).json()
    client.post(f"/briefings/{created['id']}/generate")
    resp = client.get(f"/briefings/{created['id']}/html")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Acme Holdings" in resp.text
    assert "Jane Doe" in resp.text
    assert "Revenue Growth" in resp.text


def test_html_no_metrics_section_when_empty(client: TestClient):
    payload: dict[str, object] = {**VALID_PAYLOAD, "metrics": []}
    created = client.post("/briefings", json=payload).json()
    client.post(f"/briefings/{created['id']}/generate")
    resp = client.get(f"/briefings/{created['id']}/html")
    assert resp.status_code == 200
    assert "Key Metrics" not in resp.text