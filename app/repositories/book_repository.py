from sqlite3 import Connection

from app.domain.book import Book


class BookRepository:
    """SQL and row-to-domain conversion only; no business decisions."""

    def __init__(self, connection: Connection):
        self.connection = connection

    def add(self, book: Book) -> Book:
        cursor = self.connection.execute(
            "INSERT INTO books (title, author, total_copies, available_copies) VALUES (?, ?, ?, ?)",
            (book.title, book.author, book.total_copies, book.available_copies),
        )
        book.id = cursor.lastrowid
        return book

    def get(self, book_id: int) -> Book | None:
        row = self.connection.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return None
        return Book(**dict(row))

    def list(self) -> list[Book]:
        rows = self.connection.execute("SELECT * FROM books ORDER BY id").fetchall()
        return [Book(**dict(row)) for row in rows]

    def save(self, book: Book) -> None:
        self.connection.execute(
            "UPDATE books SET title = ?, author = ?, total_copies = ?, available_copies = ? WHERE id = ?",
            (book.title, book.author, book.total_copies, book.available_copies, book.id),
        )

    def delete(self, book_id: int) -> None:
        self.connection.execute("DELETE FROM books WHERE id = ?", (book_id,))
