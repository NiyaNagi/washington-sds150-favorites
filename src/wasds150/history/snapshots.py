"""Append-only snapshot history.

Every successful ``wasds150 generate`` commits a snapshot: the profile that
produced it, plus the resulting hashes/counts. Snapshots are simple
sequentially-numbered JSON files under the user's state directory — no
external dependency, human-inspectable, and easy to restore from (see
:mod:`wasds150.history.rollback`).

This is deliberately *not* a merge-aware history (no branches/conflicts) —
it is the "basic" snapshot/rollback capability; reconciling a rollback with
newer upstream facts is the future merge engine's job.
"""
from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from wasds150.generate.pipeline import GeneratedResult
from wasds150.models.profile import Profile


@dataclass
class SnapshotMeta:
    id: str
    created_at: str
    message: str
    catalog_hash: str
    profile_hash: str
    content_hash: str
    counts: Dict[str, int] = field(default_factory=dict)


class SnapshotStore:
    def __init__(self, history_dir: Path):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def _snapshot_path(self, snap_id: str) -> Path:
        return self.history_dir / f"{snap_id}.json"

    def _existing_ids(self) -> List[str]:
        return sorted(p.stem for p in self.history_dir.glob("*.json") if p.stem.isdigit())

    def _next_id(self) -> str:
        ids = self._existing_ids()
        n = int(ids[-1]) if ids else 0
        return f"{n + 1:04d}"

    def commit(self, profile: Profile, result: GeneratedResult, message: str = "") -> SnapshotMeta:
        snap_id = self._next_id()
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        data: Dict[str, Any] = {
            "id": snap_id,
            "created_at": created_at,
            "message": message,
            "catalog_hash": result.catalog_hash,
            "profile_hash": result.profile_hash,
            "content_hash": result.content_hash,
            "counts": result.counts,
            "profile": profile.to_dict(),
        }
        self._snapshot_path(snap_id).write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return SnapshotMeta(
            id=snap_id,
            created_at=created_at,
            message=message,
            catalog_hash=result.catalog_hash,
            profile_hash=result.profile_hash,
            content_hash=result.content_hash,
            counts=result.counts,
        )

    def list(self) -> List[SnapshotMeta]:
        metas = []
        for snap_id in self._existing_ids():
            data = json.loads(self._snapshot_path(snap_id).read_text(encoding="utf-8"))
            metas.append(
                SnapshotMeta(
                    id=data["id"],
                    created_at=data["created_at"],
                    message=data.get("message", ""),
                    catalog_hash=data["catalog_hash"],
                    profile_hash=data["profile_hash"],
                    content_hash=data["content_hash"],
                    counts=data.get("counts", {}),
                )
            )
        return metas

    def load_raw(self, snap_id: str) -> Dict[str, Any]:
        path = self._snapshot_path(snap_id)
        if not path.exists():
            raise KeyError(f"no such snapshot: {snap_id!r}")
        return json.loads(path.read_text(encoding="utf-8"))

    def load_profile(self, snap_id: str) -> Profile:
        data = self.load_raw(snap_id)
        return Profile.from_dict(data["profile"])

    def latest(self) -> Optional[SnapshotMeta]:
        metas = self.list()
        return metas[-1] if metas else None
