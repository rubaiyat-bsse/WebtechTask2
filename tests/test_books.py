import pytest

pytestmark = pytest.mark.integration


def test_books_full_crud_lifecycle(client, assert_problem):
    assert client.get("/books").json() == []
    payload = {"title": "Algorithms", "author": "CLRS", "total_copies": 2}
    created = client.post("/books", json=payload)
    assert created.status_code == 201
    location = created.headers["Location"]
    book = created.json()
    assert location == f"/books/{book['id']}"
    assert book == {**payload, "id": book["id"], "available_copies": 2}

    fetched = client.get(location)
    assert fetched.status_code == 200
    assert fetched.json() == book
    listed = client.get("/books")
    assert listed.status_code == 200
    assert listed.json() == [book]

    replacement = {"title": "Introduction to Algorithms", "author": "Cormen et al.", "total_copies": 3}
    updated = client.put(location, json=replacement)
    assert updated.status_code == 200
    assert updated.json() == {**replacement, "id": book["id"], "available_copies": 3}
    assert client.get(location).json() == updated.json()

    deleted = client.delete(location)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert_problem(client.get(location), 404)
    assert client.get("/books").json() == []
    assert_problem(client.delete(location), 404)


def test_borrow_return_lifecycle_and_conflicts(client, make_book, assert_problem):
    book = make_book(total_copies=1)
    url = f"/books/{book['id']}"
    assert_problem(client.post(f"{url}/return"), 409)

    borrowed = client.post(f"{url}/borrow")
    assert borrowed.status_code == 200
    assert borrowed.json()["available_copies"] == 0
    conflict = assert_problem(client.post(f"{url}/borrow"), 409)
    assert conflict["detail"] == "No copies of this book are available"
    assert client.get(url).json()["available_copies"] == 0

    returned = client.post(f"{url}/return")
    assert returned.status_code == 200
    assert returned.json()["available_copies"] == 1
    assert client.get(url).json()["available_copies"] == 1
    assert_problem(client.post(f"{url}/return"), 409)


def test_update_preserves_outstanding_borrows(client, make_book, assert_problem):
    book = make_book(total_copies=2)
    url = f"/books/{book['id']}"
    client.post(f"{url}/borrow")
    payload = {"title": "New title", "author": "New author", "total_copies": 4}
    updated = client.put(url, json=payload)
    assert updated.status_code == 200
    assert updated.json()["available_copies"] == 3

    invalid = {**payload, "title": "Should not be saved", "total_copies": 0}
    assert_problem(client.put(url, json=invalid), 409)
    assert client.get(url).json() == updated.json()


def test_cannot_delete_borrowed_book(client, make_book, assert_problem):
    book = make_book(total_copies=1)
    url = f"/books/{book['id']}"
    client.post(f"{url}/borrow")
    assert_problem(client.delete(url), 409)
    assert client.get(url).status_code == 200
    client.post(f"{url}/return")
    assert client.delete(url).status_code == 204


@pytest.mark.parametrize("field,value", [
    ("title", ""), ("title", "  "), ("title", "x" * 201),
    ("author", ""), ("author", "x" * 121),
    ("total_copies", -1), ("total_copies", 6),
    ("total_copies", "2"), ("total_copies", True), ("total_copies", 1.5),
])
def test_book_field_validation(client, field, value, assert_problem):
    payload = {"title": "Algorithms", "author": "CLRS", "total_copies": 1, field: value}
    body = assert_problem(client.post("/books", json=payload), 422)
    assert f"/{field}" in {error["pointer"] for error in body["errors"]}
    assert client.get("/books").json() == []


def test_book_update_validation_does_not_change_record(client, make_book, assert_problem):
    book = make_book()
    url = f"/books/{book['id']}"
    assert_problem(client.put(url, json={"title": "Invalid", "author": "Author", "total_copies": 99}), 422)
    assert client.get(url).json() == book


@pytest.mark.parametrize("method,suffix", [
    ("get", ""), ("put", ""), ("delete", ""), ("post", "/borrow"), ("post", "/return"),
])
def test_missing_book_operations(client, method, suffix, assert_problem):
    kwargs = {}
    if method == "put":
        kwargs["json"] = {"title": "Book", "author": "Author", "total_copies": 1}
    assert_problem(client.request(method, f"/books/999{suffix}", **kwargs), 404)


def test_zero_stock_and_sql_special_characters(client, make_book, assert_problem):
    title = "Reader's guide'); DROP TABLE books; --"
    book = make_book(title=title, total_copies=0)
    assert client.get(f"/books/{book['id']}").json()["title"] == title
    assert_problem(client.post(f"/books/{book['id']}/borrow"), 409)
    assert client.get("/books").json() == [book]
