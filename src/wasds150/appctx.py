"""Wires together config + catalog + profile for the CLI and web UI.

Both entry points build one :class:`AppContext` at startup and use it for
every operation, so there is exactly one place that decides where the
baseline catalog comes from (packaged baseline JSON by default; an explicit
CSV override for maintainers/tests; or a persisted merged-catalog snapshot
once a three-way merge has been applied, see :mod:`wasds150.merge`) and one
place that knows how to load/save the profile.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from wasds150.catalog import baseline as baseline_mod
from wasds150.catalog import loader
from wasds150.config import AppConfig
from wasds150.catalog.validate import partition_validation_issues, validate_catalog
from wasds150.models.catalog import Catalog
from wasds150.models.profile import Profile


@dataclass
class AppContext:
    config: AppConfig
    catalog: Catalog
    catalog_source: str  # "packaged-baseline" | "merged" | the csv path used

    def load_profile(self) -> Profile:
        return Profile.load_or_create(self.config.profile_path, catalog_hash=self.catalog.content_hash())

    def save_profile(self, profile: Profile) -> None:
        self.config.ensure_dirs()
        profile.save(self.config.profile_path)

    def save_catalog(self, catalog: Catalog) -> None:
        """Persist a new catalog snapshot (e.g. after a merge apply) so
        subsequent runs use it instead of the packaged baseline, and update
        this context's in-memory ``catalog``/``catalog_source`` immediately
        so a long-running process (the web UI server) reflects the change
        on its very next request without needing a restart. See
        :mod:`wasds150.merge.three_way`."""
        fatal_issues, _ = partition_validation_issues(validate_catalog(catalog))
        if fatal_issues:
            raise ValueError("refusing to persist invalid catalog: " + "; ".join(fatal_issues))
        self.config.ensure_dirs()
        loader.save_json(catalog, self.config.catalog_path)
        self.catalog = catalog
        self.catalog_source = "merged"


def build_context(config: AppConfig, csv_override: Optional[Path] = None) -> AppContext:
    if csv_override is not None:
        catalog = loader.load_csv(Path(csv_override))
        source = str(csv_override)
    elif config.catalog_path.exists():
        catalog = loader.load_json(config.catalog_path)
        source = "merged"
    else:
        catalog = baseline_mod.load_baseline()
        source = "packaged-baseline"
    return AppContext(config=config, catalog=catalog, catalog_source=source)
