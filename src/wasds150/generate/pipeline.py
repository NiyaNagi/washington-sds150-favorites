"""The deterministic generation pipeline: baseline Catalog + Profile ->
effective output.

This is intentionally a pure function of its two inputs (no I/O, no clock)
so it is trivially testable and so ``preview``/``generate`` can share it —
``preview`` just skips the snapshot-commit step in
:mod:`wasds150.history.snapshots`.

**Static system population (Tier C)**: every effective Favorites List's
``systems`` is topped up with
:func:`wasds150.recipes.systems.static_systems_for` -- the free-text/seed
tier that needs no local HPDB, no RadioReference Premium data, and no
network access at all (see that module's docstring). This is still pure
(no I/O, no clock: it only reads fields already present on ``fl``), so it
belongs here rather than in the online update pipeline
(:mod:`wasds150.update.pipeline`), and it runs on *every* ``preview``/
``generate`` regardless of whether the packaged baseline or a merged
catalog was loaded, or whether a local-only ``systems`` value is already
present (:func:`~wasds150.recipes.systems.dedupe_systems` makes this
idempotent) -- so at least the no-private-input Favorites Lists (NOAA
weather, national interoperability, FRS/GMRS/MURS/CB, marine VHF, common
aviation/guard, ...) always come out populated, with zero setup required.
Richer systems (from a matched local HPDB/RadioReference Premium fact) are
layered in separately by :func:`wasds150.recipes.engine.enrich_catalog`
and persist through :mod:`wasds150.merge` once applied — never
overwritten here, only added to.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Dict, List

from wasds150.catalog.validate import partition_validation_issues, validate_catalog, validate_profile
from wasds150.generate.determinism import generation_content_hash, sort_favorites
from wasds150.models.catalog import Catalog, FavoritesList
from wasds150.models.profile import Profile
from wasds150.recipes.systems import dedupe_systems, populate_rollups, static_systems_for
from wasds150.util.hashing import content_hash


class GenerationValidationError(ValueError):
    pass


@dataclass
class GeneratedResult:
    """Effective, sorted Favorites List set after applying a profile to a
    catalog, plus the metadata needed to detect drift and show a summary."""

    favorites: List[FavoritesList] = field(default_factory=list)
    catalog_hash: str = ""
    profile_hash: str = ""
    content_hash: str = ""
    counts: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    @property
    def enabled_favorites(self) -> List[FavoritesList]:
        return [fl for fl in self.favorites if fl.enabled]


def profile_content_hash(profile: Profile) -> str:
    """Deterministic hash of a profile's effective content (used to detect
    "nothing changed" between two generate runs)."""
    return content_hash(profile.to_dict())


def _populate_static_systems(fl: FavoritesList) -> FavoritesList:
    """Top up ``fl.systems`` in place with Tier C (see module docstring)
    and return it, for a compact call site in :func:`apply_profile`."""
    additional = static_systems_for(fl)
    if additional:
        refreshed_ids = {system.id for system in additional}
        fl.systems = dedupe_systems([
            system for system in fl.systems if system.id not in refreshed_ids
        ] + additional)
    if fl.favorite_key.upper().startswith("UL") and fl.systems:
        from wasds150.catalog.upper_lena_lake import apply_location
        apply_location(fl)
    return fl


def apply_profile(catalog: Catalog, profile: Profile) -> GeneratedResult:
    """Apply ``profile`` on top of ``catalog`` to produce the effective,
    deterministically-ordered Favorites List set.

    Rules (see architecture doc §Profile / merge-key design):
    * A baseline entry marked ``removed`` in the profile is excluded
      entirely.
    * Field overrides replace the corresponding baseline field verbatim.
    * ``entry.enabled`` (if not ``None``) overrides the baseline default of
      ``True``.
    * Local lists (fully user-authored) are appended, respecting their own
      ``enabled`` flag.
    * ``systems`` is topped up with Tier C static systems (see module
      docstring) after overrides are applied, so an edited
      ``departments_or_channels`` is what gets parsed.
    """
    fatal_issues, validation_warnings = partition_validation_issues(
        validate_catalog(catalog) + validate_profile(profile, catalog)
    )
    if fatal_issues:
        raise GenerationValidationError(
            "catalog/profile validation failed: " + "; ".join(fatal_issues)
        )

    effective: List[FavoritesList] = []
    counts = {
        "baseline_total": len(catalog.favorites),
        "baseline_enabled": 0,
        "baseline_disabled": 0,
        "baseline_removed": 0,
        "local_total": len(profile.local_lists),
        "local_enabled": 0,
        "local_disabled": 0,
        "with_systems": 0,
    }

    for fl in catalog.favorites:
        entry = profile.entries.get(fl.slug)
        if entry is not None and entry.removed:
            counts["baseline_removed"] += 1
            continue
        eff = copy.deepcopy(fl)
        if entry is not None:
            for field_name, value in entry.overrides.items():
                setattr(eff, field_name, value)
            if entry.enabled is not None:
                eff.enabled = entry.enabled
        eff = _populate_static_systems(eff)
        if eff.enabled:
            counts["baseline_enabled"] += 1
        else:
            counts["baseline_disabled"] += 1
        effective.append(eff)

    for fl in profile.local_lists.values():
        eff = _populate_static_systems(copy.deepcopy(fl))
        if eff.enabled:
            counts["local_enabled"] += 1
        else:
            counts["local_disabled"] += 1
        effective.append(eff)

    # Explicit component rollups are derived after profile removals and
    # overrides, so preview/generate always reflects the current effective
    # components and fails closed when one is unavailable.
    populate_rollups(Catalog(favorites=effective))
    counts["with_systems"] = sum(bool(favorite.systems) for favorite in effective)
    ordered = sort_favorites(effective)

    return GeneratedResult(
        favorites=ordered,
        catalog_hash=catalog.content_hash(),
        profile_hash=profile_content_hash(profile),
        content_hash=generation_content_hash(ordered),
        counts=counts,
        warnings=validation_warnings,
    )
