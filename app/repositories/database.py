import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Database:
    """One connection per use case; a failed use case rolls back completely."""

    def __init__(self, path: str):
        self.path = path

    def initialize(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    total_copies INTEGER NOT NULL CHECK (total_copies >= 0),
                    available_copies INTEGER NOT NULL
                        CHECK (available_copies >= 0 AND available_copies <= total_copies)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL COLLATE NOCASE UNIQUE
                )
            """)

    @contextmanager
    def transaction(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            # Reserve the write lock BEFORE reading, so two borrowers cannot
            # both read the last copy and overwrite each other's changes.
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
