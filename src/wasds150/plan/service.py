"""Plan operations shared by the CLI and the web UI.

Both front ends need the same three things: resolve a named plan against the
active catalog, describe the result as plain data, and write it out as a
programming file.  Putting that here keeps a single definition of what
"export the Ozette plan" means, so the button in the browser and the command
in the terminal cannot drift apart.

Nothing in this module imports argparse, HTTP, or CHIRP.  It is deliberately
callable from a test with nothing but an :class:`AppContext`.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from wasds150.appctx import AppContext
from wasds150.generate.pipeline import apply_profile
from wasds150.models.catalog import Catalog, FavoritesList
from wasds150.models.plan import ChannelPlan
from wasds150.plan.resolve import ResolvedPlan, resolve_plan
from wasds150.plans import get_plan, list_plans

#: Where plan exports land when no directory is given.  Matches the CLI
#: default so the UI and the terminal write to the same place.
DEFAULT_OUT_DIR = "wasds150-output/radios"


def _extra_favorites(radio_id: str) -> List[FavoritesList]:
    """Radio-native catalog modules that are not part of the scanner catalog.

    These are checked-in, cited Favorites Lists (D-STAR repeater tables, DMR
    network talkgroup layouts, broadcast stations) that only a particular
    transceiver can use, so they are added at plan-resolution time rather
    than being merged into the shared catalog every scanner build reads.
    Which radio gets which module follows its capabilities; see
    :mod:`wasds150.catalog.extras`.
    """
    from wasds150.catalog.extras import extras_for
    from wasds150.radios.registry import get_profile

    return extras_for(get_profile(radio_id))


def resolve_named_plan(
    ctx: AppContext, plan_id: str, *, include_licensed: bool = True, with_repeaterbook: bool = False
) -> Tuple[ChannelPlan, ResolvedPlan]:
    """Resolve ``plan_id`` against the catalog with the user profile applied.

    The profile is applied first so that a Favorites List the user disabled
    does not contribute channels to a radio plan.  Disabling a list in the UI
    and re-exporting is therefore a supported way to slim a plan down.

    ``include_licensed=False`` leaves out lists built from a licensed
    database (RadioReference), which is how a redistributable copy of a
    programming file is produced for the repository.

    ``with_repeaterbook=True`` appends the operator's applied RepeaterBook
    records as a final block. They come from the local store only -- no
    request is made -- and can never go into a redistributable copy.
    """
    import dataclasses

    if with_repeaterbook and not include_licensed:
        raise ValueError("RepeaterBook records cannot go into a redistributable (--exclude-licensed) export")
    plan = get_plan(plan_id)
    profile = ctx.load_profile()
    generated = apply_profile(ctx.catalog, profile)
    favorites = [fl for fl in generated.enabled_favorites if include_licensed or not fl.licensed]
    # A checked-in snapshot list steps aside when the catalog already holds
    # a refreshed copy under the same key (``wasds150 sources update``).
    present = {fl.favorite_key.upper() for fl in favorites}
    favorites.extend(fl for fl in _extra_favorites(plan.radio_id) if fl.favorite_key.upper() not in present)
    if with_repeaterbook:
        from wasds150.sources.repeaterbook.catalog import plan_block
        from wasds150.sources.repeaterbook.service import RepeaterBookService

        reviewed = RepeaterBookService(ctx.config).reviewed_favorite()
        if reviewed is not None:
            favorites.append(reviewed)
            plan = dataclasses.replace(plan, blocks=tuple(plan.blocks) + (plan_block(),))
    catalog = Catalog(favorites=favorites)
    return plan, resolve_plan(plan, catalog)


def plan_index() -> List[Dict[str, Any]]:
    """Every registered plan, as summary rows for a list view."""
    rows: List[Dict[str, Any]] = []
    for key, plan in sorted(list_plans().items()):
        rows.append(
            {
                "id": key,
                "label": plan.label,
                "radio_id": plan.radio_id,
                "description": plan.description,
                "blocks": len(plan.blocks),
                "reserve_slots": plan.reserve_slots,
            }
        )
    return rows


def channel_row(channel) -> Dict[str, Any]:
    """One resolved memory as JSON-safe data."""
    return {
        "slot": channel.slot,
        "name": channel.name,
        "label": channel.label,
        "rx_mhz": channel.rx_freq_mhz,
        "tx_mhz": channel.tx_freq_mhz,
        "transmit": channel.transmit,
        "mode": channel.mode,
        "power": channel.power,
        "block": channel.block,
        "bank": channel.bank,
        "source": channel.source,
        "skip_scan": channel.skip_scan,
        "rx_tone": channel.rx_tone.raw if channel.rx_tone else "",
        "tx_tone": channel.tx_tone.raw if channel.tx_tone else "",
        "comment": channel.comment,
        "dv_urcall": channel.dv_urcall,
        "dv_rpt1": channel.dv_rpt1,
        "dv_rpt2": channel.dv_rpt2,
        "digital": asdict(channel.digital) if channel.digital is not None else None,
    }


def plan_detail(resolved: ResolvedPlan) -> Dict[str, Any]:
    """Full description of a resolved plan for the UI's detail view."""
    from wasds150.fleet.registry import fleet_info

    profile = resolved.profile
    return {
        "fleet": fleet_info(profile.id),
        "plan": resolved.plan.to_dict(),
        "radio": {
            "id": profile.id,
            "label": profile.label,
            "vendor": profile.vendor,
            "model": profile.model,
            "max_channels": profile.max_channels,
            "name_max_len": profile.name_max_len,
            "verified": profile.verified,
            "rx_coverage": profile.rx_coverage_summary(),
        },
        "slots_used": resolved.slots_used,
        "capacity": resolved.capacity,
        "block_counts": resolved.block_counts,
        "drop_reasons": resolved.drop_reasons(),
        "warnings": list(resolved.warnings),
        "dropped": [
            {
                "label": d.label,
                "freq_mhz": d.freq_mhz,
                "block": d.block,
                "reason": d.reason,
                "detail": d.detail,
            }
            for d in resolved.dropped
        ],
        "channels": [channel_row(c) for c in resolved.channels],
    }


@dataclass
class PlanExport:
    """What an export produced, so the caller can show or download it."""

    plan_id: str
    target_id: str
    rows: int
    #: The programming file, or the bundle directory for directory targets.
    csv_path: Path
    report_path: Path
    warnings: List[str]
    #: Extra locations the programming file was copied to, if any.
    copies: List[Path] = field(default_factory=list)
    #: Individual files inside a directory bundle (empty for file targets).
    files: List[Path] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan": self.plan_id,
            "target": self.target_id,
            "rows": self.rows,
            "csv_path": str(self.csv_path),
            "report_path": str(self.report_path),
            "files": [str(self.csv_path), str(self.report_path)] + [str(path) for path in self.files],
            "copies": [str(path) for path in self.copies],
            "warnings": list(self.warnings),
        }


def export_plan(
    ctx: AppContext,
    plan_id: str,
    *,
    target_id: str = "chirp-csv",
    out_dir: Optional[Path] = None,
    copy_to: Optional[Path] = None,
    include_licensed: bool = True,
    with_repeaterbook: bool = False,
) -> PlanExport:
    """Resolve and write a plan, returning the paths written.

    ``copy_to`` additionally places the programming file in a second
    directory. Exports land inside the repository, but a radio is programmed
    from wherever the operator keeps their working copy; if the two drift, the
    stale file still opens cleanly in the vendor programmer with the right
    channel count and the right frequencies, and only the fields fixed since
    are wrong. Copying in the same step removes that gap.

    Raises ``KeyError`` for an unknown plan or target, ``NotImplementedError``
    for a target that is registered but not yet built, and ``ValueError`` if
    the target does not serve the plan's radio.
    """
    import shutil

    from wasds150.export.registry import get_target
    from wasds150.export.report import render_plan_report

    plan, resolved = resolve_named_plan(
        ctx, plan_id, include_licensed=include_licensed, with_repeaterbook=with_repeaterbook
    )
    target = get_target(target_id)
    target.check_radio(resolved)

    directory = Path(out_dir) if out_dir is not None else Path(DEFAULT_OUT_DIR)
    directory.mkdir(parents=True, exist_ok=True)

    csv_path = directory / f"{plan.id}{target.extension}"
    result = target.write(resolved, csv_path)
    files = [Path(p) for p in getattr(result, "files", [])]
    report_path = directory / f"{plan.id}-report.md"
    report_path.write_text(
        render_plan_report(resolved, extra_warnings=list(getattr(result, "warnings", []))),
        encoding="utf-8",
    )

    copies: List[Path] = []
    if copy_to is not None:
        destination = Path(copy_to)
        destination.mkdir(parents=True, exist_ok=True)
        for source in (csv_path, report_path):
            target_path = destination / source.name
            if target_path.resolve() == source.resolve():
                continue
            if source.is_dir():
                shutil.copytree(source, target_path, dirs_exist_ok=True)
                copies.extend(sorted(target_path.iterdir()))
            else:
                shutil.copy2(source, target_path)
                copies.append(target_path)

    if with_repeaterbook and any(c.source.upper().startswith("RB01/") for c in resolved.channels):
        from wasds150.sources.repeaterbook.service import RepeaterBookService

        # Every file written here holds RepeaterBook-derived rows: retention
        # and Delete All must be able to find and remove each one.
        service = RepeaterBookService(ctx.config)
        for path in [csv_path, report_path, *files, *copies]:
            if Path(path).is_file():
                service.register_export_report(path)

    return PlanExport(
        plan_id=plan.id,
        target_id=target.id,
        rows=result.rows,
        csv_path=csv_path,
        report_path=report_path,
        copies=copies,
        files=files,
        warnings=list(resolved.warnings) + list(result.warnings),
    )
