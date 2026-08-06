from wasds150.catalog.band_profiles import favorites as band_favorites
from wasds150.catalog.baseline import load_baseline
from wasds150.catalog.upper_lena_lake import (
    NPS_COORDINATE_SOURCE,
    UPPER_LENA_LAT,
    UPPER_LENA_LON,
    favorites as upper_lena_favorites,
)
from wasds150.generate.pipeline import apply_profile
from wasds150.models.profile import Profile
from wasds150.recipes.systems import _rollup_component_keys


def _channels(favorite):
    return [
        channel
        for system in favorite.systems
        for department in system.departments
        for channel in department.channels
    ] + [
        channel
        for system in favorite.systems
        for site in system.sites
        for department in site.departments
        for channel in department.channels
    ]


def _departments(favorite):
    return [department for system in favorite.systems for department in system.departments] + [
        department
        for system in favorite.systems
        for site in system.sites
        for department in site.departments
    ]


def test_band_profiles_cover_twelve_distinct_listening_scenarios():
    rows = band_favorites()
    assert len(rows) == 12
    assert [row.favorite_key for row in rows] == [f"BAND{index:02d}" for index in range(1, 13)]
    assert len({row.scenario for row in rows}) == 12
    assert all(row.source_type == "derived verified rollup" for row in rows)
    assert all(_rollup_component_keys(row.system_or_category) for row in rows)


def test_all_band_profiles_generate_without_local_hpdb():
    catalog = load_baseline()
    result = apply_profile(catalog, Profile(based_on_catalog_hash=catalog.content_hash()))
    by_key = {favorite.favorite_key: favorite for favorite in result.favorites}
    assert all(by_key[f"BAND{index:02d}"].systems for index in range(1, 13))


def test_upper_lena_profiles_use_official_nps_coordinate_and_components():
    rows = upper_lena_favorites()
    assert [row.favorite_key for row in rows] == ["UL00", "UL01", "UL02", "UL03"]
    assert UPPER_LENA_LAT == 47.63373172965662
    assert UPPER_LENA_LON == -123.209626245127
    assert NPS_COORDINATE_SOURCE.startswith("https://nps.gov/")
    assert "UL00" in _rollup_component_keys(rows[1].system_or_category)
    assert _rollup_component_keys(rows[3].system_or_category) == ("UL01", "UL02")


def test_upper_lena_static_and_wilderness_lists_generate_and_are_location_tagged():
    catalog = load_baseline()
    result = apply_profile(catalog, Profile(based_on_catalog_hash=catalog.content_hash()))
    by_key = {favorite.favorite_key: favorite for favorite in result.favorites}

    ul00 = by_key["UL00"]
    ul01 = by_key["UL01"]
    assert ul00.systems
    assert ul01.systems
    assert not by_key["UL02"].systems  # fails closed without local P25 HPDB components
    assert not by_key["UL03"].systems

    frequencies = {channel.freq_mhz for channel in _channels(ul00)}
    assert {
        121.5, 146.52, 146.72, 154.0925, 155.16, 156.8, 159.42,
        162.425, 162.475, 168.525, 168.625, 243.0, 462.7125,
    }.issubset(frequencies)
    departments = _departments(ul00) + _departments(ul01)
    assert departments
    assert all(department.lat == UPPER_LENA_LAT for department in departments)
    assert all(department.lon == UPPER_LENA_LON for department in departments)
    assert {department.range_miles for department in _departments(ul00)} == {45.0}
    assert {department.range_miles for department in _departments(ul01)} == {45.0}


def test_current_interop_profile_contains_no_obsolete_pre_rebanding_channels():
    catalog = load_baseline()
    result = apply_profile(catalog, Profile(based_on_catalog_hash=catalog.content_hash()))
    fl02 = next(favorite for favorite in result.favorites if favorite.favorite_key == "FL02")
    frequencies = {channel.freq_mhz for channel in _channels(fl02)}
    assert {155.7525, 453.2125, 769.24375, 851.0125, 852.5375, 853.0125}.issubset(frequencies)
    assert not {866.0125, 866.5125, 868.0125} & frequencies
