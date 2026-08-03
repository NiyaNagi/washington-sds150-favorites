"""Cache layer tests: sqlite content-addressed store + conditional-GET HTTP
client, exercised against a real local ``http.server`` (stdlib-only, no
live network dependency) so TTL/ETag/offline/size-limit behavior is fully
covered without relying on any external endpoint being reachable in CI.
"""
from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from wasds150.cache.http import (
    CachedHttpClient,
    FetchSizeLimitError,
    OfflineModeError,
    RateLimiter,
)
from wasds150.cache.store import HttpCacheStore


class _Handler(BaseHTTPRequestHandler):
    server_version = "test/0.1"

    def log_message(self, fmt, *args):  # noqa: A003 - silence test server logs
        pass

    def do_GET(self):  # noqa: N802
        body = self.server.body
        etag = self.server.etag
        if etag and self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.end_headers()
            return
        self.server.request_count += 1
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        if etag:
            self.send_header("ETag", etag)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def local_server():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    server.body = b"hello world"
    server.etag = '"abc123"'
    server.request_count = 0
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    thread.join(timeout=5)


def _url(server, path: str = "/data.txt") -> str:
    return f"http://{server.server_address[0]}:{server.server_address[1]}{path}"


# --------------------------------------------------------------- store ----
def test_store_put_get_roundtrip(tmp_path):
    store = HttpCacheStore(tmp_path / "cache")
    entry = store.put(
        "http://example.test/a", content=b"abc", ttl_seconds=60, status=200, source_id="test"
    )
    fetched = store.get("http://example.test/a")
    assert fetched is not None
    assert fetched.content_hash == entry.content_hash
    assert store.read_blob(fetched) == b"abc"


def test_store_content_addressing_dedupes_identical_bytes(tmp_path):
    store = HttpCacheStore(tmp_path / "cache")
    store.put("http://example.test/a", content=b"same", ttl_seconds=60, status=200)
    store.put("http://example.test/b", content=b"same", ttl_seconds=60, status=200)
    blobs = list((tmp_path / "cache" / "blobs").iterdir())
    assert len(blobs) == 1


def test_store_entries_for_source(tmp_path):
    store = HttpCacheStore(tmp_path / "cache")
    store.put("http://example.test/a", content=b"1", ttl_seconds=60, status=200, source_id="wwara")
    store.put("http://example.test/b", content=b"2", ttl_seconds=60, status=200, source_id="iacc")
    assert len(store.entries_for_source("wwara")) == 1
    assert len(store.entries_for_source("iacc")) == 1
    assert len(store.entries_for_source("nope")) == 0


def test_cache_entry_is_fresh_ttl(tmp_path):
    store = HttpCacheStore(tmp_path / "cache")
    entry = store.put("http://example.test/a", content=b"x", ttl_seconds=3600, status=200)
    assert entry.is_fresh() is True

    stale = store.put("http://example.test/b", content=b"y", ttl_seconds=0, status=200)
    time.sleep(0.01)
    assert stale.is_fresh() is False


# ------------------------------------------------------------------ http ---
def test_fetch_hits_network_then_serves_from_cache(tmp_path, local_server):
    store = HttpCacheStore(tmp_path / "cache")
    client = CachedHttpClient(store, rate_limiter=RateLimiter(min_interval_seconds=0))
    url = _url(local_server)

    first = client.fetch(url, ttl_seconds=3600, source_id="test")
    assert first.status == "fetched"
    assert first.content == b"hello world"
    assert local_server.request_count == 1

    second = client.fetch(url, ttl_seconds=3600, source_id="test")
    assert second.status == "cached-fresh"
    assert local_server.request_count == 1  # no second network hit


def test_fetch_conditional_get_304_not_modified(tmp_path, local_server):
    store = HttpCacheStore(tmp_path / "cache")
    client = CachedHttpClient(store, rate_limiter=RateLimiter(min_interval_seconds=0))
    url = _url(local_server)

    client.fetch(url, ttl_seconds=0, source_id="test")
    assert local_server.request_count == 1

    # ttl_seconds=0 means immediately stale -> next fetch revalidates.
    result = client.fetch(url, ttl_seconds=0, source_id="test", force=True)
    assert result.status == "not-modified"
    assert result.content == b"hello world"


def test_offline_mode_serves_stale_cache(tmp_path, local_server):
    store = HttpCacheStore(tmp_path / "cache")
    online_client = CachedHttpClient(store, rate_limiter=RateLimiter(min_interval_seconds=0))
    url = _url(local_server)
    online_client.fetch(url, ttl_seconds=0, source_id="test")

    offline_client = CachedHttpClient(store, offline=True, rate_limiter=RateLimiter(min_interval_seconds=0))
    result = offline_client.fetch(url, ttl_seconds=0, source_id="test")
    assert result.status == "cached-stale-offline"
    assert result.content == b"hello world"


def test_offline_mode_no_cache_raises(tmp_path, local_server):
    store = HttpCacheStore(tmp_path / "cache")
    client = CachedHttpClient(store, offline=True, rate_limiter=RateLimiter(min_interval_seconds=0))
    with pytest.raises(OfflineModeError):
        client.fetch(_url(local_server), ttl_seconds=3600, source_id="test")


def test_size_limit_enforced(tmp_path, local_server):
    local_server.body = b"x" * 1000
    store = HttpCacheStore(tmp_path / "cache")
    client = CachedHttpClient(store, rate_limiter=RateLimiter(min_interval_seconds=0))
    with pytest.raises(FetchSizeLimitError):
        client.fetch(_url(local_server), ttl_seconds=3600, source_id="test", max_bytes=10)
