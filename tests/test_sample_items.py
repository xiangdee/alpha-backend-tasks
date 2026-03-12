from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db, SessionLocal
from app.main import app


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_create_and_list_sample_items(client: TestClient) -> None:
    create_response = client.post(
        "/sample-items",
        json={"name": "Starter Item", "description": "Used for starter validation"},
    )

    assert create_response.status_code == 201
    created_payload = create_response.json()
    assert created_payload["name"] == "Starter Item"

    list_response = client.get("/sample-items")
    assert list_response.status_code == 200

    items = list_response.json()
    assert len(items) >= 1
    assert any(i["id"] == created_payload["id"] for i in items)