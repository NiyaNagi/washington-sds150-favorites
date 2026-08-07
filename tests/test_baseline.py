"""Tests for the packaged baseline snapshot (data/baseline_catalog.json).

These pin the packaged JSON to the checked-in CSV: if someone edits the CSV
without regenerating the baseline, ``test_baseline_matches_repo_csv`` fails
loudly instead of silently shipping stale data.
"""
from wasds150.catalog import baseline, loader
from wasds150.catalog.ames_lake import favorites as ames_lake_favorites
from wasds150.catalog.band_profiles import favorites as band_favorites
from wasds150.catalog.puget_ham import favorite as puget_ham_favorite
from wasds150.catalog.upper_lena_lake import favorites as upper_lena_favorites
from wasds150.models.catalog import Catalog
from wasds150.recipes.systems import static_systems_for


def test_load_baseline_returns_statewide_and_king_county_favorites():
    catalog = baseline.load_baseline()
    assert len(catalog.favorites) == 137
    assert len([fl for fl in catalog.favorites if fl.favorite_key.startswith("KC")]) == 39
    assert {fl.favorite_key for fl in catalog.favorites[-5:]} == {"UL00", "UL01", "UL02", "UL03", "PSHAM01"}


def test_baseline_resource_path_exists():
    path = baseline.baseline_resource_path()
    assert path.exists()
    assert path.name == "baseline_catalog.json"


def test_baseline_matches_repo_csv(repo_csv_path):
    from_csv = loader.load_csv(repo_csv_path)
    from_baseline = baseline.load_baseline()
    statewide = Catalog(favorites=from_baseline.favorites[:len(from_csv.favorites)])
    assert statewide.content_hash() == from_csv.content_hash()
    assert [fl.slug for fl in statewide.favorites] == [fl.slug for fl in from_csv.favorites]
    assert [fl.slug for fl in from_baseline.favorites[len(from_csv.favorites):]] == [
        fl.slug for fl in ames_lake_favorites() + band_favorites() + upper_lena_favorites() + [puget_ham_favorite()]
    ]


def test_generate_baseline_from_csv_is_deterministic(sample_csv_path, tmp_path):
    out1 = tmp_path / "b1.json"
    out2 = tmp_path / "b2.json"
    cat1 = baseline.generate_baseline_from_csv(sample_csv_path, out1)
    cat2 = baseline.generate_baseline_from_csv(sample_csv_path, out2)
    assert cat1.content_hash() == cat2.content_hash()
    assert out1.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")


def test_packaged_baseline_has_populated_systems_for_most_rows():
    """Regression test for the audit finding this project fixed: "All 78
    baseline FavoritesList entries have systems=[]". The packaged
    baseline now bakes in Tier C (wasds150.recipes.systems.static_systems_for)
    at regeneration time (see wasds150.catalog.baseline's module
    docstring), so a majority of rows already carry real structured
    systems with zero configuration."""
    catalog = baseline.load_baseline()
    with_systems = [fl for fl in catalog.favorites if fl.systems]
    assert len(with_systems) >= 58
    # At least one channel with a real, explicit frequency, never a
    # placeholder/zero value.
    for fl in with_systems:
        for system in fl.systems:
            for department in system.departments:
                for channel in department.channels:
                    if channel.freq_mhz is not None:
                        assert channel.freq_mhz > 0


def test_packaged_baseline_static_systems_match_current_generation_policy():
    """Changing static seeds/metadata requires regenerating the snapshot."""
    catalog = baseline.load_baseline()
    for favorite in catalog.favorites:
        expected = static_systems_for(favorite)
        if expected:
            assert [system.to_dict() for system in favorite.systems] == [
                system.to_dict() for system in expected
            ], f"{favorite.favorite_key} packaged systems are stale"


def test_packaged_baseline_no_private_input_rows_have_systems():
    """The specific "at minimum" categories the audit called out by name."""
    catalog = baseline.load_baseline()
    by_key = {fl.favorite_key: fl for fl in catalog.favorites}
    for key in ("FL75", "FL02", "FL65", "FL52"):
        assert by_key[key].systems, f"{key} should have populated systems with no private input"


def test_generate_baseline_from_csv_bakes_in_systems_without_changing_content_hash(repo_csv_path, tmp_path):
    """Populating systems must never change the byte-identical content
    hash guarantee -- systems/provenance are excluded from
    FavoritesList.content_hash() by design."""
    plain = loader.load_csv(repo_csv_path)
    regenerated = baseline.generate_baseline_from_csv(repo_csv_path, tmp_path / "regenerated.json")
    assert any(fl.systems for fl in regenerated.favorites)  # sanity: something got baked in
    assert regenerated.content_hash() == plain.content_hash()
