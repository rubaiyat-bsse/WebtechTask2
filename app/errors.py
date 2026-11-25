"""Application exceptions. HTTP mappings belong to the web layer, not here."""


class AppError(Exception):
    def __init__(self, detail: str, errors: list[dict[str, str]] | None = None):
        super().__init__(detail)
        self.detail = detail
        self.errors = errors or []


class ValidationFailed(AppError):
    pass


class NotFound(AppError):
    pass


class Conflict(AppError):
    pass
