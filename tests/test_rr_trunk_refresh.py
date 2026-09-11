"""RadioReference trunked-site rows refresh a SID row's frequency table."""
from __future__ import annotations

from wasds150.models.catalog import (
    CSV_FIELDS,
    Catalog,
    Channel,
    Department,
    FavoritesList,
    Site,
    System,
    TrunkFrequency,
)
from wasds150.recipes import systems as systems_mod
from wasds150.recipes.default_recipes import build_default_recipes
from wasds150.recipes.engine import enrich_catalog
from wasds150.sources.facts import NormalizedFact


def _row(key, name, system_or_category, systems=()):
    row = {field: "" for field in CSV_FIELDS}
    row.update(
        favorite_key=key, favorite_name=name, system_or_category=system_or_category,
        source_type="trunked P25 Phase II", scenario="Public safety",
    )
    favorite = FavoritesList.from_csv_row(row)
    favorite.systems = list(systems)
    return favorite


def _trunked_system(sid):
    talkgroups = Department(id="d", label="Dispatch", channels=[Channel(id="tg", label="Fire Dispatch", tgid=100)])
    return System(
        id="hpdb", label="Example Radio Network", sid=sid, tech="P25Standard",
        sites=[Site(id="s1", label="Old Site", departments=[talkgroups])],
        trunk_frequencies=[TrunkFrequency(id="old", freq_mhz=851.0)],
    )


def _site(category, site, freq, county="King"):
    return NormalizedFact(
        entity_key=f"rr:{category}:{site}:{freq}", fact_type="site", name=site, freq_mhz=freq, mode="P25",
        county=county, source_id="radioreference_premium",
        raw={"rr_category": category, "rr_description": site},
    )


def test_rebuild_policy_by_row():
    assert systems_mod.rebuild_policy(_row("PSHAM01", "Puget Sound Ham", "")).mode == systems_mod.REPLACE_SYSTEMS
    trunked = systems_mod.rebuild_policy(_row("FLX", "Example Radio Network", "Example SID 1234"))
    assert trunked.mode == systems_mod.REPLACE_TRUNK_FREQUENCIES
    assert "radioreference_premium" in trunked.source_ids
    assert systems_mod.rebuild_policy(_row("FLY", "Marine", "Channels")).mode == systems_mod.ACCUMULATE
    assert systems_mod.rebuilds_systems_from_facts(_row("PSHAM01", "x", ""))
    assert not systems_mod.rebuilds_systems_from_facts(_row("FLX", "x", "SID 1234"))


def test_system_names_match_by_containment_or_acronym():
    match = systems_mod._names_match
    assert match(["Justice Integrated Wireless Network (JIWN)"], "Justice Integrated Wireless Network")
    assert match(["Metro-King PSERN Fire/EMS/Transit"], "Puget Sound Emergency Radio Network (PSERN)")
    assert not match(["Justice Integrated Wireless Network (JIWN)"], "City of Kent")
    assert not match(["Kent"], "City of Kent")  # too short to trust
    assert match(["JBLM ACE LMR (Army P25) - Support"], "US Army CONUS Enterprise Land Mobile Radio Network (ACE LMR)")
    # Acronyms written outside parentheses, as the real export spells them.
    assert match(["Thurston/Mason TCERN + conventional"], "TCERN (Thurston County Emergency Radio Network)")
    assert match(["Grant County MACC 911 Fire/EMS"], "MACC 911")
    assert match(["SW-WA Clark/Skamania CRESA"], "CRESA 911")
    assert match(["Metro-Pierce SS911/PSRS"], "PSRS Tacoma/Puyallup")


def test_ordinary_words_and_technology_names_in_parentheses_do_not_match():
    """False matches seen against a real King County export."""
    match = systems_mod._names_match
    assert not match(["SeaTac Local", "PSERN SID 11628"], "Alaska Airlines (SeaTac Airport)")
    assert not match(["Snoqualmie Local"], "Snoqualmie Casino (Snoqualmie Entertainment)")
    assert not match(["Boeing/Port of Seattle P25"], "Washington Department of Transportation (P25)")
    assert not match(["Ports & Commercial Marine"], "Washington Department of Transportation (P25)")


def test_site_rows_replace_the_frequency_table_and_keep_the_talkgroups():
    row = _row("FLX", "Example Radio Network (ERN)", "Example Radio Network SID 1234", [_trunked_system(1234)])
    facts = [
        _site("Example Radio Network", "Site 001 North", 851.0125),
        _site("Example Radio Network", "Site 001 North", 852.0125),
        _site("Example Radio Network", "Site 002 South", 853.0125, county="Pierce"),
        _site("City of Kent", "Site 001 Tank 5", 155.1075),
    ]
    catalog = Catalog(favorites=[row])
    result = enrich_catalog(catalog, facts, build_default_recipes(catalog))
    system = result.catalog.favorites[0].systems[0]
    assert [tf.freq_mhz for tf in system.trunk_frequencies] == [851.0125, 852.0125, 853.0125]
    assert system.trunk_frequencies[2].usage == "site:Site 002 South"
    assert system.sites[0].departments[0].channels[0].tgid == 100
    [coverage] = result.coverage
    assert coverage.status == "partial"
    assert any("replaced with 3" in w for w in coverage.warnings)
    assert "rr:City of Kent:Site 001 Tank 5:155.1075" not in coverage.matched_fact_keys


def test_without_talkgroups_no_bare_system_is_built():
    row = _row("FLX", "Example Radio Network (ERN)", "Example Radio Network SID 1234")
    catalog = Catalog(favorites=[row])
    facts = [_site("Example Radio Network", "Site 001 North", 851.0125)]
    result = enrich_catalog(catalog, facts, build_default_recipes(catalog))
    assert result.catalog.favorites[0].systems == []
    [coverage] = result.coverage
    assert any("no talkgroups" in w and "web-service API" in w for w in coverage.warnings)


def test_sites_carry_county_fences_and_the_technology():
    row = _row("FLX", "Example Radio Network", "SID 1234")
    [system] = systems_mod.systems_from_rr_site_facts(
        row, [_site("Example Radio Network", "Site 001 North", 851.0125)], sids=(1234,)
    )
    assert system.sid == 1234 and system.tech == "P25Standard"
    [site] = system.sites
    assert site.label == "Site 001 North" and site.lat is not None and site.range_miles
