"""Structured, secret-safe application logging."""

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from logging.config import dictConfig

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")


class JSONFormatter(logging.Formatter):
    """Emit machine-readable logs with stable operational fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize one record without dumping arbitrary object internals."""
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_context.get(),
        }
        for key in ("run_id", "tool_call_id", "status"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = str(value)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def configure_logging(log_level: str) -> None:
    """Configure consistent JSON console logging for container collection."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"json": {"()": "app.core.logging.JSONFormatter"}},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {"handlers": ["console"], "level": log_level},
        }
    )
