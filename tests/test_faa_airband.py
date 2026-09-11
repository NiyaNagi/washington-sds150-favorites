"""FAAAIR: the FAA's facility frequency file as one located airband list,
and the fleet blocks that put the airports near home on every radio."""
from __future__ import annotations

from wasds150.export.atd890_bundle import AM_AIR_MAX
from wasds150.models.catalog import Catalog, Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.plan.resolve import resolve_plan
from wasds150.plans.template import build_fleet_plan
from wasds150.recipes import build_default_recipes, enrich_catalog
from wasds150.recipes.engine import evaluate_recipe
from wasds150.recipes.faa_airband import FAA_AIRBAND_KEY, build_faa_airband_favorite
from wasds150.recipes.systems import systems_from_flat_facts
from wasds150.sources.facts import NormalizedFact

HOME = (47.6351, -121.9954)
URL = "https://nfdc.faa.gov/webContent/28DaySub/28DaySubscription_Effective_2026-08-06.zip"
BFI = (47.53, -122.30)
PAE = (47.91, -122.28)
AWO = (48.16, -122.16)
RNT = (47.49, -122.21)
S43 = (47.908, -122.103)
BEACON_HILL = (47.567, -122.308)
GEG = (47.62, -117.53)  # Spokane, far outside the 60-mile radius


def _frq(provider, facility_type, served, use, freq, where, *, name="", call="", approach="", sector="", served_name=""):
    raw = {
        "EFF_DATE": "2026/08/06", "FACILITY": provider, "FAC_NAME": name, "FACILITY_TYPE": facility_type,
        "SERVICED_FACILITY": served, "SERVICED_FAC_NAME": served_name or name, "SERVICED_STATE": "WA",
        "TOWER_OR_COMM_CALL": call, "PRIMARY_APPROACH_RADIO_CALL": approach, "FREQ": str(freq),
        "SECTORIZATION": sector, "FREQ_USE": use, "LAT_DECIMAL": str(where[0]), "LONG_DECIMAL": str(where[1]),
    }
    return NormalizedFact(
        entity_key=f"faa_nasr:frq:{served}:{freq:.3f}:{use}", fact_type="frequency",
        name=f"{call or served} {use}", freq_mhz=freq, mode="AM", lat=where[0], lon=where[1],
        location_precision="exact", source_id="faa_nasr", source_url=URL,
        retrieved_at="2026-09-10T00:00:00+00:00", raw=raw,
    )


def washington():
    boeing = dict(name="BOEING FLD/KING COUNTY INTL", call="BOEING", approach="SEATTLE")
    s46 = dict(name="SEATTLE-TACOMA APPROACH CONTROL", approach="SEATTLE")
    return [
        _frq("BFI", "ATCT", "BFI", "LCL/P", 118.3, BFI, sector="RWY 14L/32R", **boeing),
        _frq("BFI", "ATCT", "BFI", "LCL/P", 120.6, BFI, sector="RWY 14R/32L & ALL IFR", **boeing),
        _frq("BFI", "ATCT", "BFI", "GND/P", 121.9, BFI, **boeing),
        _frq("BFI", "ATCT", "BFI", "ATIS", 127.75, BFI, **boeing),
        _frq("BFI", "ATCT", "BFI", "LCL/P", 257.8, BFI, **boeing),
        _frq("BFI", "NAVAID", "BFI", "BFI VOT", 108.6, BFI, name="SEATTLE"),
        _frq("RNT", "ATCT", "RNT", "LCL/P", 124.7, RNT, name="RENTON MUNI", call="RENTON"),
        _frq("RNT", "ASOS_AWOS", "RNT", "RNT ASOS", 126.95, RNT),
        _frq("GEG", "ATCT", "GEG", "LCL/P", 132.1, GEG, name="SPOKANE INTL", call="SPOKANE"),
        _frq("S46", "TRACON", "PAE", "APCH/P DEP/P", 119.2, PAE, sector="017-079 SEA, RWY 34", served_name="PAINE", **s46),
        _frq("S46", "TRACON", "BFI", "CLASS B", 119.2, BFI, sector="017-079 SEA, RWY 34", served_name="BOEING", **s46),
        _frq("S46", "TRACON", "BFI", "APCH/P DEP/P", 119.2, BFI, sector="017-079 SEA, RWY 34", served_name="BOEING", **s46),
        _frq("S46", "TRACON", "AWO", "APCH/P DEP/P", 128.5, AWO, served_name="ARLINGTON", **s46),
        _frq("BEACON HILL", "RCAG", "BEACON HILL", "BEACON HILL RCAG", 120.3, BEACON_HILL, name="BEACON HILL", sector="LOW/HIGH"),
        _frq("S43", "NON-ATCT", "S43", "CTAF", 122.9, S43, name="HARVEY FLD"),
    ]


def _row(key, *, scenario="", systems=(), provenance=()):
    return FavoritesList(
        id=key.lower(), slug=key.lower(), favorite_key=key, favorite_name=f"{key} test", region="", counties="",
        scenario=scenario, source_type="conventional AM", system_or_category="", sites_or_coverage="",
        departments_or_channels="", mode="AM", monitorability="", upgrade_required="", source_url="", notes="",
        systems=list(systems), provenance=list(provenance),
    )


def _faaair():
    return build_faa_airband_favorite(washington(), home=HOME)


def _departments(fl):
    return {d.label: d for s in fl.systems for d in s.departments}


# ----------------------------------------------------------------- the list
def test_one_geo_fenced_department_per_facility_towers_first():
    fl = _faaair()
    assert fl.favorite_key == FAA_AIRBAND_KEY and fl.enabled and not fl.licensed
    assert [p.source_adapter for p in fl.provenance] == ["faa_nasr"] and fl.source_url == URL
    assert [d.label for s in fl.systems for d in s.departments] == [
        "RNT Renton Muni", "BFI Boeing Fld/King County Intl", "GEG Spokane Intl",
        "S46 Seattle-Tacoma Approach Control", "Beacon Hill RCAG", "S43 Harvey Fld",
    ]
    renton = _departments(fl)["RNT Renton Muni"]
    assert (renton.lat, renton.lon, renton.range_miles, renton.shape) == (47.49, -122.21, 25.0, "Circle")
    approach = _departments(fl)["S46 Seattle-Tacoma Approach Control"]
    assert approach.range_miles > 40.0  # the fence reaches every airport it serves


def test_labels_say_what_each_frequency_is_and_beacons_are_left_out():
    fl = _faaair()
    boeing = _departments(fl)["BFI Boeing Fld/King County Intl"]
    assert [(c.label, c.freq_mhz) for c in boeing.channels] == [
        ("BFI TWR 14L/32R", 118.3), ("BFI TWR 14R/32L", 120.6), ("BFI TWR", 257.8),
        ("BFI ATIS", 127.75), ("BFI GND", 121.9),
    ]
    assert all(c.mode == "AM" and c.service_type == 15 for c in boeing.channels)
    labels = {c.label for d in _departments(fl).values() for c in d.channels}
    assert {"RNT TWR", "RNT ASOS", "Beacon Hill CTR", "S43 CTAF", "Seattle APP"} <= labels
    assert 108.6 not in {c.freq_mhz for d in _departments(fl).values() for c in d.channels}


def test_an_approach_frequency_is_kept_once_where_it_is_nearest_home():
    approach = _departments(_faaair())["S46 Seattle-Tacoma Approach Control"]
    [shared] = [c for c in approach.channels if c.freq_mhz == 119.2]
    assert shared.label == "Seattle APP 017-079"
    assert (shared.lat, shared.lon) == BFI  # Boeing Field is nearer home than Paine Field
    assert "serves BFI, PAE" in shared.notes


def test_a_tower_label_keeps_only_the_first_runway_pair():
    sea = _frq("SEA", "ATCT", "SEA", "LCL/P", 119.9, (47.45, -122.31), name="SEATTLE-TACOMA INTL",
               sector="RWY 16L/34R, 16C/34C WEST")
    [department] = build_faa_airband_favorite([sea]).systems[0].departments
    assert [c.label for c in department.channels] == ["SEA TWR 16L/34R"]


def test_a_tower_keeps_a_frequency_a_nearby_field_shares():
    w36 = _frq("W36", "NON-ATCT", "W36", "CTAF", 124.7, (47.53, -122.28), name="WILL ROGERS WILEY POST MEML")
    departments = _departments(build_faa_airband_favorite(washington() + [w36], home=HOME))
    [channel] = [c for d in departments.values() for c in d.channels if c.freq_mhz == 124.7]
    assert channel.label == "RNT TWR" and "also W36 CTAF" in channel.notes
    assert "W36 Will Rogers Wiley Post Meml" not in departments  # its only frequency is Renton's


def test_a_ctaf_several_fields_share_becomes_one_common_channel():
    fields = [_frq(f"F{i}", "NON-ATCT", f"F{i}", "CTAF", 122.9, (47.70 + i * 0.05, -122.05), name=f"FIELD {i}") for i in range(3)]
    departments = _departments(build_faa_airband_favorite(washington() + fields, home=HOME))
    [common] = [d for label, d in departments.items() if label.startswith("Common CTAF")]
    [channel] = common.channels
    assert (channel.label, channel.freq_mhz) == ("Common CTAF", 122.9)
    assert "shared by F0, F1, F2" in channel.notes and common.range_miles > 15.0
    assert [c for label, d in departments.items() if not label.startswith("Common") for c in d.channels if c.freq_mhz == 122.9] == []


def test_guard_reads_guard():
    guard = _frq("SEA", "ATCT", "SEA", "EMERG", 121.5, (47.45, -122.31), name="SEATTLE-TACOMA INTL")
    assert [c.label for d in _departments(build_faa_airband_favorite([guard], home=HOME)).values() for c in d.channels] == ["Guard"]


def test_no_faa_frequencies_means_no_list():
    assert build_faa_airband_favorite([]) is None


# --------------------------------------------------------------- the engine
def test_the_engine_builds_faaair_whenever_the_faa_source_ran():
    catalog = enrich_catalog(Catalog(favorites=[]), washington(), []).catalog
    assert [fl.favorite_key for fl in catalog.favorites] == [FAA_AIRBAND_KEY]


def test_an_aviation_row_no_longer_absorbs_faa_frequencies_by_keyword():
    row = _row("FL48", scenario="Civil aviation monitoring")
    [recipe] = build_default_recipes(Catalog(favorites=[row]))
    citation = NormalizedFact(entity_key="faa_nasr:com:SEA", fact_type="doc_ref", name="SEATTLE RCO",
                              source_id="faa_nasr", source_url=URL)
    assert evaluate_recipe(recipe, washington() + [citation]).matched_fact_keys == ["faa_nasr:com:SEA"]


def test_frequencies_an_earlier_keyword_match_left_in_a_row_are_removed():
    marine = NormalizedFact(entity_key="uscg:16", fact_type="frequency", name="Marine 16", freq_mhz=156.8,
                            mode="FM", source_id="uscg_navcen")
    row = _row("FL48", provenance=[Provenance(source_adapter="static_pack"), Provenance(source_adapter="faa_nasr", source_url=URL)])
    baseline = System(id="fl48-base", label="Baseline", departments=[
        Department(id="fl48-d", label="Ops", channels=[Channel(id="c1", label="KSEA Tower", freq_mhz=119.9, mode="AM")]),
    ])
    row.systems = [baseline] + systems_from_flat_facts(row, washington() + [marine])  # what the old match built

    catalog = enrich_catalog(Catalog(favorites=[row]), washington(), []).catalog
    cleaned = next(fl for fl in catalog.favorites if fl.favorite_key == "FL48")
    freqs = [c.freq_mhz for s in cleaned.systems for d in s.departments for c in d.channels]
    assert freqs == [119.9, 156.8]  # the baseline and the marine row survive
    assert "faa_nasr" not in {p.source_adapter for p in cleaned.provenance}
    assert FAA_AIRBAND_KEY in {fl.favorite_key for fl in catalog.favorites}


# ---------------------------------------------------------------- the radios
FAR_OUTLET = Channel(id="far", label="Far outlet", freq_mhz=118.05, mode="AM")


def _resolved(radio_id):
    catalog = Catalog(favorites=[_faaair(), _row("FL48", systems=[
        System(id="fl48-s", label="ZSE", departments=[Department(id="fl48-d", label="Channels", channels=[FAR_OUTLET])]),
    ])])
    return resolve_plan(build_fleet_plan(radio_id), catalog)


def _block(resolved, label):
    return [c for c in resolved.channels if c.block == label]


def test_airports_near_home_come_first_nearest_first_within_the_radius():
    resolved = _resolved("th-d75")
    local = _block(resolved, "Airports Near Home")
    assert local[0].label == "RNT TWR"  # Renton is the nearest field
    near = [c for c in local if c.distance_miles <= 60]
    assert {c.rx_freq_mhz for c in near} == {118.3, 120.6, 121.9, 127.75, 257.8, 124.7, 126.95, 119.2, 128.5, 120.3, 122.9}
    # Broadcasts that never stop are programmed but kept out of the scan.
    assert {c.label for c in near if c.skip_scan} == {"BFI ATIS", "RNT ASOS"}
    # Spokane comes last, from the spare slots, programmed but not scanned.
    assert (local[-1].rx_freq_mhz, local[-1].skip_scan) == (132.1, True)
    assert [c.label for c in _block(resolved, "Airband Civil")] == ["Far outlet"]
    assert not _block(resolved, "Airport Towers")


def test_a_radio_without_uhf_airband_keeps_the_vhf_rows():
    freqs = {c.rx_freq_mhz for c in _block(_resolved("ftx1"), "Airports Near Home")}
    assert 257.8 not in freqs and {118.3, 119.2, 122.9} <= freqs


def test_the_td_h9_gets_the_nearest_towers_and_atis_in_its_few_slots():
    resolved = _resolved("td-h9")
    towers = _block(resolved, "Airport Towers")
    assert [c.label for c in towers] == ["RNT TWR", "BFI TWR 14L/32R", "BFI TWR 14R/32L", "BFI ATIS"]
    assert not _block(resolved, "Airports Near Home") and not _block(resolved, "Airband Civil")


def test_the_anytone_air_blocks_fit_its_am_air_list():
    air = [b for b in build_fleet_plan("at-d890uv").blocks if b.bank.startswith("Air")]
    assert [b.label for b in air] == ["Airports Near Home", "Airband Civil", "Airband Military SAR"]
    assert sum(b.limit for b in air) <= AM_AIR_MAX
    # nor may filling spare slots push them past it
    assert sum(b.fill_limit or b.limit for b in air) <= AM_AIR_MAX


def test_military_vhf_ops_reach_radios_that_can_program_am_there():
    ops = _frq("GRF", "ATCT", "GRF", "OPS", 138.6, (47.08, -122.58), name="GRAY AAF")
    catalog = Catalog(favorites=[build_faa_airband_favorite(washington() + [ops], home=HOME)])
    assert 138.6 in {c.rx_freq_mhz for c in resolve_plan(build_fleet_plan("th-d75"), catalog).channels}
    # The Anytone's main channel table has no AM; its air list stops at 137 MHz.
    assert 138.6 not in {c.rx_freq_mhz for c in resolve_plan(build_fleet_plan("at-d890uv"), catalog).channels}
