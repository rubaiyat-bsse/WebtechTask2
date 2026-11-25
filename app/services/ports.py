"""Storage contracts: services depend on these operations, not on SQLite.

A Protocol describes the methods an object must provide (similar to a C++
interface). Implementations do not need to inherit from it.
"""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol

from app.domain.book import Book
from app.domain.member import Member


class BookStore(Protocol):
    def add(self, book: Book) -> Book: ...
    def get(self, book_id: int) -> Book | None: ...
    def list(self) -> list[Book]: ...
    def save(self, book: Book) -> None: ...
    def delete(self, book_id: int) -> None: ...


class MemberStore(Protocol):
    def add(self, member: Member) -> Member: ...
    def get(self, member_id: int) -> Member | None: ...
    def get_by_email(self, email: str) -> Member | None: ...
    def list(self) -> list[Member]: ...
    def save(self, member: Member) -> None: ...
    def delete(self, member_id: int) -> None: ...


@dataclass
class Repositories:
    books: BookStore
    members: MemberStore


# Calling this opens a transaction and supplies repositories for that transaction.
UnitOfWork = Callable[[], AbstractContextManager[Repositories]]
