"""Loading and checking the user's own RepeaterBook token.

The token is read at run time from an environment variable or from a file the
user keeps outside this repository (for example on an encrypted drive). Only
the variable's *name* or the file's *path* is ever written to local
configuration. The value lives in a :class:`Token`, whose ``repr`` never shows
it, and is registered with :func:`wasds150.logging_setup.register_secret` the
moment it is loaded so no log line can carry it.

Error messages here never quote the value, not even partially.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Mapping, Optional

from wasds150.logging_setup import register_secret
from wasds150.sources.repeaterbook.policy import (
    DEFAULT_TOKEN_ENV,
    SHARED_TOKEN_PREFIX,
    TOKEN_PREFIX,
)


class TokenError(ValueError):
    """The token is missing, malformed, or of a kind this app never accepts."""


class Token:
    """A validated ``rbuapp_`` token. ``str``/``repr`` show only a fingerprint."""

    __slots__ = ("_value", "source")

    def __init__(self, value: str, source: str):
        self._value = validate_token(value)
        self.source = source
        register_secret(self._value)

    def reveal(self) -> str:
        """The raw value, for the request header only."""
        return self._value

    @property
    def fingerprint(self) -> str:
        """Stable, non-reversible id for the request ledger and rate limits."""
        return fingerprint(self._value)

    def __repr__(self) -> str:
        return f"Token(<redacted>, fingerprint={self.fingerprint}, source={self.source})"

    __str__ = __repr__


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def validate_token(value: str) -> str:
    text = (value or "").strip()
    if not text:
        raise TokenError("no RepeaterBook token was provided")
    if text.startswith(SHARED_TOKEN_PREFIX):
        raise TokenError(
            "shared app_ tokens are never accepted; this is a distributed application, "
            "so use your own app-bound rbuapp_ token from RepeaterBook's API Apps page"
        )
    if not text.startswith(TOKEN_PREFIX) or len(text) <= len(TOKEN_PREFIX):
        raise TokenError("a RepeaterBook token for this application must start with rbuapp_")
    if any(ch.isspace() or ord(ch) < 32 for ch in text):
        raise TokenError("the RepeaterBook token contains whitespace or control characters")
    return text


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def check_token_file_path(path_text: str, *, repo_root: Optional[Path] = None) -> Path:
    """A token file must be absolute and must not live inside this repository,
    where it could be committed."""
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        raise TokenError("the RepeaterBook token file path must be absolute")
    if repo_root is not None and _is_inside(path, repo_root):
        raise TokenError("the RepeaterBook token file must live outside this repository")
    return path


def load_token(
    *,
    token_env: Optional[str] = None,
    token_file: Optional[str] = None,
    environ: Optional[Mapping[str, str]] = None,
    repo_root: Optional[Path] = None,
) -> Optional[Token]:
    """The configured token, or ``None`` if nothing is configured or set.

    A configured file wins over the environment. Raises :class:`TokenError`
    for a token that is present but unacceptable.
    """
    environ = os.environ if environ is None else environ
    if token_file:
        path = check_token_file_path(token_file, repo_root=repo_root)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            raise TokenError("the configured RepeaterBook token file could not be read") from None
        first = text.strip().splitlines()[0] if text.strip() else ""
        return Token(first, source="file")
    name = token_env or DEFAULT_TOKEN_ENV
    value = environ.get(name)
    if not value:
        return None
    return Token(value, source=f"env:{name}")
