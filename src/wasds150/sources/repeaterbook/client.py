"""The only code that sends a request to RepeaterBook.

Deliberately separate from :class:`wasds150.cache.http.CachedHttpClient`:
that client sends one User-Agent for every adapter, retries nothing but also
refuses nothing, follows redirects and knows no per-request headers.
RepeaterBook needs the opposite on every point, and the other adapters should
not change to accommodate it.

What this client guarantees, per request:

* the User-Agent is exactly :data:`~wasds150.sources.repeaterbook.policy.USER_AGENT`,
  or nothing is sent;
* the token travels only in the ``X-RB-App-Token`` header, never in the URL;
* the query is the region's fixed parameters and nothing else (no paging);
* redirects are refused, so the token header cannot follow one to another host;
* no retry of any kind; every failure is classified and raised;
* the response is read with a hard size limit.

The transport is injectable so tests never touch the network.
"""
from __future__ import annotations

import datetime
import email.utils
import http.client
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Dict, Mapping, Optional
from urllib.parse import quote, urlencode

from wasds150.logging_setup import redact
from wasds150.sources.repeaterbook.policy import (
    EXPORT_ENDPOINT,
    MAX_RESPONSE_BYTES,
    TIMEOUT_SECONDS,
    TOKEN_HEADER,
    USER_AGENT,
    Region,
)
from wasds150.sources.repeaterbook.token import Token


class RepeaterBookError(Exception):
    """A request was refused locally or failed. Never retried automatically."""

    def __init__(self, message: str, *, status: Optional[int] = None, code: Optional[str] = None):
        super().__init__(redact(message))
        self.status = status
        self.code = code


class UserAgentRefused(RepeaterBookError):
    """The outgoing User-Agent would not be the approved one; nothing was sent."""


class AuthError(RepeaterBookError):
    """401/403 or an auth_*/ua_mismatch error: stop, and wait for the operator."""


class RateLimited(RepeaterBookError):
    """429 or rate_limited: stop and lock refresh."""

    def __init__(self, message: str, *, retry_after: Optional[datetime.timedelta], **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class BadRequest(RepeaterBookError):
    """400/404: the filter or endpoint is wrong."""


class TransientError(RepeaterBookError):
    """408/425/5xx: stop this refresh; no same-action retry."""


class ResponseError(RepeaterBookError):
    """Anything else: a redirect, an oversized body, an unexpected status."""


@dataclass
class HttpResponse:
    status: int
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes = b""


#: ``transport(url, headers, timeout_seconds, max_bytes) -> HttpResponse``
Transport = Callable[[str, Dict[str, str], float, int], HttpResponse]

#: Error codes the documentation lists. Matched as words in the body, since
#: the documentation names the codes but not the JSON shape around them.
_ERROR_CODE = re.compile(
    r"\b(auth_missing|auth_invalid|auth_inactive|auth_revoked|auth_scope_denied|ua_mismatch|rate_limited)\b"
)
_TRANSIENT = {408, 425, 500, 502, 503, 504}


class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None  # urllib then raises HTTPError with the 3xx status


def _read_limited(stream, max_bytes: int) -> bytes:
    chunks = []
    total = 0
    while True:
        chunk = stream.read(65536)
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > max_bytes:
            raise ResponseError(f"response exceeded the {max_bytes}-byte limit; aborted")
        chunks.append(chunk)


def urllib_transport(url: str, headers: Dict[str, str], timeout: float, max_bytes: int) -> HttpResponse:
    opener = urllib.request.build_opener(_RefuseRedirects)
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with opener.open(request, timeout=timeout) as response:
            return HttpResponse(response.status, dict(response.headers.items()), _read_limited(response, max_bytes))
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(65536) if exc.fp is not None else b""
        except (OSError, http.client.HTTPException):
            body = b""
        return HttpResponse(exc.code, dict((exc.headers or {}).items()), body)
    except RepeaterBookError:
        raise
    except (OSError, http.client.HTTPException) as exc:
        # Unreachable host, timeout, reset, TLS failure, truncated body: all
        # transient, none retried. The message names the kind only.
        raise TransientError(
            f"could not complete the RepeaterBook request ({type(exc).__name__}); not retried"
        ) from None


def build_export_url(region: Region) -> str:
    return f"{EXPORT_ENDPOINT}?{urlencode(region.query(), quote_via=quote)}"


def parse_retry_after(value: Optional[str], now: datetime.datetime) -> Optional[datetime.timedelta]:
    """``Retry-After`` as delta-seconds or an HTTP date; ``None`` if absent or
    unparseable."""
    if not value:
        return None
    text = value.strip()
    if text.isdigit():
        return datetime.timedelta(seconds=int(text))
    try:
        when = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    return max(when - now, datetime.timedelta(0))


def _header(headers: Mapping[str, str], name: str) -> Optional[str]:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


def classify(response: HttpResponse, now: datetime.datetime) -> bytes:
    """Return the body of a usable response; raise for everything else.

    Messages name the status and documented error code only. The body is
    never quoted, so nothing the server echoes can reach a log or a report.
    """
    status = response.status
    head = response.body[:65536].decode("utf-8", errors="replace")
    match = _ERROR_CODE.search(head)
    code = match.group(1) if match else None
    where = f"HTTP {status}" + (f" ({code})" if code else "")

    if status == 429 or code == "rate_limited":
        retry_after = parse_retry_after(_header(response.headers, "Retry-After"), now)
        raise RateLimited(f"RepeaterBook rate limit: {where}", retry_after=retry_after, status=status, code=code)
    if status in (401, 403) or (code or "").startswith("auth_") or code == "ua_mismatch":
        raise AuthError(
            f"RepeaterBook refused the credentials, scope or User-Agent: {where}. "
            "Correct the cause; this is never retried automatically.",
            status=status,
            code=code,
        )
    if status in (400, 404):
        raise BadRequest(f"RepeaterBook rejected the query or endpoint: {where}", status=status, code=code)
    if status in _TRANSIENT:
        raise TransientError(f"RepeaterBook is unavailable: {where}; not retried", status=status, code=code)
    if status != 200:
        raise ResponseError(f"unexpected RepeaterBook response: {where}", status=status, code=code)
    return response.body


class RepeaterBookClient:
    def __init__(
        self,
        token: Token,
        *,
        transport: Optional[Transport] = None,
        user_agent: str = USER_AGENT,
        timeout_seconds: float = TIMEOUT_SECONDS,
        max_bytes: int = MAX_RESPONSE_BYTES,
    ):
        self.token = token
        self.transport = transport or urllib_transport
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes

    def request_headers(self) -> Dict[str, str]:
        if self.user_agent != USER_AGENT:
            raise UserAgentRefused(
                "refusing to contact RepeaterBook with a User-Agent other than the approved one"
            )
        return {"User-Agent": USER_AGENT, TOKEN_HEADER: self.token.reveal(), "Accept": "application/json"}

    def export(self, region: Region, *, clock: Callable[[], datetime.datetime]) -> bytes:
        """One HTTP request for one region. Raises on anything but a usable 200.

        ``clock`` is read when the response arrives, so an HTTP-date
        ``Retry-After`` is measured from receipt, not from sending."""
        headers = self.request_headers()
        url = build_export_url(region)
        if self.token.reveal() in url:  # defence in depth; region.query() cannot carry it
            raise UserAgentRefused("refusing to put the token in a URL")
        response = self.transport(url, headers, self.timeout_seconds, self.max_bytes)
        return classify(response, clock())
