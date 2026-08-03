from wasds150.catalog.validate import validate_catalog, validate_profile
from wasds150.catalog import loader
from wasds150.models.catalog import Catalog, FavoritesList, ORIGIN_LOCAL
from wasds150.models.profile import Profile, ProfileEntry


def test_validate_catalog_clean(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    assert validate_catalog(catalog) == []


def test_validate_catalog_detects_duplicate_favorite_key(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    dup = catalog.favorites[0]
    catalog.favorites.append(
        FavoritesList(
            id="dup-id",
            slug=dup.slug,
            favorite_key=dup.favorite_key,
            favorite_name="Duplicate",
            region="x",
            counties="x",
            scenario="x",
            source_type="x",
            system_or_category="x",
            sites_or_coverage="x",
            departments_or_channels="x",
            mode="x",
            monitorability="x",
            upgrade_required="x",
            source_url="x",
            notes="x",
        )
    )
    issues = validate_catalog(catalog)
    assert any("duplicate" in i for i in issues)


def test_validate_catalog_flags_bad_flqk(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    catalog.favorites[0].flqk = 150
    issues = validate_catalog(catalog)
    assert any("out of range" in i for i in issues)


def test_validate_catalog_flags_reserved_flqk(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    catalog.favorites[0].flqk = 0
    issues = validate_catalog(catalog)
    assert any("reserved" in i for i in issues)


def test_validate_catalog_accepts_normal_flqk(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    catalog.favorites[0].flqk = 9
    assert validate_catalog(catalog) == []


def test_validate_profile_unknown_slug_reference(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    profile.entries["not-a-real-slug"] = ProfileEntry(slug="not-a-real-slug", enabled=False)
    issues = validate_profile(profile, catalog)
    assert any("unknown baseline slug" in i for i in issues)


def test_validate_profile_rejects_non_editable_override_field(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    profile.entries["fl01"] = ProfileEntry(slug="fl01", overrides={"id": "hacked"})
    issues = validate_profile(profile, catalog)
    assert any("not editable" in i for i in issues)


def test_validate_profile_local_list_collision_with_baseline(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    fl = FavoritesList(
        id="x",
        slug="fl01",
        favorite_key="FL01",
        favorite_name="Colliding local",
        region="x",
        counties="x",
        scenario="x",
        source_type="x",
        system_or_category="x",
        sites_or_coverage="x",
        departments_or_channels="x",
        mode="x",
        monitorability="x",
        upgrade_required="x",
        source_url="x",
        notes="x",
        origin=ORIGIN_LOCAL,
    )
    profile.local_lists["fl01"] = fl
    issues = validate_profile(profile, catalog)
    assert any("collides" in i for i in issues)
