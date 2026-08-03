"""Logging setup: console + rotating file handler, with secret redaction.

There are no secrets handled by phases 1-4, but the redaction filter is
wired in now so later phases (RadioReference Premium API keys, etc.) get it
for free instead of requiring every future log call site to remember it.
"""
from __future__ import annotations

import logging
import logging.handlers
import re
from pathlib import Path
from typing import Optional

_REDACT_PATTERNS = [
    re.compile(r"(api[_-]?key\s*[=:]\s*)([^\s'\"]+)", re.IGNORECASE),
    re.compile(r"(token\s*[=:]\s*)([^\s'\"]+)", re.IGNORECASE),
    re.compile(r"(password\s*[=:]\s*)([^\s'\"]+)", re.IGNORECASE),
]


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        redacted = msg
        for pattern in _REDACT_PATTERNS:
            redacted = pattern.sub(r"\1***REDACTED***", redacted)
        if redacted != msg:
            record.msg = redacted
            record.args = ()
        return True


def configure_logging(log_file: Optional[Path] = None, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("wasds150")
    logger.setLevel(level)
    logger.handlers.clear()
    logger.addFilter(RedactionFilter())

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%Y-%m-%dT%H:%M:%S"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger
