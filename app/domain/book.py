from dataclasses import dataclass

from app.errors import Conflict, ValidationFailed


@dataclass
class Book:
    """Inventory and its rules, independent of FastAPI and SQLite."""

    title: str
    author: str
    total_copies: int
    available_copies: int
    id: int | None = None

    def validate(self, max_copies: int) -> None:
        errors = []
        for field, limit in (("title", 200), ("author", 120)):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
                errors.append({"pointer": f"/{field}", "message": f"must contain 1 to {limit} characters"})
        if type(self.total_copies) is not int or not 0 <= self.total_copies <= max_copies:
            errors.append({"pointer": "/total_copies", "message": f"must be an integer between 0 and {max_copies}"})
        if errors:
            raise ValidationFailed("Book fields are invalid", errors)
        self.title = self.title.strip()
        self.author = self.author.strip()
        if type(self.available_copies) is not int or not 0 <= self.available_copies <= self.total_copies:
            raise Conflict("Available copies must be between zero and total copies")

    def borrow(self) -> None:
        if self.available_copies == 0:
            raise Conflict("No copies of this book are available")
        self.available_copies -= 1

    def give_back(self) -> None:
        if self.available_copies == self.total_copies:
            raise Conflict("No borrowed copies of this book remain to return")
        self.available_copies += 1

    def replace(self, title: str, author: str, total_copies: int, max_copies: int) -> None:
        # Validate a candidate so failure cannot partially mutate this object.
        candidate = Book(title, author, total_copies, total_copies, self.id)
        candidate.validate(max_copies)
        borrowed = self.total_copies - self.available_copies
        if total_copies < borrowed:
            raise Conflict("Total copies cannot be less than the number currently borrowed")
        self.title = candidate.title
        self.author = candidate.author
        self.total_copies = total_copies
        self.available_copies = total_copies - borrowed

    def ensure_deletable(self) -> None:
        if self.available_copies != self.total_copies:
            raise Conflict("Return all borrowed copies before deleting this book")
