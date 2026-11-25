import logging
import os
from pathlib import Path


class Config:
    """Environment settings, with explicit overrides for isolated tests."""

    def __init__(self, overrides: dict | None = None):
        defaults = {
            "APP_ENV": "development",
            "LOG_LEVEL": "INFO",
            "MAX_COPIES": "50",
            "DATABASE_PATH": str(Path(__file__).resolve().parent.parent / "data/library.sqlite3"),
        }
        values = {key: os.environ.get(key, value) for key, value in defaults.items()}
        for key, value in (overrides or {}).items():
            if key not in defaults:
                raise ValueError(f"Unknown setting: {key}")
            values[key] = value

        self.APP_ENV = str(values["APP_ENV"])
        self.LOG_LEVEL = str(values["LOG_LEVEL"]).upper()
        self.MAX_COPIES = int(values["MAX_COPIES"])
        self.DATABASE_PATH = str(values["DATABASE_PATH"])
        if self.APP_ENV not in {"development", "test", "production"}:
            raise ValueError("APP_ENV must be development, test, or production")
        if self.LOG_LEVEL not in logging.getLevelNamesMapping():
            raise ValueError("LOG_LEVEL must be a valid logging level")
        if self.MAX_COPIES < 1:
            raise ValueError("MAX_COPIES must be a positive integer")
        if not self.DATABASE_PATH.strip() or self.DATABASE_PATH == ":memory:":
            raise ValueError("DATABASE_PATH must be a file path; tests use a temporary file")
