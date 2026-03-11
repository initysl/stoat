"""Structured logging helpers for Stoat CLI operations."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from stoat.config import LoggingConfig


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event_name", record.getMessage()),
            "message": record.getMessage(),
        }
        payload.update(getattr(record, "stoat_fields", {}))
        return json.dumps(payload, default=str)


def configure_logging(config: LoggingConfig) -> logging.Logger:
    """Configure the Stoat file logger without affecting CLI output."""
    logger = logging.getLogger("stoat")
    logger.setLevel(getattr(logging, config.level, logging.INFO))
    logger.propagate = False

    log_path = Path(config.file).expanduser()
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_path,
            maxBytes=config.max_size_mb * 1024 * 1024,
            backupCount=config.backup_count,
        )
        handler.setFormatter(_JsonFormatter())
        logger.handlers.clear()
        logger.addHandler(handler)
    except OSError:
        logger.handlers.clear()
        logger.addHandler(logging.NullHandler())

    return logger


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Emit a structured log event."""
    logger.info(event, extra={"event_name": event, "stoat_fields": fields})
