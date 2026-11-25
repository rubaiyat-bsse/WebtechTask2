import re
from dataclasses import dataclass

from app.errors import ValidationFailed


@dataclass
class Member:
    name: str
    email: str
    id: int | None = None

    def validate(self) -> None:
        errors = []
        if not isinstance(self.name, str) or not 1 <= len(self.name.strip()) <= 120:
            errors.append({"pointer": "/name", "message": "must contain 1 to 120 characters"})
        # A simple lab rule, not full RFC email-address validation.
        if (not isinstance(self.email, str) or len(self.email.strip()) > 254
                or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", self.email.strip())):
            errors.append({"pointer": "/email", "message": "must be an email address such as reader@example.com"})
        if errors:
            raise ValidationFailed("Member fields are invalid", errors)
        self.name = self.name.strip()
        self.email = self.email.strip().lower()
