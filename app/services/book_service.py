import logging

from app.domain.book import Book
from app.errors import NotFound
from app.services.ports import BookStore, UnitOfWork

log = logging.getLogger(__name__)


class BookService:
    def __init__(self, unit_of_work: UnitOfWork, max_copies: int):
        self.unit_of_work = unit_of_work
        self.max_copies = max_copies

    @staticmethod
    def _require(repo: BookStore, book_id: int) -> Book:
        book = repo.get(book_id)
        if book is None:
            raise NotFound(f"Book {book_id} does not exist")
        return book

    def add_book(self, title: str, author: str, total_copies: int) -> Book:
        book = Book(title, author, total_copies, total_copies)
        book.validate(self.max_copies)
        with self.unit_of_work() as repos:
            saved = repos.books.add(book)
        log.info("book added id=%s", saved.id)
        return saved

    def get_book(self, book_id: int) -> Book:
        with self.unit_of_work() as repos:
            return self._require(repos.books, book_id)

    def list_books(self) -> list[Book]:
        with self.unit_of_work() as repos:
            return repos.books.list()

    def update_book(self, book_id: int, title: str, author: str, total_copies: int) -> Book:
        with self.unit_of_work() as repos:
            book = self._require(repos.books, book_id)
            book.replace(title, author, total_copies, self.max_copies)
            repos.books.save(book)
        log.info("book updated id=%s", book_id)
        return book

    def delete_book(self, book_id: int) -> None:
        with self.unit_of_work() as repos:
            book = self._require(repos.books, book_id)
            book.ensure_deletable()
            repos.books.delete(book_id)
        log.info("book deleted id=%s", book_id)

    def borrow_book(self, book_id: int) -> Book:
        with self.unit_of_work() as repos:
            book = self._require(repos.books, book_id)
            book.borrow()
            repos.books.save(book)
        log.info("book borrowed id=%s remaining=%s", book_id, book.available_copies)
        return book

    def return_book(self, book_id: int) -> Book:
        with self.unit_of_work() as repos:
            book = self._require(repos.books, book_id)
            book.give_back()
            repos.books.save(book)
        log.info("book returned id=%s available=%s", book_id, book.available_copies)
        return book
