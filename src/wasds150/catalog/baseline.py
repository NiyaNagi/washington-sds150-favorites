"""The packaged, frozen baseline catalog snapshot.

``data/baseline_catalog.json`` is a canonical-JSON snapshot generated once
(via :func:`generate_baseline_from_csv`, also exposed as
``wasds150 catalog regenerate-baseline`` for maintainers) from this
repository's hand-curated ``washington-sds150-favorites.csv``. It is what
ships inside the installed package and is what a fresh ``wasds150 init``
seeds a new profile against, so the tool works even when only the package
(not this source repo) is installed.

The CSV itself remains the human-editable source of truth; nothing in this
module writes to it.

**Baking in Tier C systems**: :func:`generate_baseline_from_csv` also
applies :func:`wasds150.recipes.systems.static_systems_for` to every row
before saving, so the *packaged* baseline already carries real, populated
``systems`` for every row whose own checked-in free text (or a curated
public seed table) supports it — not just the effective output of a
``generate``/``preview`` run (:func:`wasds150.generate.pipeline.apply_profile`
applies the same tier again, idempotently, as defense in depth for a
``--csv`` override or a not-yet-regenerated packaged snapshot). This never
changes :meth:`~wasds150.models.catalog.Catalog.content_hash` (``systems``
is excluded from ``FavoritesList.content_hash()``), so the "no local
input reproduces the shipped catalog exactly" guarantee in
``docs/data-sources.md`` still holds.
"""
from __future__ import annotations

import importlib.resources
from pathlib import Path

from wasds150.catalog import loader
from wasds150.models.catalog import Catalog
from wasds150.recipes.systems import dedupe_systems, static_systems_for

BASELINE_RESOURCE = "baseline_catalog.json"
_DATA_PACKAGE = "wasds150.data"


def load_baseline() -> Catalog:
    """Load the packaged baseline catalog snapshot."""
    resource = importlib.resources.files(_DATA_PACKAGE).joinpath(BASELINE_RESOURCE)
    with importlib.resources.as_file(resource) as path:
        return loader.load_json(Path(path))


def baseline_resource_path() -> Path:
    """Filesystem path to the packaged baseline JSON (mainly for tests)."""
    resource = importlib.resources.files(_DATA_PACKAGE).joinpath(BASELINE_RESOURCE)
    with importlib.resources.as_file(resource) as path:
        return Path(path)


def generate_baseline_from_csv(csv_path: Path, output_path: Path) -> Catalog:
    """Regenerate the packaged baseline JSON from the repo CSV.

    Maintainer-only operation (not called automatically); the resulting
    catalog is written as canonical JSON so it is diff-friendly in version
    control. See module docstring for the Tier C systems this now bakes
    in.
    """
    catalog = loader.load_csv(csv_path)
    for fl in catalog.favorites:
        additional = static_systems_for(fl)
        if additional:
            fl.systems = dedupe_systems(fl.systems + additional)
    loader.save_json(catalog, output_path)
    return catalog

