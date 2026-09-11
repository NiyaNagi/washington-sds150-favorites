"""Everything RepeaterBook returns, kept apart so it can be deleted for certain.

The shared HTTP cache stores blobs by content hash and shares them across
URLs, so deleting one URL's index row leaves the body on disk. That is fine
for public data and wrong here. This store lives in its own directory::

    <home>/state/repeaterbook/
        data.db      raw-response index, staging rows, applied records,
                     request ledger, generated report paths
        raw/         one file per raw response
        reports/     review reports
        limits.json  rate-limit window and lockouts (timestamps and token
                     fingerprints only)
        action.lock  held while a refresh is in flight

**Delete All** removes ``data.db``, ``raw/``, ``reports/`` and every report
written elsewhere that was registered here. It keeps ``limits.json``: those
entries hold no RepeaterBook data, expire on their own within 24 hours (a 429
lockout when it lapses), and deleting them would let a delete reset the
request budget.

Every method takes the current time from its caller, so retention is tested
with an injected clock.
"""
from __future__ import annotations

import datetime
import json
import os
import shutil
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from wasds150.sources.repeaterbook import policy

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_responses (
    id INTEGER PRIMARY KEY,
    region TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    blob TEXT NOT NULL,
    size_bytes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS staging (
    id INTEGER PRIMARY KEY,
    action_id TEXT NOT NULL,
    rb_key TEXT NOT NULL,
    region TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    record TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
);
CREATE TABLE IF NOT EXISTS derived (
    rb_key TEXT PRIMARY KEY,
    record TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    reviewed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ledger (
    id INTEGER PRIMARY KEY,
    token_fp TEXT NOT NULL,
    region TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    status INTEGER,
    outcome TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reports (
    path TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);
"""

_PROCESS_LOCK = threading.Lock()
_STALE_LOCK_SECONDS = 15 * 60


class ActionInProgress(RuntimeError):
    """Another RepeaterBook refresh is running; requests are never parallel."""


def iso(moment: datetime.datetime) -> str:
    return moment.astimezone(datetime.timezone.utc).isoformat()


def parse_iso(text: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(text)


class RepeaterBookStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.db_path = self.root / "data.db"
        self.raw_dir = self.root / "raw"
        self.reports_dir = self.root / "reports"
        self.limits_path = self.root / "limits.json"
        self.lock_path = self.root / "action.lock"

    @classmethod
    def for_config(cls, config) -> "RepeaterBookStore":
        return cls(config.state_dir / "repeaterbook")

    def exists(self) -> bool:
        return self.root.exists()

    # -- database -------------------------------------------------------------
    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        """A short-lived connection, so nothing holds the file open and a
        delete on Windows cannot fail on a lingering handle."""
        self.root.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            conn.executescript(SCHEMA)
            yield conn
            conn.commit()
        finally:
            conn.close()

    # -- raw responses ----------------------------------------------------------
    def put_raw(self, region: str, body: bytes, fetched_at: datetime.datetime) -> int:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        blob = f"{uuid.uuid4().hex}.json"
        (self.raw_dir / blob).write_bytes(body)
        with self._db() as conn:
            cursor = conn.execute(
                "INSERT INTO raw_responses (region, fetched_at, blob, size_bytes) VALUES (?, ?, ?, ?)",
                (region, iso(fetched_at), blob, len(body)),
            )
            return int(cursor.lastrowid)

    def latest_raw_meta(self, region: str) -> Optional[Dict[str, Any]]:
        if not self.db_path.exists():
            return None
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM raw_responses WHERE region = ? ORDER BY fetched_at DESC LIMIT 1", (region,)
            ).fetchone()
        return dict(row) if row else None

    def latest_fresh_raw(self, region: str, now: datetime.datetime) -> Optional[Dict[str, Any]]:
        meta = self.latest_raw_meta(region)
        if meta is None or now - parse_iso(meta["fetched_at"]) >= policy.RAW_FRESH:
            return None
        meta["body"] = (self.raw_dir / meta["blob"]).read_bytes()
        return meta

    # -- staging ------------------------------------------------------------------
    def stage(self, action_id: str, candidates: List[Dict[str, Any]]) -> None:
        with self._db() as conn:
            conn.executemany(
                "INSERT INTO staging (action_id, rb_key, region, fetched_at, record) VALUES (?, ?, ?, ?, ?)",
                [
                    (action_id, c["rb_key"], c["region"], c["retrieved_at"], json.dumps(c, sort_keys=True))
                    for c in candidates
                ],
            )

    def latest_action_id(self) -> Optional[str]:
        if not self.db_path.exists():
            return None
        with self._db() as conn:
            row = conn.execute("SELECT action_id FROM staging ORDER BY id DESC LIMIT 1").fetchone()
        return row["action_id"] if row else None

    def staged(self, action_id: Optional[str] = None, status: Optional[str] = "pending") -> List[Dict[str, Any]]:
        if not self.db_path.exists():
            return []
        clauses, args = [], []
        if action_id:
            clauses.append("action_id = ?")
            args.append(action_id)
        if status:
            clauses.append("status = ?")
            args.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._db() as conn:
            rows = conn.execute(f"SELECT * FROM staging {where} ORDER BY id", args).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["record"] = json.loads(item["record"])
            result.append(item)
        return result

    def mark_staged(self, ids: List[int], status: str) -> None:
        if not ids:
            return
        with self._db() as conn:
            conn.executemany("UPDATE staging SET status = ? WHERE id = ?", [(status, i) for i in ids])

    # -- applied (derived) records -------------------------------------------------
    def upsert_derived(self, rb_key: str, record: Dict[str, Any], *, retrieved_at: str, reviewed_at: str) -> None:
        with self._db() as conn:
            conn.execute(
                """INSERT INTO derived (rb_key, record, retrieved_at, reviewed_at) VALUES (?, ?, ?, ?)
                   ON CONFLICT(rb_key) DO UPDATE SET record=excluded.record,
                     retrieved_at=excluded.retrieved_at, reviewed_at=excluded.reviewed_at""",
                (rb_key, json.dumps(record, sort_keys=True), retrieved_at, reviewed_at),
            )

    def derived(self) -> List[Dict[str, Any]]:
        if not self.db_path.exists():
            return []
        with self._db() as conn:
            rows = conn.execute("SELECT * FROM derived ORDER BY rb_key").fetchall()
        result = []
        for row in rows:
            item = json.loads(row["record"])
            item.update(retrieved_at=row["retrieved_at"], reviewed_at=row["reviewed_at"])
            result.append(item)
        return result

    # -- request ledger (history) -----------------------------------------------------
    def ledger_add(self, token_fp: str, region: str, requested_at: datetime.datetime, status: Optional[int], outcome: str) -> None:
        with self._db() as conn:
            conn.execute(
                "INSERT INTO ledger (token_fp, region, requested_at, status, outcome) VALUES (?, ?, ?, ?, ?)",
                (token_fp, region, iso(requested_at), status, outcome),
            )

    def ledger(self) -> List[Dict[str, Any]]:
        if not self.db_path.exists():
            return []
        with self._db() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM ledger ORDER BY id").fetchall()]

    # -- reports ---------------------------------------------------------------------
    def register_report(self, path: Path, created_at: datetime.datetime) -> None:
        with self._db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO reports (path, created_at) VALUES (?, ?)",
                (str(Path(path).resolve()), iso(created_at)),
            )

    def reports(self) -> List[Dict[str, Any]]:
        if not self.db_path.exists():
            return []
        with self._db() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM reports ORDER BY path").fetchall()]

    # -- rate-limit window and lockouts -------------------------------------------------
    def _load_limits(self) -> Dict[str, List[Dict[str, Any]]]:
        if not self.limits_path.exists():
            return {"requests": [], "blocks": []}
        data = json.loads(self.limits_path.read_text(encoding="utf-8"))
        return {"requests": list(data.get("requests", [])), "blocks": list(data.get("blocks", []))}

    def _save_limits(self, data: Dict[str, List[Dict[str, Any]]]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.limits_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.limits_path)

    def record_request(self, token_fp: str, region: str, at: datetime.datetime) -> None:
        data = self._load_limits()
        data["requests"].append({"fp": token_fp, "region": region, "at": iso(at)})
        self._save_limits(data)

    def requests_since(self, token_fp: str, since: datetime.datetime) -> List[Dict[str, Any]]:
        return [
            r for r in self._load_limits()["requests"]
            if r["fp"] == token_fp and parse_iso(r["at"]) > since
        ]

    def last_request(self, token_fp: str, region: str) -> Optional[datetime.datetime]:
        times = [
            parse_iso(r["at"]) for r in self._load_limits()["requests"]
            if r["fp"] == token_fp and r["region"] == region
        ]
        return max(times) if times else None

    def set_block(self, token_fp: str, kind: str, until: Optional[datetime.datetime], reason: str) -> None:
        data = self._load_limits()
        data["blocks"] = [b for b in data["blocks"] if not (b["fp"] == token_fp and b["kind"] == kind)]
        data["blocks"].append({"fp": token_fp, "kind": kind, "until": iso(until) if until else None, "reason": reason})
        self._save_limits(data)

    def clear_block(self, token_fp: str, kind: str) -> bool:
        data = self._load_limits()
        kept = [b for b in data["blocks"] if not (b["fp"] == token_fp and b["kind"] == kind)]
        changed = len(kept) != len(data["blocks"])
        data["blocks"] = kept
        if changed:
            self._save_limits(data)
        return changed

    def active_blocks(self, token_fp: str, now: datetime.datetime) -> List[Dict[str, Any]]:
        return [
            b for b in self._load_limits()["blocks"]
            if b["fp"] == token_fp and (b["until"] is None or parse_iso(b["until"]) > now)
        ]

    # -- one refresh at a time ------------------------------------------------------------
    @contextmanager
    def action_lock(self, now: datetime.datetime) -> Iterator[None]:
        """Held for a whole refresh: a thread lock within this process and an
        exclusive lock file across processes. A second refresh fails at once
        rather than waiting."""
        if not _PROCESS_LOCK.acquire(blocking=False):
            raise ActionInProgress("another RepeaterBook refresh is already running")
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            fd = self._open_lock_file()
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(f"{os.getpid()} {iso(now)}\n")
            try:
                yield
            finally:
                try:
                    self.lock_path.unlink()
                except FileNotFoundError:
                    pass
        finally:
            _PROCESS_LOCK.release()

    def _open_lock_file(self) -> int:
        for _ in range(2):
            try:
                return os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                age = time.time() - self.lock_path.stat().st_mtime
                if age < _STALE_LOCK_SECONDS:
                    raise ActionInProgress("another RepeaterBook refresh is already running") from None
                self.lock_path.unlink()  # left behind by a crashed process
        raise ActionInProgress("could not take the RepeaterBook refresh lock")

    # -- retention ---------------------------------------------------------------------------
    def purge(self, now: datetime.datetime) -> Dict[str, int]:
        """Apply every retention rule for ``now``. Safe to call often."""
        counts = {"raw": 0, "staging": 0, "derived": 0, "ledger": 0, "reports": 0, "limits": 0}
        if not self.exists():
            return counts
        if self.db_path.exists():
            raw_cut = iso(now - policy.RAW_DELETE_AFTER)
            with self._db() as conn:
                for row in conn.execute("SELECT id, blob FROM raw_responses WHERE fetched_at <= ?", (raw_cut,)).fetchall():
                    (self.raw_dir / row["blob"]).unlink(missing_ok=True)
                    conn.execute("DELETE FROM raw_responses WHERE id = ?", (row["id"],))
                    counts["raw"] += 1
                counts["staging"] = conn.execute(
                    "DELETE FROM staging WHERE fetched_at <= ?", (iso(now - policy.STAGING_DELETE_AFTER),)
                ).rowcount
                counts["derived"] = conn.execute(
                    "DELETE FROM derived WHERE reviewed_at <= ?", (iso(now - policy.DERIVED_DELETE_AFTER),)
                ).rowcount
                counts["ledger"] = conn.execute(
                    "DELETE FROM ledger WHERE requested_at <= ?", (iso(now - policy.LEDGER_DELETE_AFTER),)
                ).rowcount
                report_cut = iso(now - policy.DERIVED_DELETE_AFTER)
                for row in conn.execute("SELECT path FROM reports WHERE created_at <= ?", (report_cut,)).fetchall():
                    Path(row["path"]).unlink(missing_ok=True)
                    conn.execute("DELETE FROM reports WHERE path = ?", (row["path"],))
                    counts["reports"] += 1
        if self.limits_path.exists():
            data = self._load_limits()
            keep_after = now - max(policy.REQUEST_WINDOW, policy.REGION_COOLDOWN)
            requests = [r for r in data["requests"] if parse_iso(r["at"]) > keep_after]
            blocks = [b for b in data["blocks"] if b["until"] is None or parse_iso(b["until"]) > now]
            counts["limits"] = (len(data["requests"]) - len(requests)) + (len(data["blocks"]) - len(blocks))
            if counts["limits"]:
                self._save_limits({"requests": requests, "blocks": blocks})
        return counts

    def delete_all(self) -> Dict[str, int]:
        """Delete All RepeaterBook Data. See the module docstring for what is kept."""
        counts = {"raw": 0, "staging": 0, "derived": 0, "ledger": 0, "reports": 0}
        if self.db_path.exists():
            with self._db() as conn:
                for table, key in (("raw_responses", "raw"), ("staging", "staging"), ("derived", "derived"), ("ledger", "ledger")):
                    counts[key] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                reports = [row["path"] for row in conn.execute("SELECT path FROM reports").fetchall()]
            for path in reports:
                Path(path).unlink(missing_ok=True)
            counts["reports"] = len(reports)
            for suffix in ("", "-journal", "-wal", "-shm"):
                Path(str(self.db_path) + suffix).unlink(missing_ok=True)
        for directory in (self.raw_dir, self.reports_dir):
            if directory.exists():
                shutil.rmtree(directory)
        return counts
