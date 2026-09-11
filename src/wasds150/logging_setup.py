"""Logging setup: console + rotating file handler, with secret redaction.

There are no secrets handled by phases 1-4, but the redaction filter is
wired in now so later phases (RadioReference Premium API keys, etc.) get it
for free instead of requiring every future log call site to remember it.
"""
from __future__ import annotations

import logging
import logging.handlers
import re
import threading
from pathlib import Path
from typing import Optional, Set

_MASK = "***REDACTED***"

_REDACT_PATTERNS = [
    re.compile(r"(api[_-]?key\s*[=:]\s*)([^\s'\"]+)", re.IGNORECASE),
    re.compile(r"(token\s*[=:]\s*)([^\s'\"]+)", re.IGNORECASE),
    re.compile(r"(password\s*[=:]\s*)([^\s'\"]+)", re.IGNORECASE),
    # RepeaterBook tokens have recognisable prefixes, so they are masked even
    # when nothing labels them as a token.
    re.compile(r"\b(rbuapp_)([A-Za-z0-9._~+/=-]+)"),
    re.compile(r"\b(app_)([A-Za-z0-9._~+/=-]{8,})"),
]

#: Exact values registered at run time (see :func:`register_secret`).
_SECRETS: Set[str] = set()
_SECRETS_LOCK = threading.Lock()


def register_secret(value: str) -> None:
    """Mask ``value`` wherever it appears in a log line or :func:`redact` output
    for the rest of this process. Short values are ignored so a mistake cannot
    blank out ordinary words."""
    if value and len(value) >= 8:
        with _SECRETS_LOCK:
            _SECRETS.add(value)


def redact(text: str) -> str:
    """``text`` with every registered secret and recognised credential masked."""
    if not text:
        return text
    with _SECRETS_LOCK:
        secrets = sorted(_SECRETS, key=len, reverse=True)
    for secret in secrets:
        text = text.replace(secret, _MASK)
    for pattern in _REDACT_PATTERNS:
        text = pattern.sub(r"\1" + _MASK, text)
    return text


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        redacted = redact(msg)
        if redacted != msg:
            record.msg = redacted
            record.args = ()
        if record.exc_info and not record.exc_text:
            # Formatters reuse a pre-set exc_text, so the traceback is masked too.
            record.exc_text = redact(logging.Formatter().formatException(record.exc_info))
        return True


def configure_logging(log_file: Optional[Path] = None, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("wasds150")
    logger.setLevel(level)
    logger.handlers.clear()
    redaction = RedactionFilter()
    logger.addFilter(redaction)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%Y-%m-%dT%H:%M:%S"
    )

    # Handler-level too: a logger's own filters never see records propagated
    # from child loggers such as ``wasds150.webui``.
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.addFilter(redaction)
    logger.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(redaction)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger
