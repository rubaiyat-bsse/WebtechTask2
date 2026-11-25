from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from app import create_app
from app.repositories.book_repository import BookRepository

pytestmark = pytest.mark.integration


def test_records_survive_a_new_app_instance(app, client, make_book, make_member):
    book = make_book()
    member = make_member()
    client.post(f"/books/{book['id']}/borrow")
    with TestClient(create_app({
        "APP_ENV": "test",
        "DATABASE_PATH": app.state.config.DATABASE_PATH,
        "MAX_COPIES": 5,
    })) as restarted:
        assert restarted.get(f"/books/{book['id']}").json()["available_copies"] == 1
        assert restarted.get(f"/members/{member['id']}").json() == member


def test_failed_save_rolls_back_the_whole_transaction(client, make_book, monkeypatch, assert_problem):
    book = make_book()
    original_save = BookRepository.save

    def save_then_fail(self, changed):
        original_save(self, changed)
        raise RuntimeError("simulated failure after UPDATE")

    monkeypatch.setattr(BookRepository, "save", save_then_fail)
    assert_problem(client.post(f"/books/{book['id']}/borrow"), 500)
    assert client.get(f"/books/{book['id']}").json() == book


def test_simultaneous_borrows_cannot_take_the_same_last_copy(app, client, make_book):
    book = make_book(total_copies=1)
    barrier = Barrier(2)
    second_app = create_app({
        "APP_ENV": "test", "MAX_COPIES": 5,
        "DATABASE_PATH": app.state.config.DATABASE_PATH,
    })
    with TestClient(second_app) as second_client:
        def borrow(test_client):
            barrier.wait(timeout=5)
            return test_client.post(f"/books/{book['id']}/borrow").status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(borrow, client)
            second = executor.submit(borrow, second_client)
            assert sorted([first.result(timeout=15), second.result(timeout=15)]) == [200, 409]
    assert client.get(f"/books/{book['id']}").json()["available_copies"] == 0
