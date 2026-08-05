"""Guarded bulk installation into a local BCDx36HP Sentinel workspace.

Sentinel stores Favorites Lists as plain ``f_NNNNNN.hpd`` files under
``FavoriteLists`` plus one global and one profile-specific ``f_list.cfg``.
This is distinct from HPE interchange: one HPE still represents one list.
The installer writes all selected generated lists in one preflighted,
backed-up application transaction so the user can reopen Sentinel with every
selected list already populated.
"""
from __future__ import annotations

import os
import re
import hashlib
import json
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from wasds150.hpe.builders import build_favorites_document
from wasds150.hpe.flist import entries, find_entry_by_filename, new_entry, parse_f_list, patch_entry, render
from wasds150.hpe.record import Record, RecordDocument, serialize_records
from wasds150.hpe.schema import F_LIST_SCHEMA, MAX_FAVORITES_LISTS
from wasds150.hpe.validation import require_valid_document
from wasds150.installer.backup import InstallerError, backup_card, verify_backup
from wasds150.installer.rollback import rollback_from_backup
from wasds150.installer.writer import _write_synced
from wasds150.models.catalog import FavoritesList


@dataclass(frozen=True)
class WorkspaceAssignment:
    slug: str
    favorite_key: str
    user_name: str
    index: int
    filename: str
    replacing: bool

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "favorite_key": self.favorite_key,
            "user_name": self.user_name,
            "index": self.index,
            "filename": self.filename,
            "replacing": self.replacing,
        }


@dataclass
class WorkspaceInstallResult:
    dry_run: bool
    workspace: Path
    profile_name: str
    assignments: List[WorkspaceAssignment] = field(default_factory=list)
    planned_writes: List[str] = field(default_factory=list)
    backup_path: Optional[Path] = None
    written_files: List[str] = field(default_factory=list)
    outcome: str = "planned"
    verified: bool = False
    plan_id: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "dry_run": self.dry_run,
            "workspace": str(self.workspace),
            "profile_name": self.profile_name,
            "assignments": [assignment.to_dict() for assignment in self.assignments],
            "planned_writes": list(self.planned_writes),
            "backup_path": str(self.backup_path) if self.backup_path else None,
            "written_files": list(self.written_files),
            "outcome": self.outcome,
            "verified": self.verified,
            "plan_id": self.plan_id,
            "warnings": list(self.warnings),
        }


def default_workspace_path() -> Path:
    return Path.home() / "Documents" / "Uniden" / "BCDx36HP"


def discover_profiles(workspace: Path) -> List[str]:
    profile_root = Path(workspace) / "Profile"
    if not profile_root.is_dir():
        return []
    return sorted(path.name for path in profile_root.iterdir() if path.is_dir() and (path / "profile.cfg").is_file())


def confirmation_phrase(profile_name: str) -> str:
    return f"IMPORT {profile_name}"


def _validate_workspace(workspace: Path, profile_name: str) -> Tuple[Path, Path, Path]:
    workspace = Path(workspace)
    if not profile_name or Path(profile_name).name != profile_name or profile_name in (".", ".."):
        raise InstallerError("invalid Sentinel profile name")
    favorites_dir = workspace / "FavoriteLists"
    global_index = favorites_dir / "f_list.cfg"
    profile_dir = workspace / "Profile" / profile_name
    profile_index = profile_dir / "f_list.cfg"
    if workspace.is_symlink() or workspace.name != "BCDx36HP" or not favorites_dir.is_dir() or not profile_dir.is_dir():
        raise InstallerError(f"{workspace} is not a BCDx36HP Sentinel workspace/profile")
    if not global_index.is_file() or not profile_index.is_file() or not (profile_dir / "profile.cfg").is_file():
        raise InstallerError("Sentinel workspace is missing f_list.cfg or profile.cfg")
    for path in (favorites_dir, profile_dir, global_index, profile_index):
        if path.is_symlink():
            raise InstallerError(f"refusing symlinked Sentinel workspace path: {path}")
    for path in workspace.rglob("*"):
        if path.is_symlink():
            raise InstallerError(f"refusing Sentinel workspace containing a symlink: {path}")
    return favorites_dir, global_index, profile_index


@contextmanager
def _workspace_lock(workspace: Path):
    identity = hashlib.sha256(str(workspace.resolve()).casefold().encode("utf-8")).hexdigest()[:16]
    lock_path = Path(tempfile.gettempdir()) / f"wasds150-sentinel-{identity}.lock"
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise InstallerError(f"another Sentinel install is active (lock: {lock_path})") from exc
    try:
        os.write(fd, str(os.getpid()).encode("ascii"))
        os.close(fd)
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _field(record: Record, name: str) -> str:
    spec = F_LIST_SCHEMA.field_by_name(name)
    return record.get(spec.index - 1, "") or ""


def _index_from_filename(filename: str) -> Optional[int]:
    match = re.fullmatch(r"f_(\d{6})\.hpd", filename, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _display_name(favorite: FavoritesList) -> str:
    return f"{favorite.favorite_key} - {favorite.favorite_name}"


def _find_existing_generated(doc: RecordDocument, favorite_key: str) -> Optional[Record]:
    prefix = favorite_key.casefold() + " - "
    return next((record for record in entries(doc) if _field(record, "user_name").casefold().startswith(prefix)), None)


def _allocate_assignments(
    favorites: Sequence[FavoritesList],
    global_doc: RecordDocument,
    favorites_dir: Path,
) -> List[WorkspaceAssignment]:
    used = {
        index
        for record in entries(global_doc)
        for index in [_index_from_filename(_field(record, "filename"))]
        if index is not None
    }
    used.update(
        index
        for path in favorites_dir.glob("f_*.hpd")
        for index in [_index_from_filename(path.name)]
        if index is not None
    )
    assignments: List[WorkspaceAssignment] = []
    assigned_indices = set()
    for favorite in sorted(favorites, key=lambda item: item.favorite_key.casefold()):
        existing = _find_existing_generated(global_doc, favorite.favorite_key)
        index = _index_from_filename(_field(existing, "filename")) if existing is not None else None
        replacing = index is not None
        if index is None:
            index = next((candidate for candidate in range(MAX_FAVORITES_LISTS) if candidate not in used and candidate not in assigned_indices), None)
        if index is None or index in assigned_indices:
            raise InstallerError("not enough unique Sentinel Favorites List slots for this selection")
        assigned_indices.add(index)
        used.add(index)
        assignments.append(WorkspaceAssignment(
            slug=favorite.slug,
            favorite_key=favorite.favorite_key,
            user_name=_display_name(favorite),
            index=index,
            filename=f"f_{index:06d}.hpd",
            replacing=replacing,
        ))
    return assignments


def _patch_index(doc: RecordDocument, assignments: Sequence[WorkspaceAssignment]) -> RecordDocument:
    result = RecordDocument(records=list(doc.records), line_endings=list(doc.line_endings))
    for assignment in assignments:
        existing = find_entry_by_filename(result, assignment.filename)
        replacement = (
            patch_entry(existing, user_name=assignment.user_name, monitor="On")
            if existing is not None
            else new_entry(assignment.user_name, assignment.filename)
        )
        if existing is not None:
            result.records[result.records.index(existing)] = replacement
        else:
            result.records.append(replacement)
            result.line_endings.append("\r\n")
    return result


def _workspace_hpd_bytes(favorite: FavoritesList) -> bytes:
    document = build_favorites_document(favorite.systems)
    require_valid_document(document, context=favorite.favorite_key)
    records = list(document.records)
    endings = list(document.line_endings)
    if records and records[-1].tag == "File":
        records.pop()
        endings.pop()
    return serialize_records(RecordDocument(records=records, line_endings=endings)).encode("ascii")


def _prepare_install(
    workspace: Path,
    profile_name: str,
    favorites: Sequence[FavoritesList],
) -> Tuple[WorkspaceInstallResult, Dict[Path, bytes]]:
    favorites_dir, global_index, profile_index = _validate_workspace(workspace, profile_name)
    global_bytes = global_index.read_bytes()
    profile_bytes = profile_index.read_bytes()
    global_doc = parse_f_list(global_bytes.decode("ascii"))
    profile_doc = parse_f_list(profile_bytes.decode("ascii"))
    assignments = _allocate_assignments(favorites, global_doc, favorites_dir)
    by_slug = {favorite.slug: favorite for favorite in favorites}
    payloads: Dict[Path, bytes] = {
        favorites_dir / assignment.filename: _workspace_hpd_bytes(by_slug[assignment.slug])
        for assignment in assignments
    }
    payloads[global_index] = render(_patch_index(global_doc, assignments)).encode("ascii")
    payloads[profile_index] = render(_patch_index(profile_doc, assignments)).encode("ascii")
    fingerprint = {
        "workspace": str(workspace.resolve()),
        "profile": profile_name,
        "global_index": hashlib.sha256(global_bytes).hexdigest(),
        "profile_index": hashlib.sha256(profile_bytes).hexdigest(),
        "payloads": [
            (path.relative_to(workspace).as_posix(), hashlib.sha256(payload).hexdigest())
            for path, payload in payloads.items()
        ],
        "target_state": [
            (
                path.relative_to(workspace).as_posix(),
                hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
            )
            for path in payloads
        ],
    }
    plan_id = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode("utf-8")).hexdigest()
    result = WorkspaceInstallResult(
        dry_run=True,
        workspace=workspace,
        profile_name=profile_name,
        assignments=assignments,
        planned_writes=[path.relative_to(workspace).as_posix() for path in payloads],
        plan_id=plan_id,
        warnings=["Close Sentinel before executing; reopen it only after the transaction completes."],
    )
    return result, payloads


def install_selected_favorites(
    workspace: Path,
    profile_name: str,
    favorites: Sequence[FavoritesList],
    *,
    backup_dir: Path,
    execute: bool = False,
    confirm: str = "",
    expected_plan_id: str = "",
    allow_replacements: bool = False,
) -> WorkspaceInstallResult:
    """Plan or install selected generated lists into one Sentinel profile.

    All inputs are validated and serialized before a real operation takes one
    verified workspace backup. Detected failures trigger restoration from
    that backup. Sentinel must be closed while executing.
    """
    if not favorites:
        raise InstallerError("select at least one populated Favorites List")
    if len({favorite.slug for favorite in favorites}) != len(favorites):
        raise InstallerError("duplicate Favorites List selection")
    if any(not favorite.enabled or not favorite.systems for favorite in favorites):
        raise InstallerError("every selected Favorites List must be enabled and populated")

    workspace = Path(workspace)
    backup_dir = Path(backup_dir)
    _validate_workspace(workspace, profile_name)
    try:
        backup_dir.resolve().relative_to(workspace.resolve())
    except ValueError:
        pass
    else:
        raise InstallerError("backup directory must be outside the Sentinel workspace")
    if not execute:
        result, _ = _prepare_install(workspace, profile_name, favorites)
        return result
    if confirm != confirmation_phrase(profile_name):
        raise InstallerError(f"confirmation phrase mismatch; expected {confirmation_phrase(profile_name)!r}")
    if not expected_plan_id:
        raise InstallerError("execute requires the plan_id returned by a fresh dry run")

    with _workspace_lock(workspace):
        result, payloads = _prepare_install(workspace, profile_name, favorites)
        if result.plan_id != expected_plan_id:
            raise InstallerError("Sentinel workspace or selection changed after planning; run Plan again")
        replacement_count = sum(assignment.replacing for assignment in result.assignments)
        if replacement_count and not allow_replacements:
            raise InstallerError(
                f"plan replaces {replacement_count} existing entries; explicitly approve replacements"
            )
        backup_path = backup_card(workspace.parent, backup_dir, subtree=workspace.name)
        issues = verify_backup(backup_path)
        if issues:
            raise InstallerError("mandatory Sentinel workspace backup failed verification: " + "; ".join(issues))
        result.backup_path = backup_path

        try:
            _validate_workspace(workspace, profile_name)
            for path, payload in payloads.items():
                if path.exists() and path.is_symlink():
                    raise InstallerError(f"refusing symlinked write target: {path}")
                _write_synced(path, payload)
                result.written_files.append(path.relative_to(workspace).as_posix())
            mismatches = [path for path, payload in payloads.items() if path.read_bytes() != payload]
            if mismatches:
                raise InstallerError("post-write verification failed: " + ", ".join(str(path) for path in mismatches))
            result.outcome = "committed"
            result.verified = True
            result.dry_run = False
            return result
        except Exception as exc:
            try:
                rollback_from_backup(workspace.parent, backup_path)
            except Exception as rollback_exc:
                result.outcome = "rollback_failed"
                raise InstallerError(f"Sentinel install failed ({exc}); automatic rollback also failed ({rollback_exc})") from rollback_exc
            result.outcome = "rolled_back"
            raise InstallerError(f"Sentinel install failed and was rolled back: {exc}") from exc
