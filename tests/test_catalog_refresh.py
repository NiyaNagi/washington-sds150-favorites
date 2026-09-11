"""A correction in the code must reach a catalog persisted before it.

Both paths below once let a withdrawn channel survive forever: persisted
systems are kept by id, so the old copy always won.
"""
from __future__ import annotations

import copy

from wasds150.appctx import build_context
from wasds150.config import AppConfig


def test_persisted_catalog_takes_oz01_channels_from_code(wasds_home):
    from wasds150.catalog import baseline, loader
    from wasds150.models.catalog import Channel, Department, System

    config = AppConfig.default()
    persisted = baseline.load_baseline()
    oz01 = persisted.by_slug("oz01")
    from_code = copy.deepcopy(oz01.systems[0])
    stale = copy.deepcopy(from_code)
    stale.departments[0].channels.append(Channel(id="withdrawn", label="Withdrawn", freq_mhz=145.13))
    enriched = System(id="local-marker", label="Locally enriched", departments=[Department(id="d", label="Ops")])
    oz01.systems = [stale, enriched]
    config.ensure_dirs()
    loader.save_json(persisted, config.catalog_path)

    refreshed = build_context(config).catalog.by_slug("oz01")

    assert [system.id for system in refreshed.systems] == [from_code.id, "local-marker"]
    assert refreshed.systems[0].to_dict() == from_code.to_dict()


def test_other_rows_still_keep_persisted_systems(wasds_home):
    from wasds150.catalog import baseline, loader
    from wasds150.models.catalog import Department, System

    config = AppConfig.default()
    persisted = baseline.load_baseline()
    ham01 = persisted.by_slug("ham01")
    marker = System(id=ham01.systems[0].id, label="Locally curated", departments=[Department(id="d", label="Ops")])
    ham01.systems = [marker]
    config.ensure_dirs()
    loader.save_json(persisted, config.catalog_path)

    refreshed = build_context(config).catalog.by_slug("ham01")

    assert [system.label for system in refreshed.systems] == ["Locally curated"]


def test_apply_profile_drops_static_system_once_prose_names_no_frequency(sample_csv_path):
    from wasds150.catalog.loader import load_csv
    from wasds150.generate.pipeline import apply_profile
    from wasds150.models.profile import Profile
    from wasds150.recipes.systems import static_system_id, static_systems_for

    catalog = load_csv(sample_csv_path)
    fl01 = catalog.by_slug("fl01")
    fl01.systems = static_systems_for(fl01)  # parsed from "ALPHA1 155.000"
    assert [system.id for system in fl01.systems] == [static_system_id(fl01)]
    fl01.departments_or_channels = "Alpha net; no fixed channel"

    result = apply_profile(catalog, Profile(based_on_catalog_hash=catalog.content_hash()))

    assert next(fl for fl in result.favorites if fl.slug == "fl01").systems == []
