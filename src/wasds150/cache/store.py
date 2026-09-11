"""sqlite-backed HTTP cache metadata index + content-addressed blob store.

Every fetched response is stored once under ``blobs/<sha256>.bin`` (so two
URLs that happen to return byte-identical content share storage), with a
sqlite row per **URL** recording which blob it currently points to, the
conditional-GET headers needed for the next request (``ETag``/
``Last-Modified``), a TTL, and provenance (``source_id``, fetch time,
status). This is the single place every source adapter's fetch provenance
comes from for ``wasds150 sources status``/the web UI's provenance view.
"""
from __future__ import annotations

import datetime
import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS http_cache (
    url TEXT PRIMARY KEY,
    etag TEXT,
    last_modified TEXT,
    content_hash TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    ttl_seconds INTEGER NOT NULL,
    status INTEGER NOT NULL,
    content_type TEXT,
    size_bytes INTEGER NOT NULL,
    source_id TEXT
);
"""


@dataclass
class CacheEntry:
    url: str
    content_hash: str
    fetched_at: str  # ISO 8601 UTC
    ttl_seconds: int
    status: int
    size_bytes: int
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    content_type: Optional[str] = None
    source_id: Optional[str] = None

    def is_fresh(self, now: Optional[datetime.datetime] = None) -> bool:
        now = now or datetime.datetime.now(datetime.timezone.utc)
        fetched = datetime.datetime.fromisoformat(self.fetched_at)
        age = (now - fetched).total_seconds()
        return age < self.ttl_seconds

    def age_seconds(self, now: Optional[datetime.datetime] = None) -> float:
        now = now or datetime.datetime.now(datetime.timezone.utc)
        fetched = datetime.datetime.fromisoformat(self.fetched_at)
        return (now - fetched).total_seconds()


def _row_to_entry(row: sqlite3.Row) -> CacheEntry:
    return CacheEntry(
        url=row["url"],
        etag=row["etag"],
        last_modified=row["last_modified"],
        content_hash=row["content_hash"],
        fetched_at=row["fetched_at"],
        ttl_seconds=row["ttl_seconds"],
        status=row["status"],
        content_type=row["content_type"],
        size_bytes=row["size_bytes"],
        source_id=row["source_id"],
    )


class HttpCacheStore:
    """A sqlite index (``cache.db``) plus a content-addressed blob
    directory (``blobs/``), both under ``cache_dir``."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.blobs_dir = self.cache_dir / "blobs"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.blobs_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "cache.db"
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def _blob_path(self, content_hash: str) -> Path:
        return self.blobs_dir / f"{content_hash}.bin"

    def get(self, url: str) -> Optional[CacheEntry]:
        row = self._conn.execute("SELECT * FROM http_cache WHERE url = ?", (url,)).fetchone()
        return _row_to_entry(row) if row else None

    def put(
        self,
        url: str,
        *,
        content: bytes,
        ttl_seconds: int,
        status: int,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        content_type: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> CacheEntry:
        content_hash = hashlib.sha256(content).hexdigest()
        blob_path = self._blob_path(content_hash)
        if not blob_path.exists():
            blob_path.write_bytes(content)
        fetched_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        entry = CacheEntry(
            url=url,
            etag=etag,
            last_modified=last_modified,
            content_hash=content_hash,
            fetched_at=fetched_at,
            ttl_seconds=ttl_seconds,
            status=status,
            content_type=content_type,
            size_bytes=len(content),
            source_id=source_id,
        )
        self._conn.execute(
            """INSERT INTO http_cache
               (url, etag, last_modified, content_hash, fetched_at, ttl_seconds, status, content_type, size_bytes, source_id)
               VALUES (:url, :etag, :last_modified, :content_hash, :fetched_at, :ttl_seconds, :status, :content_type, :size_bytes, :source_id)
               ON CONFLICT(url) DO UPDATE SET
                 etag=excluded.etag, last_modified=excluded.last_modified, content_hash=excluded.content_hash,
                 fetched_at=excluded.fetched_at, ttl_seconds=excluded.ttl_seconds, status=excluded.status,
                 content_type=excluded.content_type, size_bytes=excluded.size_bytes, source_id=excluded.source_id
            """,
            vars(entry),
        )
        self._conn.commit()
        return entry

    def touch(self, url: str, *, ttl_seconds: Optional[int] = None) -> CacheEntry:
        """Refresh ``fetched_at`` (and optionally ``ttl_seconds``) without
        changing content — used on a ``304 Not Modified`` response."""
        entry = self.get(url)
        if entry is None:
            raise KeyError(f"no cache entry for {url!r} to touch")
        entry.fetched_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if ttl_seconds is not None:
            entry.ttl_seconds = ttl_seconds
        self._conn.execute(
            "UPDATE http_cache SET fetched_at = ?, ttl_seconds = ? WHERE url = ?",
            (entry.fetched_at, entry.ttl_seconds, url),
        )
        self._conn.commit()
        return entry

    def read_blob(self, entry: CacheEntry) -> bytes:
        return self._blob_path(entry.content_hash).read_bytes()

    def all_entries(self) -> List[CacheEntry]:
        rows = self._conn.execute("SELECT * FROM http_cache ORDER BY url").fetchall()
        return [_row_to_entry(r) for r in rows]

    def entries_for_source(self, source_id: str) -> List[CacheEntry]:
        rows = self._conn.execute(
            "SELECT * FROM http_cache WHERE source_id = ? ORDER BY url", (source_id,)
        ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def delete(self, url: str) -> None:
        self._conn.execute("DELETE FROM http_cache WHERE url = ?", (url,))
        self._conn.commit()
