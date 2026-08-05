"""Restore a card's ``BCDx36HP`` tree from a :mod:`wasds150.installer.backup`
archive, verifying each restored file's checksum against the backup's own
manifest before reporting success.
"""
from __future__ import annotations

import hashlib
import os
import zipfile
from pathlib import Path
from typing import List

from wasds150.installer.backup import read_backup_manifest


def rollback_from_backup(mount_point: Path, backup_path: Path, *, remove_extraneous: bool = True) -> List[str]:
    """Restore every file recorded in ``backup_path``'s manifest back onto
    ``mount_point``, fsyncing each write, and verify the restored bytes
    match the manifest's recorded checksum. Returns the list of restored
    relative paths.

    If ``remove_extraneous`` (default), also deletes any file that exists
    under the backed-up subtree on the card but was **not** part of the
    backup — e.g. a ``.hpd``/``f_list.cfg`` written after the backup was
    taken — so the card is restored to the exact pre-write state, not just
    "the old files are back but new ones also remain".

    Raises :class:`ValueError` if any restored file's checksum doesn't
    match the manifest (the backup itself may be corrupt).
    """
    manifest = read_backup_manifest(backup_path)
    mount_point = Path(mount_point)
    restored: List[str] = []
    backed_up_paths = {entry["path"] for entry in manifest["files"]}

    with zipfile.ZipFile(backup_path) as zf:
        for entry in manifest["files"]:
            rel_path = entry["path"]
            data = zf.read(rel_path)
            actual = hashlib.sha256(data).hexdigest()
            if actual != entry["sha256"]:
                raise ValueError(f"backup entry {rel_path!r} failed checksum verification; refusing to restore it")

            target = mount_point / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            restored.append(rel_path)

    if remove_extraneous:
        subtree_dir = mount_point / manifest["subtree"]
        if subtree_dir.is_dir():
            for path in sorted(subtree_dir.rglob("*")):
                if not path.is_file():
                    continue
                rel_path = path.relative_to(mount_point).as_posix()
                if rel_path not in backed_up_paths:
                    path.unlink()

    return restored
