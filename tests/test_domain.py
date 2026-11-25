from contextlib import contextmanager
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.config import Config
from app.domain.book import Book
from app.domain.member import Member
from app.errors import Conflict, ValidationFailed
from app.services.book_service import BookService

pytestmark = pytest.mark.unit


def test_book_domain_rules_need_no_web_server():
    book = Book("Algorithms", "CLRS", 1, 1)
    book.validate(5)
    book.borrow()
    assert book.available_copies == 0
    with pytest.raises(Conflict):
        book.borrow()
    with pytest.raises(Conflict):
        book.ensure_deletable()
    book.give_back()
    assert book.available_copies == 1
    with pytest.raises(Conflict):
        book.give_back()
    book.ensure_deletable()


def test_domain_validation_runs_outside_pydantic():
    with pytest.raises(ValidationFailed) as failure:
        Book(" ", "Author", 6, 6).validate(5)
    assert {error["pointer"] for error in failure.value.errors} == {"/title", "/total_copies"}
    with pytest.raises(ValidationFailed):
        Member("Reader", "bad-address").validate()


def test_failed_domain_replace_does_not_partially_change_object():
    book = Book("Old", "Author", 2, 1)
    before = replace(book)
    with pytest.raises(Conflict):
        book.replace("Should not be saved", "New author", 0, 5)
    assert book == before


def test_service_accepts_fake_storage_without_fastapi_or_sqlite():
    class MemoryBooks:
        def __init__(self):
            self.rows = {}

        def add(self, book):
            book.id = len(self.rows) + 1
            self.rows[book.id] = replace(book)
            return book

        def get(self, book_id):
            book = self.rows.get(book_id)
            if book is None:
                return None
            return replace(book)

        def save(self, book):
            self.rows[book.id] = replace(book)

    repo = MemoryBooks()

    @contextmanager
    def fake_unit_of_work():
        yield SimpleNamespace(books=repo)

    service = BookService(fake_unit_of_work, max_copies=5)
    book = service.add_book("Algorithms", "CLRS", 1)
    assert service.borrow_book(book.id).available_copies == 0
    with pytest.raises(Conflict):
        service.borrow_book(book.id)
    assert service.get_book(book.id).available_copies == 0
    assert service.return_book(book.id).available_copies == 1


@pytest.mark.parametrize("overrides", [
    {"MAX_COPIES": 0}, {"MAX_COPIES": "bad"}, {"LOG_LEVEL": "NOPE"},
    {"APP_ENV": "unknown"}, {"DATABASE_PATH": ""}, {"UNRECOGNIZED": True},
])
def test_invalid_configuration_fails_at_startup(overrides):
    with pytest.raises(ValueError):
        Config(overrides)
