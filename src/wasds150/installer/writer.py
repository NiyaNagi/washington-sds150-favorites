"""SD-card write orchestration: the full documented safety sequence.

Order matters and is exactly (see ``NOTICE.md``/research report):

1. Verify the target looks like an SDS150 card (``BCDx36HP`` marker) and
   every write/delete target is on the strict path allow-list
   (:mod:`wasds150.installer.paths`).
2. Dry-run by default — report the plan, touch nothing.
3. Require an explicit typed confirmation phrase before any real write.
4. Take a **mandatory** full-``BCDx36HP`` backup (abort if it fails).
5. Write the new/updated ``.hpd`` file as **plain** tab-delimited text
   (CRLF, no gzip/XOR — that obfuscation is only for `.hpe` *export*
   files, never for on-card `.hpd` files) and ``fsync`` it.
6. Patch (never regenerate wholesale) the existing ``f_list.cfg`` entry —
   only ``UserName``/``Monitor`` change; every other of its 112 fields is
   preserved verbatim — or synthesize a fresh entry only if this is a
   brand-new list. ``fsync`` it too.
7. Delete ``app_data.cfg`` (mandatory after any program-data write, so the
   scanner doesn't misbehave on resume).
8. Post-write verification: re-read everything just written and confirm it
   matches what was intended; confirm ``app_data.cfg`` is gone.

``HPDB/``, ``profile.cfg``, and ``discvery.cfg`` are never read or written
by this module.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from wasds150.hpe.flist import find_entry_by_filename, new_entry, parse_f_list, patch_entry, render
from wasds150.hpe.record import Record, RecordDocument, new_document, serialize_records
from wasds150.hpe.validation import HpeValidationError, require_valid_document
from wasds150.installer.backup import InstallerError, backup_card, verify_backup
from wasds150.installer.confirm import confirm_phrase_for, verify_confirmation
from wasds150.installer.paths import (
    APP_DATA_CFG,
    F_LIST_CFG,
    FAVORITES_LISTS_DIR,
    hpd_filename,
    is_allowed_delete_path,
    is_sds150_card,
    is_within_allowed_write_path,
)


@dataclass
class WriteResult:
    dry_run: bool
    planned_writes: List[str] = field(default_factory=list)
    planned_deletes: List[str] = field(default_factory=list)
    backup_path: Optional[Path] = None
    written_files: List[str] = field(default_factory=list)
    deleted_files: List[str] = field(default_factory=list)
    verified: bool = False
    warnings: List[str] = field(default_factory=list)


def _write_synced(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, candidate_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    candidate = Path(candidate_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(candidate, path)
        _fsync_dir_best_effort(path.parent)
    finally:
        if candidate.exists():
            candidate.unlink()


def _fsync_dir_best_effort(directory: Path) -> None:
    """fsync the containing directory too (durability of the directory
    entry itself on POSIX filesystems). Windows has no directory-fd concept
    for this, so failures here are swallowed rather than fatal."""
    try:
        fd = os.open(str(directory), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def plan_write(mount_point: Path, index: int) -> Tuple[Path, Path]:
    """Resolve (and allow-list-validate) the two paths a favorites-list
    write touches: the ``.hpd`` file and ``f_list.cfg``."""
    mount_point = Path(mount_point)
    target_hpd = mount_point / FAVORITES_LISTS_DIR / hpd_filename(index)
    target_flist = mount_point / F_LIST_CFG
    for target in (target_hpd, target_flist):
        if not is_within_allowed_write_path(mount_point, target):
            raise InstallerError(f"refusing to write outside the allow-listed favorites_lists path: {target}")
    return target_hpd, target_flist


def write_favorites_list(
    mount_point: Path,
    *,
    index: int,
    document: RecordDocument,
    user_name: str,
    backup_dir: Path,
    confirm_phrase: Optional[str] = None,
    dry_run: bool = True,
) -> WriteResult:
    """Write one Favorites List (``document``, from
    :mod:`wasds150.hpe.builders`) to ``mount_point`` at favorites-index
    ``index``, following the full documented safety sequence.

    Always dry-run unless ``dry_run=False`` **and** ``confirm_phrase``
    matches :func:`wasds150.installer.confirm.confirm_phrase_for`.
    """
    mount_point = Path(mount_point)
    if not is_sds150_card(mount_point):
        raise InstallerError(f"{mount_point} does not look like an SDS150 card (no BCDx36HP directory)")
    try:
        require_valid_document(document, context="SD-card Favorites List")
    except HpeValidationError as exc:
        raise InstallerError(str(exc)) from exc

    target_hpd, target_flist = plan_write(mount_point, index)
    planned_writes = [str(target_hpd.relative_to(mount_point)), str(target_flist.relative_to(mount_point))]
    planned_deletes = [APP_DATA_CFG] if (mount_point / APP_DATA_CFG).exists() else []

    if dry_run:
        return WriteResult(
            dry_run=True,
            planned_writes=planned_writes,
            planned_deletes=planned_deletes,
            warnings=["dry run: no changes were made"],
        )

    if not verify_confirmation(confirm_phrase or "", mount_point):
        raise InstallerError(
            f"confirmation phrase mismatch; expected {confirm_phrase_for(mount_point)!r} "
            "(dry_run=False requires an exact match — this is the explicit-confirmation gate)"
        )

    # Mandatory backup — the entire point of running this before any write.
    backup_path = backup_card(mount_point, backup_dir)
    backup_issues = verify_backup(backup_path)
    if backup_issues:
        raise InstallerError(
            "mandatory pre-write backup failed verification: " + "; ".join(backup_issues)
        )

    # 1) Write the .hpd file as plain text (NOT gzip/XOR — that's only for
    #    exported .hpe files, never for on-card .hpd files).
    hpd_bytes = serialize_records(document).encode("ascii")
    _write_synced(target_hpd, hpd_bytes)

    # 2) Patch (or create) the f_list.cfg entry, preserving every other
    #    field verbatim for an existing entry.
    filename = target_hpd.name
    if target_flist.exists():
        flist_doc = parse_f_list(target_flist.read_bytes().decode("ascii"))
    else:
        flist_doc = new_document(
            [Record(tag="TargetModel", fields=["BCDx36HP"]), Record(tag="FormatVersion", fields=["1.00"])]
        )
    existing = find_entry_by_filename(flist_doc, filename)
    if existing is not None:
        position = flist_doc.records.index(existing)
        flist_doc.records[position] = patch_entry(existing, user_name=user_name, monitor="On")
    else:
        flist_doc.records.append(new_entry(user_name, filename))
        flist_doc.line_endings.append("\r\n")
    flist_bytes = render(flist_doc).encode("ascii")
    _write_synced(target_flist, flist_bytes)

    # 3) Delete app_data.cfg — mandatory after any program-data write.
    app_data_path = mount_point / APP_DATA_CFG
    deleted: List[str] = []
    if app_data_path.exists():
        if not is_allowed_delete_path(mount_point, app_data_path):  # pragma: no cover - defensive
            raise InstallerError(f"refusing to delete outside the allow-list: {app_data_path}")
        app_data_path.unlink()
        _fsync_dir_best_effort(app_data_path.parent)
        deleted.append(APP_DATA_CFG)

    # 4) Post-write verification.
    warnings: List[str] = []
    verified = True
    if target_hpd.read_bytes() != hpd_bytes:
        verified = False
        warnings.append(f"post-write verification failed: {target_hpd} does not match what was written")
    if target_flist.read_bytes() != flist_bytes:
        verified = False
        warnings.append(f"post-write verification failed: {target_flist} does not match what was written")
    if app_data_path.exists():
        verified = False
        warnings.append("app_data.cfg still exists after deletion — resume state may be stale")

    return WriteResult(
        dry_run=False,
        planned_writes=planned_writes,
        planned_deletes=planned_deletes,
        backup_path=backup_path,
        written_files=planned_writes,
        deleted_files=deleted,
        verified=verified,
        warnings=warnings,
    )
