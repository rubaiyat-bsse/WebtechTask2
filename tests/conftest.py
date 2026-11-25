import pytest
from fastapi.testclient import TestClient

from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({
        "APP_ENV": "test",
        "LOG_LEVEL": "INFO",
        "MAX_COPIES": 5,
        "DATABASE_PATH": str(tmp_path / "library.sqlite3"),
    })


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_book(client):
    def create(**overrides):
        payload = {"title": "Clean Architecture", "author": "Robert C. Martin", "total_copies": 2}
        payload.update(overrides)
        response = client.post("/books", json=payload)
        assert response.status_code == 201, response.text
        return response.json()
    return create


@pytest.fixture
def make_member(client):
    def create(**overrides):
        payload = {"name": "Ayesha Rahman", "email": "ayesha@example.com"}
        payload.update(overrides)
        response = client.post("/members", json=payload)
        assert response.status_code == 201, response.text
        return response.json()
    return create


@pytest.fixture
def assert_problem():
    def check(response, status):
        assert response.status_code == status, response.text
        assert response.headers["content-type"] == "application/problem+json"
        body = response.json()
        assert {"type", "title", "status", "detail", "instance", "requestId"} <= body.keys()
        assert body["status"] == status
        assert body["type"].startswith("/problems/")
        assert body["requestId"] == response.headers["X-Request-ID"]
        return body
    return check
