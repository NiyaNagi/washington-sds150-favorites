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

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from wasds150.appctx import AppContext
from wasds150.generate.pipeline import apply_profile
from wasds150.models.catalog import Catalog
from wasds150.models.plan import ChannelPlan
from wasds150.plan.resolve import ResolvedPlan, resolve_plan
from wasds150.plans import get_plan, list_plans

#: Where plan exports land when no directory is given.  Matches the CLI
#: default so the UI and the terminal write to the same place.
DEFAULT_OUT_DIR = "wasds150-output/radios"


def resolve_named_plan(ctx: AppContext, plan_id: str) -> Tuple[ChannelPlan, ResolvedPlan]:
    """Resolve ``plan_id`` against the catalog with the user profile applied.

    The profile is applied first so that a Favorites List the user disabled
    does not contribute channels to a radio plan.  Disabling a list in the UI
    and re-exporting is therefore a supported way to slim a plan down.
    """
    profile = ctx.load_profile()
    generated = apply_profile(ctx.catalog, profile)
    catalog = Catalog(favorites=generated.enabled_favorites)
    plan = get_plan(plan_id)
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
        "source": channel.source,
        "skip_scan": channel.skip_scan,
        "rx_tone": channel.rx_tone.raw if channel.rx_tone else "",
        "tx_tone": channel.tx_tone.raw if channel.tx_tone else "",
        "comment": channel.comment,
    }


def plan_detail(resolved: ResolvedPlan) -> Dict[str, Any]:
    """Full description of a resolved plan for the UI's detail view."""
    profile = resolved.profile
    return {
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
    csv_path: Path
    report_path: Path
    warnings: List[str]
    #: Extra locations the programming file was copied to, if any.
    copies: List[Path] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan": self.plan_id,
            "target": self.target_id,
            "rows": self.rows,
            "csv_path": str(self.csv_path),
            "report_path": str(self.report_path),
            "files": [str(self.csv_path), str(self.report_path)],
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

    plan, resolved = resolve_named_plan(ctx, plan_id)
    target = get_target(target_id)
    target.check_radio(resolved)

    directory = Path(out_dir) if out_dir is not None else Path(DEFAULT_OUT_DIR)
    directory.mkdir(parents=True, exist_ok=True)

    csv_path = directory / f"{plan.id}{target.extension}"
    result = target.write(resolved, csv_path)
    report_path = directory / f"{plan.id}-report.md"
    report_path.write_text(render_plan_report(resolved), encoding="utf-8")

    copies: List[Path] = []
    if copy_to is not None:
        destination = Path(copy_to)
        destination.mkdir(parents=True, exist_ok=True)
        for source in (csv_path, report_path):
            target_path = destination / source.name
            if target_path.resolve() == source.resolve():
                continue
            shutil.copy2(source, target_path)
            copies.append(target_path)

    return PlanExport(
        plan_id=plan.id,
        target_id=target.id,
        rows=result.rows,
        csv_path=csv_path,
        report_path=report_path,
        copies=copies,
        warnings=list(resolved.warnings) + list(result.warnings),
    )
