from wasds150.appctx import build_context
from wasds150.config import AppConfig


def test_build_context_with_csv_override(wasds_home, sample_csv_path):
    config = AppConfig.default()
    ctx = build_context(config, csv_override=sample_csv_path)
    assert ctx.catalog_source == str(sample_csv_path)
    assert len(ctx.catalog.favorites) == 3


def test_build_context_default_uses_packaged_baseline(wasds_home):
    config = AppConfig.default()
    ctx = build_context(config)
    assert ctx.catalog_source == "packaged-baseline"
    assert len(ctx.catalog.favorites) == 140


def test_load_profile_creates_new_when_missing(wasds_home, sample_csv_path):
    config = AppConfig.default()
    ctx = build_context(config, csv_override=sample_csv_path)
    profile = ctx.load_profile()
    assert profile.based_on_catalog_hash == ctx.catalog.content_hash()
    assert profile.entries == {}


def test_save_profile_then_load_profile_round_trips(wasds_home, sample_csv_path):
    config = AppConfig.default()
    ctx = build_context(config, csv_override=sample_csv_path)
    profile = ctx.load_profile()
    profile.set_enabled("fl01", False)
    ctx.save_profile(profile)

    reloaded = ctx.load_profile()
    assert reloaded.entries["fl01"].enabled is False


def test_save_catalog_persists_and_updates_in_memory_state(wasds_home, sample_csv_path):
    from wasds150.models.catalog import Catalog

    config = AppConfig.default()
    ctx = build_context(config, csv_override=sample_csv_path)
    new_catalog = Catalog(favorites=list(ctx.catalog.favorites)[:1])

    ctx.save_catalog(new_catalog)

    assert config.catalog_path.exists()
    assert ctx.catalog is new_catalog  # in-memory context updated immediately
    assert ctx.catalog_source == "merged"


def test_save_catalog_is_preferred_over_baseline_on_next_build_context(wasds_home, sample_csv_path):
    from wasds150.models.catalog import Catalog

    config = AppConfig.default()
    ctx = build_context(config, csv_override=sample_csv_path)
    trimmed = Catalog(favorites=list(ctx.catalog.favorites)[:1])
    ctx.save_catalog(trimmed)

    # A fresh build_context (no csv_override this time) should now load the
    # persisted merged catalog instead of the packaged baseline.
    reloaded_ctx = build_context(config)
    assert reloaded_ctx.catalog_source == "merged"
    assert len(reloaded_ctx.catalog.favorites) == 1


def test_legacy_statewide_merged_catalog_gets_local_area_extension(wasds_home):
    from wasds150.catalog import baseline, loader

    config = AppConfig.default()
    legacy = loader.load_json(baseline.baseline_resource_path())
    assert len(legacy.favorites) == 78
    config.ensure_dirs()
    loader.save_json(legacy, config.catalog_path)

    ctx = build_context(config)

    assert ctx.catalog_source == "merged"
    assert len(ctx.catalog.favorites) == 140
    assert len([favorite for favorite in ctx.catalog.favorites if favorite.favorite_key.startswith("KC")]) == 39


def test_persisted_catalog_refreshes_public_fields_and_preserves_systems(wasds_home):
    from wasds150.catalog import baseline, loader
    from wasds150.models.catalog import Department, System

    config = AppConfig.default()
    persisted = baseline.load_baseline()
    fl02 = persisted.by_slug("fl02")
    fl02.favorite_name = "Obsolete ICALL catalog row"
    marker = System(id="local-marker", label="Locally enriched", departments=[Department(id="d", label="Ops")])
    fl02.systems = [marker]
    config.ensure_dirs()
    loader.save_json(persisted, config.catalog_path)

    ctx = build_context(config)
    refreshed = ctx.catalog.by_slug("fl02")
    assert refreshed.favorite_name == "Nationwide Interop + WA STATEOPS"
    assert [system.id for system in refreshed.systems] == ["local-marker"]
