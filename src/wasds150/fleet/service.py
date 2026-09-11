"""Fleet operations shared by the CLI, the web UI and the update wizard:
which radios are stale, write each radio's programming file, and record that
a radio was programmed.

Nothing here talks to a radio or a vendor program; that is the wizard's job
(:mod:`wasds150.fleet.update`). Everything here is callable from a test with
nothing but an :class:`~wasds150.appctx.AppContext`.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from wasds150.appctx import AppContext
from wasds150.fleet.registry import FLEET, get_fleet_radio
from wasds150.fleet.settings import FleetSettings
from wasds150.fleet.state import (
    FleetState,
    RadioStatus,
    RadioSyncRecord,
    catalog_hashes,
    now_iso,
    plan_fingerprint,
    radio_status,
    sha256_of_path,
)
from wasds150.models.catalog import FavoritesList
from wasds150.plan.service import DEFAULT_OUT_DIR, export_plan
from wasds150.plans import get_plan


@dataclass
class FleetExport:
    radio_id: str
    plan_id: str
    target_id: str
    #: The programming file, or the bundle directory.
    path: Path
    report_path: Optional[Path]
    rows: int
    sha256: str
    files: List[Path] = field(default_factory=list)
    copies: List[Path] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "radio_id": self.radio_id,
            "plan_id": self.plan_id,
            "target_id": self.target_id,
            "path": str(self.path),
            "report_path": str(self.report_path) if self.report_path else None,
            "rows": self.rows,
            "sha256": self.sha256,
            "files": [str(p) for p in self.files],
            "copies": [str(p) for p in self.copies],
            "warnings": list(self.warnings),
        }


def load_settings(ctx: AppContext) -> FleetSettings:
    return FleetSettings.load(ctx.config.fleet_settings_path)


def load_state(ctx: AppContext) -> FleetState:
    return FleetState.load(ctx.config.fleet_state_path)


def current_plan_fingerprint(radio_id: str) -> str:
    radio = get_fleet_radio(radio_id)
    return plan_fingerprint(get_plan(radio.plan_id)) if radio.plan_id else ""


def fleet_status(ctx: AppContext) -> List[RadioStatus]:
    state = load_state(ctx)
    with ctx.lock:
        content, structure = catalog_hashes(ctx.catalog)
    return [
        radio_status(
            radio,
            state.records.get(radio.radio_id),
            content_hash=content,
            structure=structure,
            current_plan_fingerprint=current_plan_fingerprint(radio.radio_id),
        )
        for radio in FLEET.values()
    ]


def scanner_favorites(ctx: AppContext, *, include_licensed: bool = True, near_me: bool = True) -> List[FavoritesList]:
    """The lists the SDS150 is loaded with: enabled, populated, and - for a
    copy meant to be shared - not built from licensed data. The Near Me lists
    built from them come first (``near_me=False`` leaves them out).

    Projected onto the SDS150 exactly as the ``.hpe`` export is, so the
    workspace installer never sees what the scanner cannot tune - the HF and
    CW rows of reference-only lists such as HAM01 and HFNET01."""
    from wasds150.generate.pipeline import apply_profile
    from wasds150.radios.projection import project_favorites
    from wasds150.radios.registry import SDS150

    generated = apply_profile(ctx.catalog, ctx.load_profile())
    chosen = [
        favorite
        for favorite in generated.enabled_favorites
        if favorite.systems and (include_licensed or not favorite.licensed)
    ]
    favorites = [favorite for favorite in project_favorites(chosen, SDS150).favorites if favorite.systems]
    if near_me:
        from wasds150.plans.template import HOME
        from wasds150.radios.near_me import build_near_me_lists

        favorites = build_near_me_lists(favorites, home=HOME) + favorites
    return favorites


def scanner_list_settings(favorites: List[FavoritesList]) -> Dict[str, Any]:
    """How each installed list appears on the scanner: the Near Me lists
    lead on quick keys 1-6, location-controlled; everything else is
    installed but not monitored (see :mod:`wasds150.radios.near_me`)."""
    from wasds150.radios.near_me import list_settings

    return list_settings(favorites)


def _copy_into(source: Path, destination: Path) -> List[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / source.name
    if target.resolve() == source.resolve():
        return []
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)
        return sorted(p for p in target.rglob("*") if p.is_file())
    shutil.copy2(source, target)
    return [target]


def _export_scanner(
    ctx: AppContext, directory: Path, copy_to: Optional[Path], include_licensed: bool
) -> FleetExport:
    from wasds150.bundle.hpe_export import build_per_list_hpe
    from wasds150.bundle.markdown_export import export_markdown

    favorites = scanner_favorites(ctx, include_licensed=include_licensed)
    bundle = directory / "sds150"
    hpe_dir = bundle / "hpe"
    hpe_dir.mkdir(parents=True, exist_ok=True)
    for stale in hpe_dir.glob("*.hpe"):
        stale.unlink()
    hpe = build_per_list_hpe(favorites)
    files: List[Path] = []
    for filename, data in sorted(hpe.files.items()):
        path = hpe_dir / filename
        path.write_bytes(data)
        files.append(path)
    report = export_markdown(favorites, bundle / "favorites-overview.md")
    copies = _copy_into(bundle, Path(copy_to)) if copy_to is not None else []
    return FleetExport(
        radio_id="sds150",
        plan_id="",
        target_id="hpe",
        path=bundle,
        report_path=Path(report),
        rows=len(hpe.files),
        sha256=sha256_of_path(hpe_dir),
        files=files,
        copies=copies,
        warnings=list(hpe.warnings),
    )


def _write_contacts(
    ctx: AppContext, radio_id: str, bundle_dir: Path, copy_to: Optional[Path]
) -> Tuple[List[Path], List[Path], List[str]]:
    """Write the stored contact directories into a CPS bundle folder (see
    :mod:`wasds150.export.atd890_contacts`)."""
    from wasds150.contacts.model import ContactStore
    from wasds150.export.atd890_contacts import contact_files
    from wasds150.radios.registry import get_profile

    profile = get_profile(radio_id)
    if profile.contacts is None or not bundle_dir.is_dir():
        return [], [], []
    store = ContactStore(ctx.config.contacts_dir)
    tables = [t for t in (store.load(p) for p in sorted(profile.contacts.protocols)) if t is not None]
    if not tables:
        return [], [], ["no DMR/NXDN contact list downloaded yet; the fleet update fetches it from radioid.net"]
    files, warnings = contact_files(tables, profile.contacts)
    # ``contacts_to`` keeps a standing copy of the lists (for example a
    # tracked folder in the repository), apart from the bundle.
    keep = load_settings(ctx).get(radio_id, "contacts_to")
    written: List[Path] = []
    copies: List[Path] = []
    for name, text in files.items():
        path = bundle_dir / name
        path.write_bytes(text.encode("ascii", errors="replace"))
        written.append(path)
        targets = [Path(copy_to) / bundle_dir.name / name] if copy_to is not None else []
        if keep:
            targets.append(Path(keep) / name)
        for target in targets:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            copies.append(target)
    return written, copies, warnings


def export_radio(
    ctx: AppContext,
    radio_id: str,
    *,
    out_dir: Optional[Path] = None,
    copy_to: Optional[Path] = None,
    include_licensed: bool = True,
) -> FleetExport:
    """Write one radio's programming file (or bundle) and report.

    ``copy_to`` falls back to the radio's ``copy_to`` fleet setting, so the
    file lands where the vendor program opens files from.
    """
    radio = get_fleet_radio(radio_id)
    directory = Path(out_dir) if out_dir is not None else Path(DEFAULT_OUT_DIR)
    if copy_to is None:
        saved = load_settings(ctx).get(radio.radio_id, "copy_to")
        copy_to = Path(saved) if saved else None
    if not radio.plan_id:
        return _export_scanner(ctx, directory, copy_to, include_licensed)
    export = export_plan(
        ctx,
        radio.plan_id,
        target_id=radio.target_id,
        out_dir=directory,
        copy_to=copy_to,
        include_licensed=include_licensed,
    )
    contact_paths, contact_copies, contact_warnings = _write_contacts(ctx, radio.radio_id, export.csv_path, copy_to)
    return FleetExport(
        radio_id=radio.radio_id,
        plan_id=radio.plan_id,
        target_id=radio.target_id,
        path=export.csv_path,
        report_path=export.report_path,
        rows=export.rows,
        sha256=sha256_of_path(export.csv_path),
        files=[Path(p) for p in export.files] + contact_paths,
        copies=[Path(p) for p in export.copies] + contact_copies,
        warnings=list(export.warnings) + contact_warnings,
    )


def export_fleet(
    ctx: AppContext,
    radio_ids: Iterable[str],
    *,
    out_dir: Optional[Path] = None,
    copy_to: Optional[Path] = None,
    include_licensed: bool = True,
) -> List[FleetExport]:
    return [
        export_radio(ctx, radio_id, out_dir=out_dir, copy_to=copy_to, include_licensed=include_licensed)
        for radio_id in radio_ids
    ]


def record_sync(
    ctx: AppContext,
    radio_id: str,
    *,
    job_id: str = "",
    export_sha256: str = "",
    loadout_snapshot_path: str = "",
    verified: bool = False,
    notes: str = "",
) -> RadioSyncRecord:
    """Mark ``radio_id`` as programmed from the catalog in use right now."""
    radio = get_fleet_radio(radio_id)
    with ctx.lock:
        content, structure = catalog_hashes(ctx.catalog)
    record = RadioSyncRecord(
        radio_id=radio.radio_id,
        plan_id=radio.plan_id,
        synced_at=now_iso(),
        job_id=job_id,
        catalog_content_hash=content,
        catalog_structure_hash=structure,
        plan_fingerprint=current_plan_fingerprint(radio.radio_id),
        export_sha256=export_sha256,
        loadout_snapshot_path=loadout_snapshot_path,
        verified=verified,
        notes=notes,
    )
    ctx.config.ensure_dirs()
    state = load_state(ctx)
    state.record(record)
    state.save(ctx.config.fleet_state_path)
    return record
