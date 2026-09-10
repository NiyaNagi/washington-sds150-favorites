"""Wires together config + catalog + profile for the CLI and web UI.

Both entry points build one :class:`AppContext` at startup and use it for
every operation, so there is exactly one place that decides where the
baseline catalog comes from (packaged baseline JSON by default; an explicit
CSV override for maintainers/tests; or a persisted merged-catalog snapshot
once a three-way merge has been applied, see :mod:`wasds150.merge`) and one
place that knows how to load/save the profile.
"""
from __future__ import annotations

import copy
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from wasds150.catalog import baseline as baseline_mod
from wasds150.catalog import loader
from wasds150.config import AppConfig
from wasds150.catalog.validate import partition_validation_issues, validate_catalog
from wasds150.models.catalog import CSV_FIELDS, Catalog
from wasds150.models.profile import Profile

if TYPE_CHECKING:
    from wasds150.catalog.delta import CatalogDelta


def _append_local_area_extension(catalog: Catalog) -> None:
    """Upgrade a real persisted catalog without changing small custom catalogs.

    Public baseline fields are refreshed in memory while locally enriched
    systems/provenance and profile overrides remain untouched. Missing public
    extension rows are appended, and hand-authored systems are restored to the
    handful of rows that are rebuilt wholly from a public source.

    That last part is narrower than it sounds, deliberately. Most rows
    accumulate: a locally enriched HPDB system is precious and must survive a
    refresh, and re-attaching baseline systems to those rows would duplicate
    content the user has already curated. But a row like ``PSHAM01`` is
    rebuilt from the WWARA extract on every run so a stale copy cannot win by
    id - and an earlier version of that rebuild replaced the row's systems
    outright, discarding hand-written net channels WWARA never supplied. Once
    discarded they stayed discarded, because later runs enrich the *persisted*
    catalog rather than the packaged baseline. Restoring by id repairs an
    already-damaged catalog and is a no-op on a healthy one.
    """
    from wasds150.recipes.systems import rebuilds_systems_from_facts, systems_defined_in_code

    existing = {favorite.slug for favorite in catalog.favorites}
    if len(existing) < 75 or "fl75" not in existing:
        return
    current_by_slug = {favorite.slug: favorite for favorite in catalog.favorites}
    for favorite in baseline_mod.load_baseline().favorites:
        current = current_by_slug.get(favorite.slug)
        if current is not None:
            for field_name in CSV_FIELDS:
                setattr(current, field_name, getattr(favorite, field_name))
            if systems_defined_in_code(current):
                # The code is the source of truth for these systems: replace
                # each persisted copy by id, keep anything enrichment added.
                fresh = {system.id: system for system in favorite.systems}
                current.systems = [
                    copy.deepcopy(fresh.pop(system.id)) if system.id in fresh else system
                    for system in current.systems
                ] + [copy.deepcopy(system) for system in fresh.values()]
            elif rebuilds_systems_from_facts(current):
                present = {system.id for system in current.systems}
                for system in favorite.systems:
                    if system.id not in present:
                        current.systems.append(copy.deepcopy(system))
        elif favorite.favorite_key.startswith(("KC", "LA", "OUT", "BAND", "UL", "PSHAM", "OZ", "HAM", "FTX", "HFNET")):
            catalog.favorites.append(copy.deepcopy(favorite))


@dataclass
class AppContext:
    config: AppConfig
    catalog: Catalog
    catalog_source: str  # "packaged-baseline" | "merged" | the csv path used
    #: Held while ``catalog`` is swapped, so a background job and the web
    #: UI's request threads never see (or write) a half-applied change.
    lock: Any = field(default_factory=threading.RLock, repr=False, compare=False)

    def load_profile(self) -> Profile:
        return Profile.load_or_create(self.config.profile_path, catalog_hash=self.catalog.content_hash())

    def save_profile(self, profile: Profile) -> None:
        self.config.ensure_dirs()
        profile.save(self.config.profile_path)

    def save_catalog(self, catalog: Catalog, *, reason: str = "") -> "CatalogDelta":
        """Persist a new catalog snapshot (e.g. after a merge apply) so
        subsequent runs use it instead of the packaged baseline, and update
        this context's in-memory ``catalog``/``catalog_source`` immediately
        so a long-running process (the web UI server) reflects the change
        on its very next request without needing a restart. See
        :mod:`wasds150.merge.three_way`.

        ``catalog`` is first normalised exactly as :func:`build_context` will
        normalise it on the next load, so the returned
        :class:`~wasds150.catalog.delta.CatalogDelta` - and any hash taken
        from ``self.catalog`` afterwards - describes what a fresh process will
        see. A delta that moved anything is committed to
        ``config.updates_dir``; that record is what tells the fleet which
        radios a talkgroup or repeater refresh has made stale."""
        from wasds150.catalog.delta import UpdateStore, compute_delta

        with self.lock:
            _append_local_area_extension(catalog)
            fatal_issues, _ = partition_validation_issues(validate_catalog(catalog))
            if fatal_issues:
                raise ValueError("refusing to persist invalid catalog: " + "; ".join(fatal_issues))
            delta = compute_delta(self.catalog, catalog, reason=reason)
            self.config.ensure_dirs()
            loader.save_json(catalog, self.config.catalog_path)
            if not delta.is_empty:
                UpdateStore(self.config.updates_dir).commit(delta)
            self.catalog = catalog
            self.catalog_source = "merged"
            return delta


def build_context(config: AppConfig, csv_override: Optional[Path] = None) -> AppContext:
    if csv_override is not None:
        catalog = loader.load_csv(Path(csv_override))
        _append_local_area_extension(catalog)
        source = str(csv_override)
    elif config.catalog_path.exists():
        catalog = loader.load_json(config.catalog_path)
        _append_local_area_extension(catalog)
        source = "merged"
    else:
        catalog = baseline_mod.load_baseline()
        source = "packaged-baseline"
    return AppContext(config=config, catalog=catalog, catalog_source=source)
