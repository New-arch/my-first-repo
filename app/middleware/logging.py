"""Structured JSON audit logger (FR-12, SEC-9).

Provides a JSON log formatter so that all log output is machine-parseable.
Configured once at application startup via ``setup_audit_logging()``.

Important: message content is never logged — only metadata (FR-12.5).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Merge any extra fields the caller passed
        for key in ("session_id", "agent_used", "tokens_used", "latency_ms",
                     "request_id", "tool_name", "tool_params", "action"):
            value = getattr(record, key, None)
            if value is not None:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


def setup_audit_logging() -> None:
    """Configure the root logger to emit structured JSON to stderr."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    # Avoid duplicate handlers if called more than once
    if not any(isinstance(h, logging.StreamHandler) and isinstance(h.formatter, JSONFormatter)
               for h in root.handlers):
        root.addHandler(handler)
        root.setLevel(logging.INFO)
