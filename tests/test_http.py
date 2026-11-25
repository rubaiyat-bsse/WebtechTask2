import logging

import pytest

from app.dependencies import get_book_service

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("body", ["{oops", "[]", "null", '"hello"', "{}"])
def test_invalid_json_or_body_shape(client, body, assert_problem):
    response = client.post("/books", content=body, headers={"Content-Type": "application/json"})
    assert_problem(response, 422)


@pytest.mark.parametrize("path", ["/books/abc", "/books/0", "/members/-1"])
def test_invalid_path_parameter(client, path, assert_problem):
    body = assert_problem(client.get(path), 422)
    assert body["errors"]


def test_unknown_route_and_wrong_method(client, assert_problem):
    assert_problem(client.get("/no-such-route"), 404)
    response = client.patch("/books")
    assert_problem(response, 405)
    assert "Allow" in response.headers


def test_put_requires_full_replacement_and_rejects_server_fields(client, make_book, assert_problem):
    book = make_book()
    url = f"/books/{book['id']}"
    assert_problem(client.put(url, json={"title": "Only title"}), 422)
    payload = {"title": "Book", "author": "Author", "total_copies": 1, "available_copies": 99}
    assert_problem(client.put(url, json=payload), 422)
    assert client.get(url).json() == book


def test_request_id_in_success_error_and_service_logs(client, caplog):
    with caplog.at_level(logging.INFO, logger="app"):
        response = client.post("/books", json={"title": "Book", "author": "Author", "total_copies": 1},
                               headers={"X-Request-ID": "lab-demo-42"})
    assert response.headers["X-Request-ID"] == "lab-demo-42"
    assert any("book added" in record.message and record.request_id == "lab-demo-42" for record in caplog.records)
    assert any("POST /books -> 201" in record.message for record in caplog.records)
    failed = client.get("/books/999", headers={"X-Request-ID": "lab-demo-43"})
    assert failed.json()["requestId"] == failed.headers["X-Request-ID"] == "lab-demo-43"


def test_invalid_request_id_is_replaced_and_generated_ids_are_distinct(client):
    first = client.get("/health", headers={"X-Request-ID": "x" * 100})
    second = client.get("/health")
    assert len(first.headers["X-Request-ID"]) == 12
    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]


def test_unexpected_exception_is_logged_but_hidden(app, client, caplog, assert_problem):
    class BrokenService:
        def list_books(self):
            raise RuntimeError("private storage failure")

    app.dependency_overrides[get_book_service] = lambda: BrokenService()
    with caplog.at_level(logging.ERROR, logger="app"):
        response = client.get("/books", headers={"X-Request-ID": "failure-demo"})
    body = assert_problem(response, 500)
    assert body["detail"] == "Something went wrong"
    assert "private storage failure" not in response.text
    errors = [record for record in caplog.records if record.exc_info]
    assert len(errors) == 1
    assert errors[0].request_id == "failure-demo"
    assert str(errors[0].exc_info[1]) == "private storage failure"


def test_docs_and_openapi_are_available(client):
    assert client.get("/docs").status_code == 200
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert {"/books", "/members", "/books/{book_id}/borrow"} <= spec["paths"].keys()
    assert "application/problem+json" in spec["paths"]["/books"]["post"]["responses"]["422"]["content"]
