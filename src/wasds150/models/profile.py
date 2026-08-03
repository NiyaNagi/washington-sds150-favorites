"""User profile: the editable layer on top of the baseline catalog.

A :class:`Profile` never mutates the baseline catalog directly. Instead it
records, per baseline entry (keyed by stable ``slug``), the small set of
changes a user has made (enable/disable, field edits, removal), plus any
fully user-authored "local" Favorites Lists. :mod:`wasds150.generate.pipeline`
combines a :class:`Catalog` and a :class:`Profile` to produce the effective,
deterministic output.

This override shape (``enabled`` / ``overrides`` dict / ``removed`` flag,
keyed by stable slug) is deliberately compatible with the three-way merge
design described in the architecture doc: it already separates
"user-owned/presentation" fields (this module) from "fact" fields (which
will live on upstream-sourced catalog entries once online sources and the
merge engine are implemented). Nothing here needs to change shape when that
lands.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional

from wasds150.models.catalog import CSV_FIELDS, FavoritesList, ORIGIN_LOCAL

#: Fields a user is allowed to override on a baseline entry via
#: ``ProfileEntry.overrides``. All CSV columns plus the FLQK assignment.
EDITABLE_FIELDS: tuple = tuple(CSV_FIELDS) + ("flqk",)

DEFAULT_PROFILE_ID = "default"


@dataclass
class ProfileEntry:
    """A recorded change to one baseline Favorites List, keyed by its slug."""

    slug: str
    enabled: Optional[bool] = None  # None => inherit the baseline default (True)
    removed: bool = False
    overrides: Dict[str, Any] = field(default_factory=dict)
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProfileEntry":
        return cls(
            slug=data["slug"],
            enabled=data.get("enabled"),
            removed=data.get("removed", False),
            overrides=dict(data.get("overrides", {})),
            note=data.get("note", ""),
        )

    def is_noop(self) -> bool:
        """True if this entry no longer records any effective change and can
        be pruned from the profile."""
        return self.enabled is None and not self.removed and not self.overrides


@dataclass
class Profile:
    profile_id: str = DEFAULT_PROFILE_ID
    based_on_catalog_hash: str = ""
    entries: Dict[str, ProfileEntry] = field(default_factory=dict)
    local_lists: Dict[str, FavoritesList] = field(default_factory=dict)

    # -- entry helpers --------------------------------------------------
    def entry_for(self, slug: str) -> ProfileEntry:
        return self.entries.setdefault(slug, ProfileEntry(slug=slug))

    def set_enabled(self, slug: str, enabled: bool) -> None:
        self.entry_for(slug).enabled = enabled

    def set_removed(self, slug: str, removed: bool = True) -> None:
        self.entry_for(slug).removed = removed

    def set_override(self, slug: str, field_name: str, value: Any) -> None:
        if field_name not in EDITABLE_FIELDS:
            raise ValueError(
                f"{field_name!r} is not editable; must be one of {EDITABLE_FIELDS}"
            )
        self.entry_for(slug).overrides[field_name] = value

    def clear_override(self, slug: str, field_name: str) -> None:
        entry = self.entries.get(slug)
        if entry and field_name in entry.overrides:
            del entry.overrides[field_name]
            if entry.is_noop():
                del self.entries[slug]

    def restore(self, slug: str) -> None:
        """Drop all recorded changes for a baseline slug, reverting to the
        baseline as-is."""
        self.entries.pop(slug, None)

    # -- local lists ------------------------------------------------------
    def add_local_list(self, favorites_list: FavoritesList) -> None:
        favorites_list.origin = ORIGIN_LOCAL
        self.local_lists[favorites_list.slug] = favorites_list

    def remove_local_list(self, slug: str) -> None:
        self.local_lists.pop(slug, None)

    # -- serialization ----------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "based_on_catalog_hash": self.based_on_catalog_hash,
            "entries": {slug: entry.to_dict() for slug, entry in self.entries.items()},
            "local_lists": {slug: fl.to_dict() for slug, fl in self.local_lists.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Profile":
        entries = {
            slug: ProfileEntry.from_dict(entry_data)
            for slug, entry_data in data.get("entries", {}).items()
        }
        local_lists = {
            slug: FavoritesList.from_dict(fl_data)
            for slug, fl_data in data.get("local_lists", {}).items()
        }
        return cls(
            profile_id=data.get("profile_id", DEFAULT_PROFILE_ID),
            based_on_catalog_hash=data.get("based_on_catalog_hash", ""),
            entries=entries,
            local_lists=local_lists,
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Profile":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def load_or_create(cls, path: Path, catalog_hash: str = "") -> "Profile":
        if path.exists():
            return cls.load(path)
        return cls(based_on_catalog_hash=catalog_hash)
