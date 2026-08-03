"""Loopback-only auth for the local web UI.

A random bearer token is generated per server run and never persisted; the
server only binds to loopback addresses, and every mutating API request
must present the token via the ``X-Wasds150-Token`` header. The token is
also embedded into the served ``index.html`` (loopback-only, same process)
so the page's own JS can call the API without prompting the user for
anything.
"""
from __future__ import annotations

import secrets

TOKEN_HEADER = "X-Wasds150-Token"


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def token_matches(expected: str, headers) -> bool:
    provided = headers.get(TOKEN_HEADER)
    return provided is not None and secrets.compare_digest(provided, expected)
