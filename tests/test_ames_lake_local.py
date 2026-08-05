from wasds150.catalog.ames_lake import KING_COUNTY_CITIES, favorites
from wasds150.models.catalog import Channel, Department, FavoritesList, Site, System, Catalog
from wasds150.recipes.default_recipes import build_default_recipes
from wasds150.recipes.local_area import curate_local_area_systems
from wasds150.recipes.systems import populate_rollups


def _channel(channel_id, label, tgid):
    return Channel(id=channel_id, label=label, tgid=tgid, mode="P25", service_type=3)


def _psern_system():
    return System(
        id="hpdb:TrunkId:11628",
        label="Synthetic PSERN",
        sid=11628,
        tech="P25Standard",
        sites=[Site(id="site", label="Synthetic Site", departments=[
            Department(id="redmond", label="Redmond", channels=[
                _channel("rf", "Fire Communications", 1),
                _channel("rp", "Police Dispatch", 2),
                _channel("rw", "Public Works - Drains 1", 3),
            ]),
            Department(id="norcom", label="NORCOM", channels=[
                _channel("nf", "Fire Dispatch 1 (Auto Alerts)", 4),
                _channel("np", "Police 1 (Bellevue)", 5),
            ]),
            Department(id="kcso", label="King County Sheriff", channels=[
                _channel("kn", "Dispatch North", 6),
                _channel("ks", "Dispatch Southwest", 7),
            ]),
            Department(id="king", label="King County", channels=[
                _channel("ki", "King County Interop 2", 8),
                _channel("ku", "Unrelated Administration", 9),
            ]),
        ])],
        trunk_frequencies=[],
    )


def test_all_39_king_county_cities_have_location_definitions_and_rows():
    assert len(KING_COUNTY_CITIES) == 39
    assert all(-90 <= spec.lat <= 90 and -180 <= spec.lon <= 180 for spec in KING_COUNTY_CITIES.values())
    assert all(spec.range_miles > 0 for spec in KING_COUNTY_CITIES.values())
    rows = {favorite.favorite_key: favorite for favorite in favorites()}
    assert set(KING_COUNTY_CITIES) <= set(rows)
    assert all(not rows[key].systems for key in KING_COUNTY_CITIES)
    assert {"LA01", "LA17", "OUT01"} <= set(rows)


def test_redmond_curation_splits_law_and_adds_census_location_tags():
    favorite = next(item for item in favorites() if item.favorite_key == "KC29")
    system = curate_local_area_systems(favorite, [_psern_system()])[0]
    departments = [department for site in system.sites for department in site.departments]
    channels = {channel.label for department in departments for channel in department.channels}

    assert "Fire Communications" in channels
    assert "Public Works - Drains 1" in channels
    assert "King County Interop 2" in channels
    assert "Unrelated Administration" not in channels
    encrypted = [department for department in departments if department.encrypted_bucket]
    assert encrypted and all(department.avoid for department in encrypted)
    assert any(channel.label == "Police Dispatch" for department in encrypted for channel in department.channels)
    spec = KING_COUNTY_CITIES["KC29"]
    assert all((department.lat, department.lon, department.range_miles, department.shape) == (
        spec.lat, spec.lon, spec.range_miles, "Circle"
    ) for department in departments)


def test_sammamish_uses_only_reviewed_kcso_dispatch_and_marks_it_avoided():
    favorite = next(item for item in favorites() if item.favorite_key == "KC31")
    system = curate_local_area_systems(favorite, [_psern_system()])[0]
    departments = [department for site in system.sites for department in site.departments]
    labels = [channel.label for department in departments for channel in department.channels]
    assert "Dispatch North" in labels
    assert "Dispatch Southwest" not in labels
    kcso = next(department for department in departments if "King County Sheriff" in department.label)
    assert kcso.encrypted_bucket is True and kcso.avoid is True


def test_milton_recipe_uses_psern_and_psrs_exact_ids():
    catalog = Catalog(favorites=[next(item for item in favorites() if item.favorite_key == "KC24")])
    recipe = build_default_recipes(catalog)[0]
    assert recipe.match.sids == (11628, 8203)


def test_exact_rollup_parser_supports_split_component_keys():
    def component(key):
        return FavoritesList(
            id=key.lower(), slug=key.lower(), favorite_key=key, favorite_name=key,
            region="", counties="", scenario="", source_type="conventional",
            system_or_category="", sites_or_coverage="", departments_or_channels="",
            mode="", monitorability="", upgrade_required="", source_url="", notes="",
            systems=[System(id=f"system-{key}", label=key, departments=[
                Department(id=f"dep-{key}", label="Ops", channels=[Channel(id=f"ch-{key}", label="Ch", freq_mhz=155.0)])
            ])],
        )

    rollup = component("OUT01")
    rollup.systems = []
    rollup.system_or_category = "Outdoor (reuses FL01, FL09a)"
    catalog = Catalog(favorites=[component("FL01"), component("FL09a"), rollup])
    populated = populate_rollups(catalog)
    assert populated["out01"] == ("FL01", "FL09A")
    assert [system.id for system in rollup.systems] == ["system-FL01", "system-FL09a"]
