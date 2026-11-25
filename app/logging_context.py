import logging
import sys
from contextvars import ContextVar

request_id: ContextVar[str] = ContextVar("request_id", default="startup")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True


def configure_logging(level: str) -> None:
    logger = logging.getLogger("app")
    logger.setLevel(level)
    # Repeated create_app() calls in tests must not add duplicate handlers.
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.addFilter(RequestIdFilter())
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s [%(request_id)s]"
        ))
        logger.addHandler(handler)
