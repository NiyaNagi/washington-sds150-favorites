"""Restore the profile to a prior snapshot's state.

Basic/local rollback: overwrites ``profile.json`` with the profile stored in
a chosen snapshot, after saving a timestamped backup copy of whatever
profile is currently active (so a rollback can itself be undone by hand).
"""
from __future__ import annotations

import datetime
import shutil
from pathlib import Path

from wasds150.history.snapshots import SnapshotStore


def rollback_profile(profile_path: Path, history_dir: Path, snap_id: str) -> Path:
    store = SnapshotStore(history_dir)
    restored_profile = store.load_profile(snap_id)

    if profile_path.exists():
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = profile_path.with_name(f"profile.pre-rollback-{timestamp}.json")
        shutil.copy2(profile_path, backup_path)

    restored_profile.save(profile_path)
    return profile_path
