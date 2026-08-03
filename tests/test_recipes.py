"""Tests for the recipe engine: coverage classification + catalog
enrichment (provenance *and* structured systems — see wasds150.recipes
package docstring for why the 14 free-text catalog fields are still never
auto-rewritten, even though systems now are populated)."""
from __future__ import annotations

from wasds150.models.catalog import Catalog, FavoritesList
from wasds150.recipes import (
    Recipe,
    RecipeMatch,
    build_default_recipes,
    enrich_catalog,
    evaluate_recipe,
)
from wasds150.sources.facts import NormalizedFact


def _fl(slug, favorite_key, scenario, source_type, system_or_category, counties="All 39 counties", notes=""):
    return FavoritesList(
        id=slug,
        slug=slug,
        favorite_key=favorite_key,
        favorite_name=favorite_key,
        region="Statewide",
        counties=counties,
        scenario=scenario,
        source_type=source_type,
        system_or_category=system_or_category,
        sites_or_coverage="",
        departments_or_channels="",
        mode="FM",
        monitorability="Full",
        upgrade_required="None",
        source_url="",
        notes=notes,
    )


def test_build_default_recipes_detects_sid_and_trunk_requirement():
    catalog = Catalog(
        favorites=[
            _fl("fl04", "FL04", "Public safety", "trunked P25 Phase II", "WSP SID 7971 (SysID 9CC, WACN BEE00)"),
            _fl("fl01", "FL01", "Public safety/SAR", "conventional", "WA SAR Net"),
        ]
    )
    recipes = build_default_recipes(catalog)
    by_key = {r.favorite_key: r for r in recipes}
    assert by_key["FL04"].requires_local_hpdb is True
    assert by_key["FL04"].match.sid == 7971
    assert by_key["FL01"].requires_local_hpdb is False


def test_build_default_recipes_detects_keyword_sources():
    catalog = Catalog(
        favorites=[
            _fl("fl60", "FL60", "Weather", "conventional", "NOAA Weather Radio (NWR)"),
            _fl("fl61", "FL61", "Amateur", "conventional", "Amateur repeater coordination (WWARA)"),
        ]
    )
    recipes = build_default_recipes(catalog)
    by_key = {r.favorite_key: r for r in recipes}
    assert "noaa_nwr" in by_key["FL60"].match.source_ids
    assert "wwara" in by_key["FL61"].match.source_ids


def test_build_default_recipes_distinguishes_nifc_from_wa_dnr():
    catalog = Catalog(
        favorites=[
            _fl("fl06", "FL06", "Wildfire", "conventional", "WA DNR statewide fire"),
            _fl("fl07", "FL07", "Wildfire", "conventional", "National interagency wildfire cache (NIRSC)"),
        ]
    )
    recipes = build_default_recipes(catalog)
    by_key = {r.favorite_key: r for r in recipes}
    assert by_key["FL06"].match.source_ids == ("wa_dnr",)
    assert by_key["FL07"].match.source_ids == ("nifc",)


def test_build_default_recipes_treats_statewide_as_no_county_filter():
    catalog = Catalog(
        favorites=[
            _fl(
                "fl60",
                "FL60",
                "Amateur",
                "conventional",
                "Amateur repeaters (WWARA)",
                counties="Statewide airspace",
            )
        ]
    )
    recipe = build_default_recipes(catalog)[0]
    assert recipe.match.county_contains == ()

    fact = NormalizedFact(
        entity_key="wwara:1",
        fact_type="frequency",
        source_id="wwara",
        county="King",
        freq_mhz=146.82,
    )
    assert evaluate_recipe(recipe, [fact]).status == "full"


def test_build_default_recipes_extracts_counties_from_regional_prose():
    catalog = Catalog(
        favorites=[
            _fl(
                "flx",
                "FLX",
                "Public safety",
                "conventional",
                "Regional mutual aid",
                counties="Eastern counties (Spokane / Whitman); plus Lincoln County",
            )
        ]
    )
    recipe = build_default_recipes(catalog)[0]
    assert recipe.match.county_contains == ("Spokane", "Whitman", "Lincoln")


def test_evaluate_recipe_full_when_no_local_needed_and_matched():
    recipe = Recipe(slug="fl60", favorite_key="FL60", label="Weather", match=RecipeMatch(source_ids=("noaa_nwr",)))
    fact = NormalizedFact(entity_key="noaa:X", fact_type="station", source_id="noaa_nwr")
    coverage = evaluate_recipe(recipe, [fact])
    assert coverage.status == "full"
    assert coverage.matched_fact_keys == ["noaa:X"]
    assert coverage.warnings == []


def test_evaluate_recipe_none_when_no_facts_match():
    recipe = Recipe(slug="fl60", favorite_key="FL60", label="Weather", match=RecipeMatch(source_ids=("noaa_nwr",)))
    coverage = evaluate_recipe(recipe, [])
    assert coverage.status == "none"


def test_evaluate_recipe_trunk_requires_local_source():
    recipe = Recipe(
        slug="fl04", favorite_key="FL04", label="WSP", requires_local_hpdb=True, match=RecipeMatch(sid=7971)
    )
    public_fact = NormalizedFact(entity_key="fcc:PW:1", fact_type="frequency", source_id="fcc_uls", raw={})
    coverage_partial = evaluate_recipe(recipe, [public_fact])
    assert coverage_partial.status in ("partial", "none")

    local_fact = NormalizedFact(
        entity_key="hpdb:TrunkId:7971", fact_type="system", source_id="sentinel_local", raw={"sid": 7971}
    )
    coverage_full = evaluate_recipe(recipe, [local_fact])
    assert coverage_full.status == "full"
    assert coverage_full.warnings == []


def test_evaluate_recipe_trunk_without_any_match_warns():
    recipe = Recipe(
        slug="fl04", favorite_key="FL04", label="WSP", requires_local_hpdb=True, match=RecipeMatch(sid=7971)
    )
    coverage = evaluate_recipe(recipe, [])
    assert coverage.status == "none"
    assert coverage.warnings


def test_enrich_catalog_with_no_facts_is_a_content_hash_noop():
    catalog = Catalog(favorites=[_fl("fl01", "FL01", "SAR", "conventional", "WA SAR Net")])
    recipes = build_default_recipes(catalog)
    result = enrich_catalog(catalog, [], recipes)
    assert result.catalog.content_hash() == catalog.content_hash()
    assert all(c.status == "none" for c in result.coverage)


def test_enrich_catalog_appends_provenance_without_touching_facts():
    catalog = Catalog(
        favorites=[_fl("fl04", "FL04", "Public safety", "trunked P25", "WSP SID 7971 (SysID 9CC)")]
    )
    recipes = build_default_recipes(catalog)
    fact = NormalizedFact(
        entity_key="hpdb:TrunkId:7971",
        fact_type="system",
        source_id="sentinel_local",
        source_url="",
        retrieved_at="2026-01-01T00:00:00+00:00",
        raw={"sid": 7971},
    )
    result = enrich_catalog(catalog, [fact], recipes)
    new_fl = result.catalog.by_slug("fl04")
    old_fl = catalog.by_slug("fl04")
    # CSV/fact fields are byte-identical; only provenance grew.
    assert new_fl.csv_row() == old_fl.csv_row()
    assert len(new_fl.provenance) == len(old_fl.provenance) + 1
    assert new_fl.provenance[-1].source_adapter == "sentinel_local"
    assert new_fl.provenance[-1].confidence == "verified"


def test_enrich_catalog_dedupes_repeated_provenance():
    catalog = Catalog(
        favorites=[_fl("fl04", "FL04", "Public safety", "trunked P25", "WSP SID 7971 (SysID 9CC)")]
    )
    recipes = build_default_recipes(catalog)
    fact = NormalizedFact(
        entity_key="hpdb:TrunkId:7971",
        fact_type="system",
        source_id="sentinel_local",
        source_url="",
        retrieved_at="2026-01-01T00:00:00+00:00",
        raw={"sid": 7971},
    )
    result = enrich_catalog(catalog, [fact, fact], recipes)  # same fact twice
    new_fl = result.catalog.by_slug("fl04")
    sentinel_provenance = [p for p in new_fl.provenance if p.source_adapter == "sentinel_local"]
    assert len(sentinel_provenance) == 1


# ------------------------------------------------------- name_hint match --
def test_build_default_recipes_derives_name_hint_from_favorite_name():
    catalog = Catalog(favorites=[_fl("fl01", "FL01", "SAR", "conventional", "WA SAR Net")])
    recipes = build_default_recipes(catalog)
    assert recipes[0].match.name_hint == "FL01"  # _fl() uses favorite_key as favorite_name


def test_fact_matches_by_name_hint_when_no_sid_present():
    recipe = Recipe(
        slug="flx", favorite_key="FLX", label="King County Public Safety Radio",
        match=RecipeMatch(name_hint="King County Public Safety Radio"),
    )
    fact = NormalizedFact(
        entity_key="hpdb:CountyId:5301", fact_type="system", source_id="sentinel_local",
        name="King County Public Safety",
    )
    coverage = evaluate_recipe(recipe, [fact])
    assert coverage.status == "full"


def test_fact_does_not_match_by_name_hint_when_names_are_unrelated():
    recipe = Recipe(
        slug="flx", favorite_key="FLX", label="Totally Different Name",
        match=RecipeMatch(name_hint="Totally Different Name"),
    )
    fact = NormalizedFact(
        entity_key="hpdb:CountyId:5301", fact_type="system", source_id="sentinel_local",
        name="King County Public Safety",
    )
    coverage = evaluate_recipe(recipe, [fact])
    assert coverage.status == "none"


def test_fact_does_not_match_by_name_hint_when_too_short():
    """A short/generic name_hint is never enough on its own -- guards
    against an overly broad match (see wasds150.recipes.engine's
    _fact_matches docstring)."""
    recipe = Recipe(slug="flx", favorite_key="FLX", label="PD", match=RecipeMatch(name_hint="PD"))
    fact = NormalizedFact(
        entity_key="hpdb:x", fact_type="system", source_id="sentinel_local", name="Some PD Dispatch",
    )
    coverage = evaluate_recipe(recipe, [fact])
    assert coverage.status == "none"


def test_fact_matching_checks_all_configured_criteria_not_just_the_first():
    """A recipe with both sid and county_contains configured: a fact that
    fails the sid check must still be tested against county_contains
    (this is a behavior change from a strict if/elif precedence chain to
    independently-checked OR conditions)."""
    recipe = Recipe(
        slug="flx", favorite_key="FLX", label="Test",
        match=RecipeMatch(sid=9999, county_contains=("King",)),
    )
    fact = NormalizedFact(entity_key="hpdb:x", fact_type="system", source_id="sentinel_local", county="King")
    coverage = evaluate_recipe(recipe, [fact])
    assert coverage.status == "full"  # matched via county, even though sid didn't match


def test_name_hint_alone_never_disables_the_keyword_source_fallback():
    """Regression test: build_default_recipes sets a non-None name_hint on
    *every* recipe (see _detect_name_hint) -- that must never silently
    disable the independent keyword/source_ids match path, or scenario-
    based matching (e.g. weather -> noaa_nwr) would stop working for
    every real baseline row the moment a name_hint is also present."""
    recipe = Recipe(
        slug="flx", favorite_key="FLX", label="Test",
        match=RecipeMatch(source_ids=("noaa_nwr",), name_hint="FLX"),  # short, never matches on its own
    )
    fact = NormalizedFact(entity_key="noaa_nwr:1", fact_type="station", source_id="noaa_nwr", name="Unrelated Name")
    coverage = evaluate_recipe(recipe, [fact])
    assert coverage.status == "full"


def test_scenario_keyword_match_populates_systems_end_to_end():
    """"Match using ... service/scenario as available": a row whose own
    scenario/system_or_category text mentions a public-source keyword
    (here, weather -> noaa_nwr) gets that source's matched fact turned
    into a real system, not just provenance -- exercised through the full
    build_default_recipes -> enrich_catalog path, the same one
    wasds150.update.pipeline uses."""
    catalog = Catalog(
        favorites=[_fl("fl75", "FL75", "Weather/SAME", "conventional WX", "NOAA Weather Radio transmitters")]
    )
    recipes = build_default_recipes(catalog)
    assert "noaa_nwr" in recipes[0].match.source_ids
    assert recipes[0].match.name_hint  # sanity: this recipe DOES also carry a name_hint

    fact = NormalizedFact(
        entity_key="noaa_nwr:KTEST", fact_type="station", name="NOAA Weather Radio Test Site",
        freq_mhz=162.55, mode="FM", source_id="noaa_nwr", source_url="https://www.weather.gov/nwr/sites?site=KTEST",
    )
    result = enrich_catalog(catalog, [fact], recipes)
    new_fl = result.catalog.by_slug("fl75")
    assert len(new_fl.systems) == 1
    channel = new_fl.systems[0].departments[0].channels[0]
    assert channel.freq_mhz == 162.55
    assert channel.label == "NOAA Weather Radio Test Site"


# -------------------------------------------- enrich_catalog populates systems
def test_enrich_catalog_populates_systems_from_matched_hpdb_fact(synthetic_hpdb_state_path):
    from wasds150.hpe import hpdb

    catalog = Catalog(
        favorites=[_fl("fl04", "FL04", "Public safety", "trunked P25", "WSP SID 6001 (SysID 9CC)")]
    )
    recipes = build_default_recipes(catalog)
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    trunk_slice = next(s for s in hpdb.segment_systems(doc) if s.kind() == "Trunk")
    fact = NormalizedFact(
        entity_key="hpdb:TrunkId:6001", fact_type="system", source_id="sentinel_local",
        raw={"sid": 6001, "records": hpdb.serialize_system_slice(trunk_slice)},
    )
    result = enrich_catalog(catalog, [fact], recipes)
    new_fl = result.catalog.by_slug("fl04")
    assert len(new_fl.systems) == 1
    assert new_fl.systems[0].label == "Regional P25"
    # Still a content-hash no-op: systems/provenance are excluded.
    assert result.catalog.content_hash() == catalog.content_hash()


def test_enrich_catalog_systems_are_deduped_across_repeated_facts(synthetic_hpdb_state_path):
    from wasds150.hpe import hpdb

    catalog = Catalog(
        favorites=[_fl("fl04", "FL04", "Public safety", "trunked P25", "WSP SID 6001 (SysID 9CC)")]
    )
    recipes = build_default_recipes(catalog)
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    trunk_slice = next(s for s in hpdb.segment_systems(doc) if s.kind() == "Trunk")
    fact = NormalizedFact(
        entity_key="hpdb:TrunkId:6001", fact_type="system", source_id="sentinel_local",
        raw={"sid": 6001, "records": hpdb.serialize_system_slice(trunk_slice)},
    )
    result = enrich_catalog(catalog, [fact, fact], recipes)  # same fact twice
    new_fl = result.catalog.by_slug("fl04")
    assert len(new_fl.systems) == 1


def test_enrich_catalog_never_populates_systems_when_nothing_matches():
    catalog = Catalog(favorites=[_fl("fl04", "FL04", "Public safety", "trunked P25", "WSP SID 7971")])
    recipes = build_default_recipes(catalog)
    result = enrich_catalog(catalog, [], recipes)
    assert result.catalog.by_slug("fl04").systems == []
