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
from wasds150.bundle.hpe_export import build_per_list_hpe
from wasds150.generate.pipeline import apply_profile
from wasds150.models.profile import Profile
from wasds150.models.catalog import Channel, Department, Site, System
from wasds150.recipes.systems import curate_split_systems


def _fl(
    slug, favorite_key, scenario, source_type, system_or_category,
    counties="All 39 counties", notes="", source_url="",
):
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
        source_url=source_url,
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
    assert by_key["FL04"].match.sids == (7971,)
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


def test_keyword_sources_do_not_match_inside_place_names():
    catalog = Catalog(
        favorites=[
            _fl("fl58", "FL58", "Transit", "trunked", "Graham regional system SID 11628"),
        ]
    )
    recipe = build_default_recipes(catalog)[0]
    assert "wwara" not in recipe.match.source_ids


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
        entity_key="public:king-safety", fact_type="system", source_id="public_source",
        name="King County Public Safety Radio Network",
    )
    coverage = evaluate_recipe(recipe, [fact])
    assert coverage.status == "full"


def test_fact_does_not_match_by_name_hint_when_names_are_unrelated():
    recipe = Recipe(
        slug="flx", favorite_key="FLX", label="Totally Different Name",
        match=RecipeMatch(name_hint="Totally Different Name"),
    )
    fact = NormalizedFact(
        entity_key="public:king-safety", fact_type="system", source_id="public_source",
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
        entity_key="public:x", fact_type="system", source_id="public_source", name="Some PD Dispatch",
    )
    coverage = evaluate_recipe(recipe, [fact])
    assert coverage.status == "none"


def test_sid_identity_takes_precedence_over_county_fallback():
    """A SID-qualified trunk recipe must not absorb every system in one of
    its counties when the fact's authoritative system identity differs."""
    recipe = Recipe(
        slug="flx", favorite_key="FLX", label="Test",
        match=RecipeMatch(sid=9999, county_contains=("King",)),
    )
    fact = NormalizedFact(entity_key="hpdb:x", fact_type="system", source_id="sentinel_local", county="King")
    coverage = evaluate_recipe(recipe, [fact])
    assert coverage.status == "none"


def test_local_database_fact_without_sid_recipe_never_matches_by_county_or_name():
    recipe = Recipe(
        slug="flx", favorite_key="FLX", label="Regional",
        match=RecipeMatch(county_contains=("King",), name_hint="Regional"),
    )
    fact = NormalizedFact(
        entity_key="hpdb:CountyId:1", fact_type="system", source_id="sentinel_local",
        county="King", name="Regional Public Safety",
    )
    assert evaluate_recipe(recipe, [fact]).status == "none"


def test_build_default_recipes_detects_multiple_and_url_only_sids():
    catalog = Catalog(favorites=[
        _fl("fl15", "FL15", "Business", "trunked", "Boeing SID 7665 + Port SID 11481"),
        _fl(
            "fl58", "FL58", "Transit", "trunked", "Sound Transit Link",
            source_url="https://www.radioreference.com/db/sid/11628",
        ),
    ])
    by_key = {recipe.favorite_key: recipe for recipe in build_default_recipes(catalog)}
    assert by_key["FL15"].match.sids == (7665, 11481)
    assert by_key["FL58"].match.sids == (11628,)


def test_multi_sid_recipe_matches_either_sid_but_not_county_or_superstring():
    recipe = Recipe(
        slug="flx", favorite_key="FLX", label="Test", requires_local_hpdb=True,
        match=RecipeMatch(sid=7665, sids=(7665, 11481), county_contains=("King",)),
    )
    facts = [
        NormalizedFact(
            entity_key="hpdb:TrunkId:11481", fact_type="system", source_id="sentinel_local",
            raw={"sid": 11481},
        ),
        NormalizedFact(
            entity_key="hpdb:TrunkId:17665", fact_type="system", source_id="sentinel_local",
            county="King", raw={},
        ),
    ]
    coverage = evaluate_recipe(recipe, facts)
    assert coverage.matched_fact_keys == ["hpdb:TrunkId:11481"]


def test_trunk_sid_recipe_rejects_same_number_in_agency_namespace():
    recipe = Recipe(
        slug="flx", favorite_key="FLX", label="Test", requires_local_hpdb=True,
        match=RecipeMatch(sid=7971, sids=(7971,)),
    )
    facts = [
        NormalizedFact(
            entity_key="hpdb:AgencyId:7971", fact_type="system", source_id="sentinel_local",
            raw={"sid": 7971, "sid_kind": "AgencyId"},
        ),
        NormalizedFact(
            entity_key="hpdb:TrunkId:7971", fact_type="system", source_id="sentinel_local",
            raw={"sid": 7971, "sid_kind": "TrunkId"},
        ),
    ]
    assert evaluate_recipe(recipe, facts).matched_fact_keys == ["hpdb:TrunkId:7971"]


def test_discovery_target_recipe_never_auto_matches():
    catalog = Catalog(favorites=[
        _fl("fl72", "FL72", "Discovery", "discovery target", "Schools and stadiums", counties="King"),
    ])
    recipe = build_default_recipes(catalog)[0]
    fact = NormalizedFact(
        entity_key="hpdb:CountyId:1", fact_type="system", source_id="sentinel_local",
        county="King", name="FL72 Schools and stadiums",
    )
    assert recipe.match.configured_sids() == ()
    assert evaluate_recipe(recipe, [fact]).status == "none"


def test_split_curator_keeps_explicit_intent_and_avoids_encrypted_departments():
    clear = _fl("fl09a", "FL09a", "Public safety", "trunked", "SID 1")
    encrypted = _fl("fl09b", "FL09b", "Public safety", "trunked", "SID 1")

    def systems():
        return [System(
            id="s1", label="Regional", sid=1,
            sites=[Site(id="site1", label="Site", departments=[
                Department(id="fire", label="Fire Ops", channels=[Channel(id="f1", label="Dispatch", tgid=1)]),
                Department(id="law", label="Police", channels=[Channel(id="p1", label="Patrol", tgid=2)]),
                Department(id="other", label="Other", channels=[Channel(id="o1", label="Unknown", tgid=3)]),
            ])],
        )]

    clear_result = curate_split_systems(clear, systems())
    encrypted_result = curate_split_systems(encrypted, systems())

    assert [d.id for d in clear_result[0].sites[0].departments] == ["fire"]
    encrypted_department = encrypted_result[0].sites[0].departments[0]
    assert encrypted_department.id == "law"
    assert encrypted_department.encrypted_bucket is True
    assert encrypted_department.avoid is True
    assert encrypted_department.label.startswith("[E]-ENCRYPTED ")


def test_split_curator_supports_documented_numbered_talkgroup_families():
    encrypted = _fl("fl20b", "FL20b", "Public safety", "trunked", "SID 1")
    systems = [System(
        id="s1", label="Regional", sid=1,
        sites=[Site(id="site1", label="Site", departments=[
            Department(id="ops", label="Operations", channels=[
                Channel(id="c1", label="LOPS11", tgid=1),
                Channel(id="c2", label="INV 4", tgid=2),
                Channel(id="c4", label="Investigations", tgid=4),
                Channel(id="c3", label="Unrelated", tgid=3),
            ]),
        ])],
    )]

    result = curate_split_systems(encrypted, systems)

    assert [channel.id for channel in result[0].sites[0].departments[0].channels] == ["c1", "c2", "c4"]


def test_rollup_recipe_does_not_claim_full_coverage_from_one_component_sid():
    catalog = Catalog(favorites=[
        _fl(
            "fl30", "FL30", "Interop", "trunked P25 + conventional",
            "WSP + WSDOT + DNR + Mutual Aid (reuses FL4/5/6/1)",
            source_url="https://www.radioreference.com/db/sid/7971",
        ),
    ])
    recipe = build_default_recipes(catalog)[0]
    fact = NormalizedFact(
        entity_key="hpdb:TrunkId:7971", fact_type="system", source_id="sentinel_local",
        raw={"sid": 7971},
    )
    assert recipe.match.configured_sids() == ()
    assert evaluate_recipe(recipe, [fact]).status == "none"


def test_enrich_catalog_populates_declared_rollup_from_complete_components():
    def component(key, system_id):
        favorite = _fl(key.lower(), key, "Interop", "conventional", "Component")
        favorite.systems = [System(
            id=system_id,
            label=key,
            departments=[Department(
                id=f"{system_id}-department",
                label="Operations",
                channels=[Channel(id=f"{system_id}-channel", label="Channel", freq_mhz=155.0)],
            )],
        )]
        return favorite

    catalog = Catalog(favorites=[
        component("FL01", "system-1"),
        component("FL04", "system-4"),
        component("FL05", "system-5"),
        component("FL06", "system-6"),
        _fl(
            "fl30", "FL30", "Interop", "trunked P25 + conventional",
            "WSP + WSDOT + DNR + Mutual Aid (reuses FL4/5/6/1)",
        ),
    ])

    result = enrich_catalog(catalog, [], build_default_recipes(catalog))
    rollup = result.catalog.by_slug("fl30")
    coverage = next(item for item in result.coverage if item.slug == "fl30")

    assert [system.id for system in rollup.systems] == ["system-4", "system-5", "system-6", "system-1"]
    assert coverage.status == "full"
    assert coverage.warnings == []
    assert coverage.matched_fact_keys == ["derived:FL04", "derived:FL05", "derived:FL06", "derived:FL01"]
    assert {item.source_adapter for item in rollup.provenance} == {"derived_rollup"}
    export = build_per_list_hpe([rollup])
    assert set(export.files) == {"FL30.hpe"}
    assert export.warnings == []

    generated = apply_profile(
        catalog,
        Profile(based_on_catalog_hash=catalog.content_hash()),
    )
    generated_rollup = next(item for item in generated.favorites if item.favorite_key == "FL30")
    assert [system.id for system in generated_rollup.systems] == [
        "system-4", "system-5", "system-6", "system-1",
    ]
    assert generated.counts["with_systems"] == 5


def test_enrich_catalog_leaves_rollup_empty_when_component_is_missing():
    catalog = Catalog(favorites=[
        _fl(
            "fl30", "FL30", "Interop", "trunked P25 + conventional",
            "WSP + WSDOT + DNR + Mutual Aid (reuses FL4/5/6/1)",
        ),
    ])

    result = enrich_catalog(catalog, [], build_default_recipes(catalog))

    assert result.catalog.by_slug("fl30").systems == []
    assert next(item for item in result.coverage if item.slug == "fl30").status == "none"


def test_enrich_catalog_recomputes_existing_rollup_from_current_components():
    def component(key, system_id):
        favorite = _fl(key.lower(), key, "Interop", "conventional", "Component")
        favorite.systems = [System(
            id=system_id, label=key,
            departments=[Department(
                id=f"{system_id}-department", label="Operations",
                channels=[Channel(id=f"{system_id}-channel", label="Channel", freq_mhz=155.0)],
            )],
        )]
        return favorite

    catalog = Catalog(favorites=[
        component("FL01", "system-1"), component("FL04", "system-4"),
        component("FL05", "system-5"), component("FL06", "system-6"),
        _fl(
            "fl30", "FL30", "Interop", "trunked P25 + conventional",
            "Components (reuses FL4/5/6/1)",
        ),
    ])
    first = enrich_catalog(catalog, [], build_default_recipes(catalog)).catalog
    first.by_slug("fl04").systems = component("FL04", "system-4-new").systems

    second = enrich_catalog(first, [], build_default_recipes(first)).catalog

    assert [system.id for system in second.by_slug("fl30").systems] == [
        "system-4-new", "system-5", "system-6", "system-1",
    ]
    assert sum(
        item.source_adapter == "derived_rollup"
        for item in second.by_slug("fl30").provenance
    ) == 4


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
