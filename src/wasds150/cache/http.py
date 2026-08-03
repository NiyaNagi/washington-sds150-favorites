"""Conditional-GET HTTP client on top of :class:`wasds150.cache.store.HttpCacheStore`:
TTL-gated fetch, ``ETag``/``Last-Modified`` revalidation, a hard response-size
limit (enforced while streaming, not after the fact), per-host rate limiting,
and an explicit offline mode that serves stale cache instead of ever
touching the network.

Every adapter in :mod:`wasds150.sources` goes through this client rather
than calling ``urllib`` directly, so TTL/offline/rate-limit/size-limit
behavior is uniform and only needs testing once.
"""
from __future__ import annotations

import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlsplit

from wasds150.cache.store import CacheEntry, HttpCacheStore

DEFAULT_USER_AGENT = "wasds150/0.1 (+https://github.com/NiyaNagi/washington-sds150-favorites)"
DEFAULT_MAX_BYTES = 20 * 1024 * 1024  # 20 MiB
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MIN_HOST_INTERVAL_SECONDS = 1.0


class FetchError(Exception):
    """Base class for all cached-fetch errors."""


class OfflineModeError(FetchError):
    """Raised when offline mode is on and no usable cached copy exists."""


class FetchSizeLimitError(FetchError):
    """Raised when a response would exceed the configured byte limit."""


@dataclass
class FetchResult:
    #: "cached-fresh" | "not-modified" | "fetched" | "cached-stale-offline"
    status: str
    content: bytes
    entry: CacheEntry


class RateLimiter:
    """A minimal per-host rate limiter: never issue two requests to the same
    host closer together than ``min_interval_seconds``. Thread-safe."""

    def __init__(self, min_interval_seconds: float = DEFAULT_MIN_HOST_INTERVAL_SECONDS):
        self.min_interval_seconds = min_interval_seconds
        self._last_call: dict = {}
        self._lock = threading.Lock()

    def wait_if_needed(self, host: str, *, sleep=time.sleep, now=time.monotonic) -> float:
        """Blocks (via ``sleep``) just long enough to respect the interval;
        returns the number of seconds waited (0 if none needed). ``sleep``/
        ``now`` are injectable for deterministic tests."""
        with self._lock:
            last = self._last_call.get(host)
            current = now()
            wait_for = 0.0
            if last is not None:
                elapsed = current - last
                if elapsed < self.min_interval_seconds:
                    wait_for = self.min_interval_seconds - elapsed
            self._last_call[host] = current + wait_for
        if wait_for > 0:
            sleep(wait_for)
        return wait_for


def _read_with_limit(response, max_bytes: int) -> bytes:
    chunks = []
    total = 0
    chunk_size = 65536
    while True:
        chunk = response.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise FetchSizeLimitError(
                f"response exceeded the {max_bytes}-byte limit while streaming; aborted"
            )
        chunks.append(chunk)
    return b"".join(chunks)


class CachedHttpClient:
    def __init__(
        self,
        store: HttpCacheStore,
        *,
        offline: bool = False,
        max_bytes: int = DEFAULT_MAX_BYTES,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        self.store = store
        self.offline = offline
        self.max_bytes = max_bytes
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.rate_limiter = rate_limiter or RateLimiter()

    def fetch(
        self, url: str, *, ttl_seconds: int, source_id: str, force: bool = False, max_bytes: Optional[int] = None
    ) -> FetchResult:
        """Fetch ``url``, honoring TTL/offline/conditional-GET/size-limit
        rules. ``force`` bypasses the TTL freshness check (still uses
        conditional-GET headers, so an unchanged resource costs no
        bandwidth beyond the request itself)."""
        entry = self.store.get(url)
        effective_max_bytes = max_bytes if max_bytes is not None else self.max_bytes

        if entry is not None and not force and entry.is_fresh():
            return FetchResult(status="cached-fresh", content=self.store.read_blob(entry), entry=entry)

        if self.offline:
            if entry is not None:
                return FetchResult(status="cached-stale-offline", content=self.store.read_blob(entry), entry=entry)
            raise OfflineModeError(f"offline mode is on and there is no cached copy of {url}")

        host = urlsplit(url).netloc
        self.rate_limiter.wait_if_needed(host)

        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        if entry is not None:
            if entry.etag:
                request.add_header("If-None-Match", entry.etag)
            if entry.last_modified:
                request.add_header("If-Modified-Since", entry.last_modified)

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                content = _read_with_limit(response, effective_max_bytes)
                new_entry = self.store.put(
                    url,
                    content=content,
                    ttl_seconds=ttl_seconds,
                    status=response.status,
                    etag=response.headers.get("ETag"),
                    last_modified=response.headers.get("Last-Modified"),
                    content_type=response.headers.get("Content-Type"),
                    source_id=source_id,
                )
                return FetchResult(status="fetched", content=content, entry=new_entry)
        except urllib.error.HTTPError as exc:
            if exc.code == 304 and entry is not None:
                touched = self.store.touch(url, ttl_seconds=ttl_seconds)
                return FetchResult(status="not-modified", content=self.store.read_blob(touched), entry=touched)
            raise
