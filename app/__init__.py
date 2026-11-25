import logging
import re
import time
import uuid
from contextlib import contextmanager
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.config import Config
from app.errors import AppError, Conflict, NotFound, ValidationFailed
from app.logging_context import configure_logging, request_id
from app.repositories.book_repository import BookRepository
from app.repositories.database import Database
from app.repositories.member_repository import MemberRepository
from app.routes import books, members
from app.services.book_service import BookService
from app.services.member_service import MemberService
from app.services.ports import Repositories

log = logging.getLogger("app.http")


def problem(request: Request, status: int, title: str, detail: str, code: str,
            errors: list | None = None, headers: dict | None = None) -> JSONResponse:
    body = {
        "type": f"/problems/{code}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "requestId": request_id.get(),
    }
    if errors:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type="application/problem+json", headers=headers)


def create_app(overrides: dict | None = None) -> FastAPI:
    config = Config(overrides)
    configure_logging(config.LOG_LEVEL)
    app = FastAPI(
        title="Bookshelf Library API",
        version="1.0.0",
        description="Layered FastAPI lab: Books and Members CRUD with inventory borrowing rules.",
        debug=False,
    )
    app.state.config = config

    # Composition root: concrete dependencies are selected and wired ONLY here.
    database = Database(config.DATABASE_PATH)
    database.initialize()

    @contextmanager
    def unit_of_work():
        with database.transaction() as connection:
            yield Repositories(BookRepository(connection), MemberRepository(connection))

    app.state.book_service = BookService(unit_of_work, config.MAX_COPIES)
    app.state.member_service = MemberService(unit_of_work)
    app.include_router(books.router)
    app.include_router(members.router)

    @app.get("/health", tags=["Operations"])
    def health():
        return {"status": "ok"}

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        mappings = {
            ValidationFailed: (422, "Validation failed", "validation_failed"),
            NotFound: (404, "Resource not found", "not_found"),
            Conflict: (409, "Request conflicts with current state", "conflict"),
        }
        status, title, code = mappings[type(exc)]
        return problem(request, status, title, exc.detail, code, exc.errors)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            location = list(error["loc"])
            if location and location[0] in {"body", "path", "query", "header"}:
                location = location[1:]
            # JSON Pointer escaping, without echoing submitted input or secrets.
            pointer = "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in location)
            errors.append({"pointer": pointer, "message": error["msg"]})
        return problem(request, 422, "Validation failed", "Request fields are invalid",
                       "validation_failed", errors)

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException):
        title = HTTPStatus(exc.status_code).phrase
        return problem(request, exc.status_code, title, str(exc.detail),
                       title.lower().replace(" ", "_"), headers=exc.headers)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        supplied = request.headers.get("X-Request-ID", "")
        # Only accept bounded, log-safe request IDs; otherwise generate one.
        if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", supplied):
            current_id = supplied
        else:
            current_id = uuid.uuid4().hex[:12]
        token = request_id.set(current_id)
        started = time.perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception:
                # Catch before the response leaves so 500s get the same ID,
                # problem format and access log as successful responses.
                log.exception("unhandled error")
                response = problem(request, 500, "Internal server error",
                                   "Something went wrong", "internal_error")
            response.headers["X-Request-ID"] = current_id
            log.info("%s %s -> %s duration_ms=%.2f", request.method, request.url.path,
                     response.status_code, (time.perf_counter() - started) * 1000)
            return response
        finally:
            request_id.reset(token)

    return app
