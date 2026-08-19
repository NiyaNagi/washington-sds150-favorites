"""What is currently configured for each radio, in that radio's own shape.

The dropdown in the UI asks a simple question - "what is loaded for this
radio?" - and the honest answer has a different shape per radio.

The SDS150 is a trunk-tracking scanner.  Its configuration is *hierarchical*:
Favorites Lists containing systems, sites, departments and talkgroups.
Flattening that into a numbered memory list would silently discard every
trunked talkgroup, which is most of what the scanner actually holds.

The TD-H9 and FTX-1 are memory-list transceivers.  Their configuration is a
*flat ordered list* of numbered memories, and the slot number is meaningful
because it is the order the radio scans in.

So this module deliberately does not unify the two.  It returns a
:class:`Loadout` that says which kind it is and carries the matching payload,
and the UI renders whichever shape it gets.  A single "channels" table that
served both would have to lie about one of them.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from wasds150.appctx import AppContext
from wasds150.generate.pipeline import apply_profile
from wasds150.plan.service import channel_row, resolve_named_plan
from wasds150.plans import list_plans
from wasds150.radios.projection import project_favorites
from wasds150.radios.registry import get_profile, list_profiles

#: A radio whose configuration is a flat, ordered list of memories.
KIND_MEMORY_LIST = "memory-list"

#: A radio whose configuration is a tree of Favorites Lists.
KIND_FAVORITES = "favorites"

#: Where saved snapshots live inside the wasds150 home directory.
SNAPSHOT_DIRNAME = "radio-loadouts"


@dataclass
class Loadout:
    """One radio's current configuration."""

    radio_id: str
    radio_label: str
    kind: str
    #: Plan id for a memory-list radio; empty for a favorites radio.
    plan_id: str = ""
    label: str = ""
    description: str = ""
    verified: bool = True
    #: Headline numbers, rendered as a small table in the UI.
    summary: Dict[str, Any] = field(default_factory=dict)
    #: Flat memories, for KIND_MEMORY_LIST.
    channels: List[Dict[str, Any]] = field(default_factory=list)
    #: Favorites Lists, for KIND_FAVORITES.
    favorites: List[Dict[str, Any]] = field(default_factory=list)
    #: Per-block or per-category counts.
    groups: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    export_targets: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "radio_id": self.radio_id,
            "radio_label": self.radio_label,
            "kind": self.kind,
            "plan_id": self.plan_id,
            "label": self.label,
            "description": self.description,
            "verified": self.verified,
            "summary": dict(self.summary),
            "channels": list(self.channels),
            "favorites": list(self.favorites),
            "groups": list(self.groups),
            "warnings": list(self.warnings),
            "export_targets": list(self.export_targets),
        }


def _targets_for(radio_id: str) -> List[Dict[str, Any]]:
    from wasds150.export.registry import targets_for_radio

    return [
        {
            "id": target.id,
            "label": target.label,
            "extension": target.extension,
            "available": target.available,
            "description": target.description,
        }
        for target in targets_for_radio(radio_id)
    ]


def _memory_list_loadout(ctx: AppContext, plan_id: str) -> Loadout:
    """A transceiver's loadout: the resolved plan as numbered memories."""
    plan, resolved = resolve_named_plan(ctx, plan_id)
    profile = resolved.profile

    groups = [
        {"label": name, "count": count}
        for name, count in resolved.block_counts.items()
    ]
    transmit = sum(1 for c in resolved.channels if c.transmit)

    return Loadout(
        radio_id=profile.id,
        radio_label=profile.label,
        kind=KIND_MEMORY_LIST,
        plan_id=plan.id,
        label=plan.label,
        description=plan.description,
        verified=profile.verified,
        summary={
            "memories_used": resolved.slots_used,
            "memories_available": resolved.capacity,
            "reserved": plan.reserve_slots,
            "blocks": len(plan.blocks),
            "transmit_enabled": transmit,
            "receive_only": resolved.slots_used - transmit,
            "dropped": len(resolved.dropped),
            "rx_coverage": profile.rx_coverage_summary(),
        },
        channels=[channel_row(c) for c in resolved.channels],
        groups=groups,
        warnings=list(resolved.warnings),
        export_targets=_targets_for(profile.id),
    )


def _favorites_loadout(ctx: AppContext, radio_id: str) -> Loadout:
    """A scanner's loadout: the enabled Favorites Lists, kept hierarchical."""
    profile = get_profile(radio_id)
    user_profile = ctx.load_profile()
    generated = apply_profile(ctx.catalog, user_profile)
    enabled = generated.enabled_favorites

    projection = project_favorites(enabled, profile)
    rows: List[Dict[str, Any]] = []
    total_channels = 0
    total_talkgroups = 0
    total_systems = 0

    for favorite in projection.favorites:
        channels = 0
        talkgroups = 0
        systems = len(favorite.systems)
        departments = 0
        trunked = 0
        for system in favorite.systems:
            # A trunked system carries its groups under sites and needs the
            # system-wide LCN table; a conventional one has departments
            # directly and no trunk frequencies.
            if system.sites or system.trunk_frequencies:
                trunked += 1
            depts = list(system.departments)
            for site in system.sites:
                depts.extend(site.departments)
            departments += len(depts)
            for dept in depts:
                for channel in dept.channels:
                    # A talkgroup is a channel identified by TGID rather than
                    # by frequency; both live in the same list.
                    if getattr(channel, "tgid", None) is not None:
                        talkgroups += 1
                    else:
                        channels += 1
        total_channels += channels
        total_systems += systems
        total_talkgroups += talkgroups
        rows.append(
            {
                "key": favorite.favorite_key,
                "slug": favorite.slug,
                "name": favorite.favorite_name,
                "region": getattr(favorite, "region", ""),
                "systems": systems,
                "trunked_systems": trunked,
                "departments": departments,
                "channels": channels,
                "talkgroups": talkgroups,
                "reference_only": favorite.reference_only,
            }
        )

    rows.sort(key=lambda row: row["key"])
    groups: Dict[str, int] = {}
    for row in rows:
        prefix = "".join(ch for ch in row["key"] if ch.isalpha()) or "other"
        groups[prefix] = groups.get(prefix, 0) + 1

    return Loadout(
        radio_id=profile.id,
        radio_label=profile.label,
        kind=KIND_FAVORITES,
        label=f"{profile.label} - Favorites Lists",
        description=(
            "The scanner's configuration is hierarchical: Favorites Lists "
            "containing systems, sites, departments and talkgroups. It is "
            "written as one .hpe file per list rather than a memory list."
        ),
        verified=profile.verified,
        summary={
            "favorites_lists": len(rows),
            "systems": total_systems,
            "channels": total_channels,
            "talkgroups": total_talkgroups,
            "rx_coverage": profile.rx_coverage_summary(),
        },
        favorites=rows,
        groups=[
            {"label": key, "count": count} for key, count in sorted(groups.items())
        ],
        warnings=list(projection.warnings),
        export_targets=_targets_for(profile.id),
    )


def loadout_index() -> List[Dict[str, Any]]:
    """One entry per radio, for the dropdown.

    A radio with a registered channel plan gets one entry per plan; a radio
    without one still appears, so the list is never quietly missing hardware
    the project claims to support.
    """
    plans_by_radio: Dict[str, List[Any]] = {}
    for plan in list_plans().values():
        plans_by_radio.setdefault(plan.radio_id, []).append(plan)

    entries: List[Dict[str, Any]] = []
    for radio_id, profile in sorted(list_profiles().items()):
        plans = sorted(plans_by_radio.get(radio_id, []), key=lambda p: p.id)
        if plans:
            for plan in plans:
                entries.append(
                    {
                        "id": plan.id,
                        "radio_id": radio_id,
                        "radio_label": profile.label,
                        "kind": KIND_MEMORY_LIST,
                        "label": plan.label,
                        "description": plan.description,
                        "verified": profile.verified,
                    }
                )
        else:
            entries.append(
                {
                    "id": radio_id,
                    "radio_id": radio_id,
                    "radio_label": profile.label,
                    "kind": KIND_FAVORITES,
                    "label": f"{profile.label} - Favorites Lists",
                    "description": (
                        "Hierarchical scanner configuration; no flat channel "
                        "plan applies."
                    ),
                    "verified": profile.verified,
                }
            )
    return entries


def get_loadout(ctx: AppContext, loadout_id: str) -> Loadout:
    """Resolve one dropdown entry into a full loadout.

    ``loadout_id`` is either a plan id or a radio id; plans win, because a
    radio with a plan is always shown through it.
    """
    key = str(loadout_id).strip().lower()
    if key in list_plans():
        return _memory_list_loadout(ctx, key)
    if key in list_profiles():
        return _favorites_loadout(ctx, key)
    known = sorted({entry["id"] for entry in loadout_index()})
    raise KeyError(f"unknown loadout {loadout_id!r}; known: {', '.join(known)}")


# ------------------------------------------------------------- snapshots --
def snapshot_dir(ctx: AppContext) -> Path:
    return Path(ctx.config.home) / SNAPSHOT_DIRNAME


def save_snapshot(ctx: AppContext, loadout_id: str) -> Dict[str, Any]:
    """Write the current loadout to disk so it can be compared later.

    Two files are written: a timestamped snapshot that is never overwritten,
    and a ``<id>-latest.json`` pointer. Keeping the history means "what
    changed since the last refresh" is answerable without having remembered
    to save anything beforehand.
    """
    loadout = get_loadout(ctx, loadout_id)
    directory = snapshot_dir(ctx)
    directory.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    payload = {
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "loadout_id": loadout_id,
        "catalog_source": ctx.catalog_source,
        "catalog_hash": ctx.catalog.content_hash(),
        "loadout": loadout.to_dict(),
    }
    body = json.dumps(payload, indent=2, sort_keys=True, default=str)

    path = directory / f"{loadout_id}-{stamp}.json"
    path.write_text(body, encoding="utf-8")
    latest = directory / f"{loadout_id}-latest.json"
    latest.write_text(body, encoding="utf-8")

    return {
        "loadout_id": loadout_id,
        "path": str(path),
        "latest": str(latest),
        "saved_at": payload["saved_at"],
        "catalog_hash": payload["catalog_hash"],
    }


def list_snapshots(ctx: AppContext, loadout_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Saved snapshots, newest first."""
    directory = snapshot_dir(ctx)
    if not directory.is_dir():
        return []
    rows: List[Dict[str, Any]] = []
    for path in directory.glob("*.json"):
        if path.name.endswith("-latest.json"):
            continue
        if loadout_id and not path.name.startswith(f"{loadout_id}-"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rows.append(
            {
                "path": str(path),
                "loadout_id": data.get("loadout_id", ""),
                "saved_at": data.get("saved_at", ""),
                "catalog_hash": data.get("catalog_hash", ""),
                "summary": (data.get("loadout") or {}).get("summary", {}),
            }
        )
    rows.sort(key=lambda row: row["saved_at"], reverse=True)
    return rows


def diff_against_snapshot(ctx: AppContext, loadout_id: str) -> Dict[str, Any]:
    """Compare the current loadout with the most recent saved snapshot.

    Comparison is by frequency for a memory-list radio and by favourite key
    for a scanner, because slot numbers and list ordering shift for reasons
    that are not interesting - a channel moving from slot 40 to 41 is not a
    change anybody needs reported.
    """
    latest = snapshot_dir(ctx) / f"{loadout_id}-latest.json"
    current = get_loadout(ctx, loadout_id)
    if not latest.is_file():
        return {
            "loadout_id": loadout_id,
            "has_snapshot": False,
            "message": "no saved snapshot yet; save one to enable comparison",
        }

    saved = json.loads(latest.read_text(encoding="utf-8"))
    previous = saved.get("loadout") or {}

    if current.kind == KIND_MEMORY_LIST:
        def keyed(rows):
            return {
                (round(float(r.get("rx_mhz") or 0), 6), (r.get("name") or "")): r
                for r in rows
            }

        before = keyed(previous.get("channels") or [])
        after = keyed(current.channels)
        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        detail = {
            "added": [
                {"rx_mhz": mhz, "name": name} for mhz, name in added[:200]
            ],
            "removed": [
                {"rx_mhz": mhz, "name": name} for mhz, name in removed[:200]
            ],
        }
    else:
        before = {row["key"]: row for row in previous.get("favorites") or []}
        after = {row["key"]: row for row in current.favorites}
        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        changed = [
            {
                "key": key,
                "channels_before": before[key].get("channels"),
                "channels_after": after[key].get("channels"),
            }
            for key in sorted(set(before) & set(after))
            if before[key].get("channels") != after[key].get("channels")
        ]
        detail = {
            "added": [{"key": key} for key in added],
            "removed": [{"key": key} for key in removed],
            "changed": changed[:200],
        }

    return {
        "loadout_id": loadout_id,
        "has_snapshot": True,
        "saved_at": saved.get("saved_at", ""),
        "catalog_hash_then": saved.get("catalog_hash", ""),
        "catalog_hash_now": ctx.catalog.content_hash(),
        "summary_then": previous.get("summary", {}),
        "summary_now": current.summary,
        "added": len(detail.get("added", [])),
        "removed": len(detail.get("removed", [])),
        "detail": detail,
    }
