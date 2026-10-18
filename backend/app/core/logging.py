"""Structured application logging infrastructure for Aegis.

Provides consistent JSON formatting, contextual request tracing, and sensitive data masking.
"""

import contextvars
import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

# Context variable for request correlation tracing
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

def sanitize_message(message: str) -> str:
    """Mask credentials, tokens, secrets, emails, phone numbers, and DB connection strings from log output."""
    from app.security.sanitizer import DataSanitizer

    return DataSanitizer.sanitize_text(message)


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON with contextual metadata."""

    def __init__(
        self, service_name: str = "aegis-backend", environment: str = "development"
    ) -> None:
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "message": sanitize_message(record.getMessage()),
            "service": self.service_name,
            "environment": self.environment,
        }

        # Include request ID if present in async context
        req_id = request_id_ctx.get()
        if req_id:
            log_payload["request_id"] = req_id

        # Include exception trace if available
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        # Include extra attributes attached to record
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_payload["extra"] = record.extra

        return json.dumps(log_payload)


class ConsoleFormatter(logging.Formatter):
    """Readable console formatter for local interactive development."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = request_id_ctx.get()
        req_str = f" [{req_id[:8]}]" if req_id else ""
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        msg = sanitize_message(record.getMessage())
        formatted = (
            f"{timestamp} | {record.levelname:<8} | {record.name}:{record.module}{req_str} - {msg}"
        )
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)
        return formatted


def setup_logging(
    log_level: str = "INFO", environment: str = "development", service_name: str = "aegis-backend"
) -> None:
    """Initialize root and application loggers."""
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    if environment == "production":
        console_handler.setFormatter(
            StructuredJsonFormatter(service_name=service_name, environment=environment)
        )
    else:
        console_handler.setFormatter(ConsoleFormatter())

    root_logger.addHandler(console_handler)

    # Quieten overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger instance."""
    return logging.getLogger(name)
