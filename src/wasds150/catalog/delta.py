"""What changed between two catalogs, at the level a radio cares about.

``Catalog.content_hash`` covers the 14 CSV fields (plus ``enabled``/``flqk``/
``origin``) and deliberately ignores ``systems``; that exclusion is what keeps
the "no local input reproduces the shipped catalog" guarantee. It also means a
refreshed talkgroup table, a new repeater or a corrected frequency changes no
hash the project records, although every radio is programmed from exactly that
structure. :func:`structure_hash` is a second hash that covers it, alongside
``content_hash`` (which is untouched). :func:`compute_delta` explains a change
per favorites list, and :class:`UpdateStore` keeps those explanations as
numbered JSON files, the way :mod:`wasds150.history.snapshots` keeps generate
history.

Compare catalogs that went through :func:`wasds150.appctx.build_context` (or
the same normalisation in :meth:`wasds150.appctx.AppContext.save_catalog`).
Loading refreshes the public CSV fields and restores some baseline systems, so
hashing a raw JSON file reports differences no radio will ever see.
"""
from __future__ import annotations

import datetime
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from wasds150.models.catalog import CSV_FIELDS, Catalog, Channel, Department, FavoritesList, System
from wasds150.util.hashing import content_hash

#: Channel attributes that change what a radio is programmed with, or
#: whether a radius-filtered plan selects the channel at all (position).
#: Notes and provenance are left out: they never reach a memory slot.
CHANNEL_FINGERPRINT_FIELDS: Tuple[str, ...] = (
    "label",
    "freq_mhz",
    "tgid",
    "mode",
    "tone",
    "tx_freq_mhz",
    "tx_tone",
    "service_type",
    "avoid",
    "dmr_color_code",
    "dmr_timeslot",
    "dmr_talkgroup",
    "dmr_talkgroup_name",
    "dmr_call_type",
    "nxdn_ran",
    "nxdn_group_id",
    "network",
    "dv_urcall",
    "dv_rpt1",
    "dv_rpt2",
    "lat",
    "lon",
)

#: List-level fields reported when they differ. Presentation flags are
#: included because they change what an exporter may do with the list.
_LIST_FIELDS: Tuple[str, ...] = tuple(CSV_FIELDS) + (
    "enabled",
    "flqk",
    "origin",
    "reference_only",
    "licensed",
)

#: Sample lines kept per list, so a delta stays readable for a large refresh.
_MAX_SAMPLES = 12


def channel_fingerprint(channel: Channel) -> Dict[str, Any]:
    return {name: getattr(channel, name, None) for name in CHANNEL_FINGERPRINT_FIELDS}


def _department_shell(department: Department) -> Dict[str, Any]:
    return {
        "label": department.label,
        "avoid": department.avoid,
        "lat": department.lat,
        "lon": department.lon,
        "range_miles": department.range_miles,
    }


def _system_shell(system: System) -> Dict[str, Any]:
    """Everything about a system except its channels: identity, trunk
    frequency table, site fences and department fences."""
    return {
        "label": system.label,
        "sid": system.sid,
        "wacn": system.wacn,
        "tech": system.tech,
        "avoid": system.avoid,
        "trunk_frequencies": [[tf.freq_mhz, tf.lcn, tf.usage] for tf in system.trunk_frequencies],
        "departments": [_department_shell(d) for d in system.departments],
        "sites": [
            {
                "label": site.label,
                "avoid": site.avoid,
                "lat": site.lat,
                "lon": site.lon,
                "range_miles": site.range_miles,
                "departments": [_department_shell(d) for d in site.departments],
            }
            for site in system.sites
        ],
    }


def _iter_system_departments(system: System) -> Iterator[Tuple[str, Department]]:
    for department in system.departments:
        yield f"{system.label}/{department.label}", department
    for site in system.sites:
        for department in site.departments:
            yield f"{system.label}/{site.label}/{department.label}", department


def _favorite_structure(favorite: FavoritesList) -> Dict[str, Any]:
    """Ordered, id-free structure of one list. Order is kept because plans
    that sort in catalog order program memories in exactly this order."""
    return {
        "slug": favorite.slug,
        "favorite_key": favorite.favorite_key,
        "systems": [
            {
                "shell": _system_shell(system),
                "channels": [
                    [path, channel_fingerprint(channel)]
                    for path, department in _iter_system_departments(system)
                    for channel in department.channels
                ],
            }
            for system in favorite.systems
        ],
    }


def favorite_structure_hash(favorite: FavoritesList) -> str:
    return content_hash(_favorite_structure(favorite))


def structure_hash(catalog: Catalog) -> str:
    """Hash over every list's systems, sites, departments and channels.

    Additional to :meth:`~wasds150.models.catalog.Catalog.content_hash`, never
    a replacement: that hash pins profiles and history and must keep ignoring
    systems.
    """
    return content_hash([favorite_structure_hash(favorite) for favorite in catalog.favorites])


# ------------------------------------------------------------------ delta --
@dataclass
class SlugDelta:
    slug: str
    favorite_key: str
    #: "added" | "removed" | "changed"
    status: str
    fields_changed: List[str] = field(default_factory=list)
    channels_added: int = 0
    channels_removed: int = 0
    channels_changed: int = 0
    #: Channels whose content is unchanged but whose id or department moved.
    channels_moved: int = 0
    #: Systems whose identity, trunk frequency table or fences changed.
    systems_changed: List[str] = field(default_factory=list)
    samples: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SlugDelta":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class CatalogDelta:
    id: str
    created_at: str
    reason: str
    content_before: str
    content_after: str
    structure_before: str
    structure_after: str
    lists_added: List[str] = field(default_factory=list)
    lists_removed: List[str] = field(default_factory=list)
    per_slug: List[SlugDelta] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return (
            self.content_before == self.content_after
            and self.structure_before == self.structure_after
            and not self.per_slug
        )

    def totals(self) -> Dict[str, int]:
        return {
            "lists_changed": len(self.per_slug),
            "channels_added": sum(s.channels_added for s in self.per_slug),
            "channels_removed": sum(s.channels_removed for s in self.per_slug),
            "channels_changed": sum(s.channels_changed for s in self.per_slug),
        }

    def summary(self) -> str:
        if self.is_empty:
            return "no change"
        t = self.totals()
        return (
            f"{t['lists_changed']} list(s) changed: +{t['channels_added']} "
            f"-{t['channels_removed']} ~{t['channels_changed']} channel(s)"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "reason": self.reason,
            "content_before": self.content_before,
            "content_after": self.content_after,
            "structure_before": self.structure_before,
            "structure_after": self.structure_after,
            "lists_added": list(self.lists_added),
            "lists_removed": list(self.lists_removed),
            "totals": self.totals(),
            "per_slug": [s.to_dict() for s in self.per_slug],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CatalogDelta":
        return cls(
            id=data.get("id", ""),
            created_at=data.get("created_at", ""),
            reason=data.get("reason", ""),
            content_before=data["content_before"],
            content_after=data["content_after"],
            structure_before=data["structure_before"],
            structure_after=data["structure_after"],
            lists_added=list(data.get("lists_added", [])),
            lists_removed=list(data.get("lists_removed", [])),
            per_slug=[SlugDelta.from_dict(s) for s in data.get("per_slug", [])],
        )


def _keyed_channels(favorite: FavoritesList) -> Dict[str, Dict[str, Any]]:
    keyed: Dict[str, Dict[str, Any]] = {}
    for system in favorite.systems:
        for path, department in _iter_system_departments(system):
            for channel in department.channels:
                base = f"{path}/{channel.id}"
                key, n = base, 2
                while key in keyed:
                    key, n = f"{base}#{n}", n + 1
                keyed[key] = channel_fingerprint(channel)
    return keyed


def _keyed_shells(favorite: FavoritesList) -> Dict[str, Dict[str, Any]]:
    keyed: Dict[str, Dict[str, Any]] = {}
    for system in favorite.systems:
        key, n = system.label, 2
        while key in keyed:
            key, n = f"{system.label}#{n}", n + 1
        keyed[key] = _system_shell(system)
    return keyed


def _describe(fingerprint: Dict[str, Any]) -> str:
    if fingerprint.get("freq_mhz") is not None:
        return f"{fingerprint['label']} {fingerprint['freq_mhz']:g}"
    if fingerprint.get("tgid") is not None:
        return f"{fingerprint['label']} TG {fingerprint['tgid']}"
    return str(fingerprint.get("label", ""))


def _count_channels(favorite: FavoritesList) -> int:
    return len(_keyed_channels(favorite))


def _diff_favorite(before: FavoritesList, after: FavoritesList) -> Optional[SlugDelta]:
    fields_changed = [
        name for name in _LIST_FIELDS if getattr(before, name, None) != getattr(after, name, None)
    ]
    same_structure = favorite_structure_hash(before) == favorite_structure_hash(after)
    if not fields_changed and same_structure:
        return None

    delta = SlugDelta(slug=after.slug, favorite_key=after.favorite_key, status="changed", fields_changed=fields_changed)
    if same_structure:
        return delta

    old, new = _keyed_channels(before), _keyed_channels(after)
    for key in old.keys() & new.keys():
        if old[key] != new[key]:
            delta.channels_changed += 1
            if len(delta.samples) < _MAX_SAMPLES:
                delta.samples.append(f"~ {_describe(old[key])} -> {_describe(new[key])}")

    removed = [old[key] for key in old.keys() - new.keys()]
    added = [new[key] for key in new.keys() - old.keys()]
    # A channel that only changed id or department is the same memory; pair
    # those off before counting additions and removals.
    unmatched_added = list(added)
    for fingerprint in list(removed):
        if fingerprint in unmatched_added:
            unmatched_added.remove(fingerprint)
            removed.remove(fingerprint)
            delta.channels_moved += 1
    delta.channels_removed = len(removed)
    delta.channels_added = len(unmatched_added)
    for fingerprint in sorted(unmatched_added, key=_describe):
        if len(delta.samples) < _MAX_SAMPLES:
            delta.samples.append(f"+ {_describe(fingerprint)}")
    for fingerprint in sorted(removed, key=_describe):
        if len(delta.samples) < _MAX_SAMPLES:
            delta.samples.append(f"- {_describe(fingerprint)}")

    old_shells, new_shells = _keyed_shells(before), _keyed_shells(after)
    delta.systems_changed = sorted(
        key
        for key in old_shells.keys() | new_shells.keys()
        if old_shells.get(key) != new_shells.get(key)
    )
    return delta


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def compute_delta(before: Catalog, after: Catalog, *, reason: str = "") -> CatalogDelta:
    """Per-list explanation of ``before -> after``; ``id`` is assigned when
    the delta is committed to an :class:`UpdateStore`."""
    old = {favorite.slug: favorite for favorite in before.favorites}
    new = {favorite.slug: favorite for favorite in after.favorites}
    per_slug: List[SlugDelta] = []
    for favorite in after.favorites:
        previous = old.get(favorite.slug)
        if previous is None:
            per_slug.append(
                SlugDelta(
                    slug=favorite.slug,
                    favorite_key=favorite.favorite_key,
                    status="added",
                    channels_added=_count_channels(favorite),
                )
            )
            continue
        changed = _diff_favorite(previous, favorite)
        if changed is not None:
            per_slug.append(changed)
    for favorite in before.favorites:
        if favorite.slug not in new:
            per_slug.append(
                SlugDelta(
                    slug=favorite.slug,
                    favorite_key=favorite.favorite_key,
                    status="removed",
                    channels_removed=_count_channels(favorite),
                )
            )
    return CatalogDelta(
        id="",
        created_at=_now(),
        reason=reason,
        content_before=before.content_hash(),
        content_after=after.content_hash(),
        structure_before=structure_hash(before),
        structure_after=structure_hash(after),
        lists_added=[s.slug for s in per_slug if s.status == "added"],
        lists_removed=[s.slug for s in per_slug if s.status == "removed"],
        per_slug=per_slug,
    )


# ------------------------------------------------------------------ store --
class UpdateStore:
    """Append-only ``NNNN.json`` records of applied catalog changes."""

    def __init__(self, updates_dir: Path):
        self.updates_dir = Path(updates_dir)
        self.updates_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, update_id: str) -> Path:
        return self.updates_dir / f"{update_id}.json"

    def _existing_ids(self) -> List[str]:
        return sorted(p.stem for p in self.updates_dir.glob("*.json") if p.stem.isdigit())

    def _next_id(self) -> str:
        ids = self._existing_ids()
        return f"{(int(ids[-1]) if ids else 0) + 1:04d}"

    def commit(self, delta: CatalogDelta) -> CatalogDelta:
        delta.id = self._next_id()
        path = self._path(delta.id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(delta.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)
        return delta

    def list(self) -> List[CatalogDelta]:
        return [self.load(update_id) for update_id in self._existing_ids()]

    def load(self, update_id: str) -> CatalogDelta:
        path = self._path(update_id)
        if not path.exists():
            raise KeyError(f"no such catalog update: {update_id!r}")
        return CatalogDelta.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def latest(self) -> Optional[CatalogDelta]:
        ids = self._existing_ids()
        return self.load(ids[-1]) if ids else None
