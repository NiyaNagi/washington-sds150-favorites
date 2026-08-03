from wasds150.catalog import loader
from wasds150.generate.determinism import generation_content_hash, sort_favorites
from wasds150.generate.pipeline import apply_profile, profile_content_hash
from wasds150.models.catalog import FavoritesList, ORIGIN_LOCAL
from wasds150.models.profile import Profile


def test_apply_profile_no_changes_enables_all_baseline(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    result = apply_profile(catalog, profile)
    assert result.counts["baseline_total"] == 3
    assert result.counts["baseline_enabled"] == 3
    assert result.counts["baseline_disabled"] == 0
    assert len(result.enabled_favorites) == 3
    assert result.warnings == []


def test_apply_profile_populates_systems_from_static_free_text(sample_csv_path):
    """Tier C (wasds150.recipes.systems.static_systems_for) runs on every
    apply_profile call, with zero configuration: FL01's "ALPHA1 155.000"
    and FL09a's "CTAF 122.800" each carry an explicit literal frequency;
    FL02 ("Bravo Dispatch, [E]-ENCRYPTED") does not."""
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    result = apply_profile(catalog, profile)
    by_slug = {fl.slug: fl for fl in result.favorites}
    assert len(by_slug["fl01"].systems) == 1
    assert by_slug["fl01"].systems[0].departments[0].channels[0].freq_mhz == 155.0
    assert len(by_slug["fl09a"].systems) == 1
    assert by_slug["fl02"].systems == []
    assert result.counts["with_systems"] == 2


def test_apply_profile_static_systems_reflect_profile_overrides(sample_csv_path):
    """systems are (re)computed *after* profile overrides are applied, so
    an edited departments_or_channels is what actually gets parsed."""
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    profile.set_override("fl02", "departments_or_channels", "Bravo Dispatch 155.000")
    result = apply_profile(catalog, profile)
    fl02 = next(fl for fl in result.favorites if fl.slug == "fl02")
    assert len(fl02.systems) == 1
    assert fl02.systems[0].departments[0].channels[0].freq_mhz == 155.0


def test_apply_profile_systems_never_affect_content_hash(sample_csv_path):
    """systems/provenance are excluded from FavoritesList.content_hash(),
    so populating them can never change generate's determinism guarantee
    or the "no local input reproduces the shipped catalog" invariant."""
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    result = apply_profile(catalog, profile)
    assert any(fl.systems for fl in result.favorites)  # sanity: something got populated
    assert result.content_hash == generation_content_hash(catalog.favorites)


def test_apply_profile_disable(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    profile.set_enabled("fl02", False)
    result = apply_profile(catalog, profile)
    assert result.counts["baseline_enabled"] == 2
    assert result.counts["baseline_disabled"] == 1
    slugs_enabled = {fl.slug for fl in result.enabled_favorites}
    assert "fl02" not in slugs_enabled
    assert "fl02" in {fl.slug for fl in result.favorites}  # still present, just disabled


def test_apply_profile_edit_override(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    profile.set_override("fl01", "notes", "overridden note")
    result = apply_profile(catalog, profile)
    fl01 = next(fl for fl in result.favorites if fl.slug == "fl01")
    assert fl01.notes == "overridden note"
    # baseline catalog itself must remain untouched
    assert catalog.by_slug("fl01").notes != "overridden note"


def test_apply_profile_remove_excludes_entirely(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    profile.set_removed("fl02", True)
    result = apply_profile(catalog, profile)
    assert result.counts["baseline_removed"] == 1
    assert "fl02" not in {fl.slug for fl in result.favorites}


def test_apply_profile_local_addition(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    local_fl = FavoritesList(
        id="local-id",
        slug="local01",
        favorite_key="LOCAL01",
        favorite_name="My Local List",
        region="Test",
        counties="",
        scenario="",
        source_type="",
        system_or_category="",
        sites_or_coverage="",
        departments_or_channels="",
        mode="",
        monitorability="",
        upgrade_required="",
        source_url="",
        notes="",
        origin=ORIGIN_LOCAL,
    )
    profile.add_local_list(local_fl)
    result = apply_profile(catalog, profile)
    assert result.counts["local_total"] == 1
    assert result.counts["local_enabled"] == 1
    assert "local01" in {fl.slug for fl in result.enabled_favorites}


def test_apply_profile_is_deterministic(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    profile.set_enabled("fl02", False)
    profile.set_override("fl01", "notes", "x")

    r1 = apply_profile(catalog, profile)
    r2 = apply_profile(catalog, profile)
    assert r1.content_hash == r2.content_hash
    assert r1.catalog_hash == r2.catalog_hash
    assert r1.profile_hash == r2.profile_hash


def test_generated_output_sorted_by_natural_key(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    result = apply_profile(catalog, profile)
    keys = [fl.favorite_key for fl in result.favorites]
    assert keys == sorted(keys, key=lambda k: (int("".join(c for c in k if c.isdigit())), k))
    assert keys == ["FL01", "FL02", "FL09a"]


def test_profile_content_hash_changes_with_profile_state():
    p1 = Profile()
    p2 = Profile()
    p2.set_enabled("fl01", False)
    assert profile_content_hash(p1) != profile_content_hash(p2)


def test_sort_favorites_matches_generation_order(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    reversed_favs = list(reversed(catalog.favorites))
    assert [fl.slug for fl in sort_favorites(reversed_favs)] == [fl.slug for fl in catalog.favorites]


def test_generation_content_hash_order_independent(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    forward = generation_content_hash(catalog.favorites)
    backward = generation_content_hash(list(reversed(catalog.favorites)))
    assert forward == backward
