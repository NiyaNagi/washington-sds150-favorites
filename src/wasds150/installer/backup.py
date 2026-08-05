"""Mandatory pre-write SD-card backup.

Archives the entire ``BCDx36HP`` tree (favorites, HPDB, configs — not just
the files about to be written) into a single timestamped zip, with a
sha256 manifest recorded as an entry inside that same zip (avoiding any
fragile sidecar-filename correlation with :mod:`wasds150.installer.rollback`).
Every write path in :mod:`wasds150.installer.writer` calls this before
touching the card; a failed backup aborts the write.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List

from wasds150.installer.paths import BCDX36HP_DIR

#: Never collides with a real on-card path (which never starts with '_').
MANIFEST_ENTRY_NAME = "_wasds150_backup_manifest.json"


class InstallerError(Exception):
    """Base class for all SD-card installer errors."""


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def backup_card(mount_point: Path, backup_dir: Path, *, subtree: str = BCDX36HP_DIR) -> Path:
    """Back up ``<mount_point>/<subtree>`` (default: the whole ``BCDx36HP``
    tree) into a new zip under ``backup_dir``. Returns the zip's path.

    Raises :class:`InstallerError` if ``<mount_point>/<subtree>`` doesn't
    exist (i.e. this doesn't look like an SDS150 card).
    """
    mount_point = Path(mount_point)
    source_dir = mount_point / subtree
    if not source_dir.is_dir():
        raise InstallerError(f"{source_dir} not found; refusing to back up a non-SDS150 volume")

    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    archive_path = backup_dir / f"sdcard-backup-{timestamp}.zip"

    manifest: Dict[str, Any] = {
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "mount_point": str(mount_point),
        "subtree": subtree,
        "files": [],
    }

    files = sorted(p for p in source_dir.rglob("*") if p.is_file())
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            arcname = file_path.relative_to(mount_point).as_posix()
            zf.write(file_path, arcname=arcname)
            manifest["files"].append({"path": arcname, "sha256": _sha256_of_file(file_path)})
        zf.writestr(MANIFEST_ENTRY_NAME, json.dumps(manifest, indent=2, sort_keys=True))

    return archive_path


def read_backup_manifest(backup_path: Path) -> Dict[str, Any]:
    with zipfile.ZipFile(backup_path) as zf:
        return json.loads(zf.read(MANIFEST_ENTRY_NAME).decode("utf-8"))


def verify_backup(backup_path: Path) -> List[str]:
    """Check every file recorded in the backup's manifest still hashes the
    same inside the zip (integrity check of the backup itself, independent
    of the live card). Returns a list of problems (empty == OK)."""
    issues: List[str] = []
    manifest = read_backup_manifest(backup_path)
    with zipfile.ZipFile(backup_path) as zf:
        names = set(zf.namelist())
        for entry in manifest["files"]:
            if entry["path"] not in names:
                issues.append(f"manifest lists {entry['path']!r} but it is missing from the archive")
                continue
            data = zf.read(entry["path"])
            actual = hashlib.sha256(data).hexdigest()
            if actual != entry["sha256"]:
                issues.append(f"{entry['path']}: checksum mismatch (backup may be corrupt)")
    return issues
