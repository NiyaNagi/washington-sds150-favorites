"""Whole-plan source records stay in their own lists.

WWARA and IACC once filled a "Channels" department of every list whose text
mentioned "amateur", "ham" or "IACC"; the USCG marine plan did the same to
every list that said "marine", and every rollup copied them again. See
wasds150.recipes.systems.strip_misfiled_source_copies.
"""
import copy

from wasds150.models.catalog import CSV_FIELDS, Catalog, Channel, Department, FavoritesList, System
from wasds150.recipes.systems import (
    SOURCE_HOMES,
    populate_rollups,
    strip_misfiled_source_copies,
    systems_from_flat_facts,
)
from wasds150.sources.facts import NormalizedFact
from wasds150.util.hashing import stable_id


def _fl(key, *systems, category=""):
    row = {name: "" for name in CSV_FIELDS}
    row.update(favorite_key=key, favorite_name=f"{key} list", system_or_category=category)
    favorite = FavoritesList.from_csv_row(row)
    favorite.systems = list(systems)
    return favorite


def _fact(source, name, freq, key, mode="FM"):
    return NormalizedFact(entity_key=key, fact_type="coordination", name=name, freq_mhz=freq, mode=mode, source_id=source)


def _labels(catalog, key):
    favorite = next(f for f in catalog.favorites if f.favorite_key == key)
    return sorted(c.label for s in favorite.systems for d in s.departments for c in d.channels)


def _system(system_id, *channels):
    return System(id=system_id, label=system_id, departments=[Department(id=f"{system_id}:d", label="Channels", channels=list(channels))])


def test_a_sources_records_go_only_to_its_home_list():
    facts = [
        _fact("iacc", "N7RHT (Leavenworth, Chelan Co.)", 146.78, "iacc:1"),
        _fact("wwara", "WW7CH (Ashford)", 146.78, "wwara:2"),
        _fact("uscg_navcen", "Marine VHF Ch 16", 156.8, "uscg:16"),
        _fact("noaa_nwr", "NOAA Weather Radio Seattle", 162.55, "noaa:3"),
        _fact("faa_nasr", "BFI Tower", 120.6, "faa:4", mode="AM"),
        _fact("nifc", "NIFC Air Guard", 168.625, "nifc:5"),
    ]
    # A mountain list that mentions IACC, marine and weather keeps only what
    # no whole-plan source owns.
    mountain = systems_from_flat_facts(_fl("FL37"), facts)
    assert [[c.label for d in s.departments for c in d.channels] for s in mountain] == [["NIFC Air Guard"]]
    home = systems_from_flat_facts(_fl("FL60"), facts)
    by_system = {s.label: [c.label for d in s.departments for c in d.channels] for s in home}
    assert by_system == {"FL60 list": ["NIFC Air Guard"], "FL60 list - Coordinated": ["N7RHT (Leavenworth, Chelan Co.)"]}
    marine = systems_from_flat_facts(_fl("FL52"), facts)
    assert [c.label for s in marine for d in s.departments for c in d.channels] == ["Marine VHF Ch 16", "NIFC Air Guard"]
    # WWARA's home rebuilds from its own records; FAAAIR is built on its own.
    assert SOURCE_HOMES["wwara"] == "PSHAM01" and SOURCE_HOMES["faa_nasr"] == "FAAAIR"


def test_copies_already_in_a_catalog_come_out_of_every_list_and_rollup():
    aggregate = _system(
        stable_id("fl51:public-facts", kind="system"),
        Channel(id="a", label="WW7CH (Ashford)", freq_mhz=146.78, tone="TONE=C103.5"),
        Channel(id="b", label="ISS [FM]", freq_mhz=145.8),
        Channel(id="c", label="Marine VHF Ch 16", freq_mhz=156.8),
        Channel(id="d", label="NOAA Weather Radio Seattle", freq_mhz=162.55),
        Channel(id="d2", label="NOAA Weather WX1", freq_mhz=162.55),
        Channel(id="e", label="AL AL NDB", freq_mhz=353.0, mode="AM"),
        Channel(id="f", label="Seattle Center", freq_mhz=353.0, mode="AM"),
    )
    marine = _system(stable_id("fl52:public-facts", kind="system"), Channel(id="g", label="Marine VHF Ch 16", freq_mhz=156.8))
    weather = _system(stable_id("fl75:public-facts", kind="system"), Channel(id="h", label="NOAA Weather Radio Seattle", freq_mhz=162.55))
    curated = _system("fl60:static", Channel(id="i", label="WW7CH (Ashford)", freq_mhz=146.78))
    coordination = _system(stable_id("fl60:coordination", kind="system"), Channel(id="j", label="N7RHT (Leavenworth)", freq_mhz=146.78))
    catalog = Catalog(favorites=[
        _fl("FL51", aggregate),
        _fl("FL52", marine),
        _fl("FL60", curated, coordination),
        _fl("FL75", weather),
        # A rollup's copies: FL51's and FL52's systems, and FL60's coordination.
        _fl("OUT01", copy.deepcopy(aggregate), copy.deepcopy(marine), copy.deepcopy(coordination)),
    ])
    assert strip_misfiled_source_copies(catalog) == 11
    # Only the misfiled copies and the kilohertz beacon go.
    assert _labels(catalog, "FL51") == ["ISS [FM]", "Seattle Center"]
    assert _labels(catalog, "OUT01") == ["ISS [FM]", "Marine VHF Ch 16", "Seattle Center"]
    # Home lists, curated systems and the coordinator's own system stay.
    assert _labels(catalog, "FL52") == ["Marine VHF Ch 16"]
    assert _labels(catalog, "FL75") == ["NOAA Weather Radio Seattle"]
    assert _labels(catalog, "FL60") == ["N7RHT (Leavenworth)", "WW7CH (Ashford)"]


def test_a_rollup_does_not_copy_a_coordinators_repeaters():
    curated = _system("fl60:static", Channel(id="a", label="Seattle", freq_mhz=146.82))
    coordination = _system(stable_id("fl60:coordination", kind="system"), Channel(id="b", label="W7UPS (Kennewick)", freq_mhz=145.39))
    catalog = Catalog(favorites=[_fl("FL60", curated, coordination), _fl("OUT09", category="Trip rollup (reuses FL60)")])
    populate_rollups(catalog)
    assert _labels(catalog, "OUT09") == ["Seattle"]


def test_a_coordinated_repeater_carries_its_input_and_access_tone():
    fact = NormalizedFact(entity_key="iacc:W7UPS:145.39", fact_type="coordination", name="W7UPS (Spokane, Spokane Co.)",
                          freq_mhz=145.39, offset_mhz=-0.6, tone="TONE=C100", mode="FM", county="Spokane",
                          source_id="iacc", raw={"tx_tone": "TONE=C100"})
    [coordination] = systems_from_flat_facts(_fl("FL60"), [fact])
    channel = coordination.departments[0].channels[0]
    # Without the input a memory radio transmits simplex on the output.
    assert (channel.tx_freq_mhz, channel.tx_tone) == (144.79, "TONE=C100")
    assert channel.lat is None  # no invented position: it is not a nearby station
    # The same call on the same output in another city is another station.
    kennewick = NormalizedFact(entity_key="iacc:W7UPS:145.39", fact_type="coordination", name="W7UPS (Kennewick, Benton Co.)",
                               freq_mhz=145.39, offset_mhz=-0.6, mode="FM", source_id="iacc", raw={"tx_tone": "TONE=C103.5"})
    [both] = systems_from_flat_facts(_fl("FL60"), [fact, kennewick])
    assert len({c.id for c in both.departments[0].channels}) == 2


def test_a_radios_own_list_does_not_name_another_areas_toneless_copies():
    from wasds150.catalog.labels import StationLabels
    from wasds150.catalog.wa_counties import county_point

    snohomish = county_point("Snohomish")
    fence = Department(id="rr", label="ARES", lat=snohomish.lat, lon=snohomish.lon, range_miles=snohomish.radius_miles)
    ares = Channel(id="rr1", label="Snohomish Co ACS / ARES", freq_mhz=440.325, mode="FM", tx_freq_mhz=445.325)
    wwara = Channel(id="w1", label="NR7SS - Granite Falls", freq_mhz=440.325, mode="FM", tx_freq_mhz=445.325,
                    lat=48.13612, lon=-121.98231)
    imported = Channel(id="f1", label="W6TQF", freq_mhz=440.325, mode="FM", tx_freq_mhz=445.325,
                       tone="TONE=C100", tx_tone="TONE=C100")
    labels = StationLabels(
        [("PSHAM01", None, wwara), ("FTX01", None, imported), ("RRC-SNOHOMISH", fence, ares)],
        home=(47.6351, -121.9954),
    )
    assert labels.label(fence, ares) == "NR7SS - Granite Falls"
    assert labels.label(None, imported) == "W6TQF"  # the import keeps its own name


def test_a_record_with_no_position_does_not_rename_a_station_far_from_home():
    from wasds150.catalog.labels import StationLabels
    from wasds150.catalog.wa_counties import county_point

    kitsap = county_point("Kitsap")
    fence = Department(id="rr", label="70 cm", lat=kitsap.lat, lon=kitsap.lon, range_miles=kitsap.radius_miles)
    county = Channel(id="rr1", label="Kitsap 444.875", freq_mhz=444.875, mode="FM", tx_freq_mhz=449.875, tone="TONE=C100")
    from wasds150.catalog.labels import COORDINATED_DEPARTMENT

    iacc = Channel(id="i1", label="WB7WHF (Prosser, Benton Co.)", freq_mhz=444.875, mode="FM", tx_freq_mhz=449.875,
                   tone="TONE=C100", tx_tone="TONE=C100")
    statewide = Department(id="c", label=COORDINATED_DEPARTMENT)
    labels = StationLabels([("RRC-KITSAP", fence, county), ("FL60", statewide, iacc)], home=(47.6351, -121.9954))
    assert labels.label(fence, county) == "Kitsap 444.875"


def test_a_curated_channel_with_no_position_keeps_its_name():
    from wasds150.catalog.labels import StationLabels
    from wasds150.catalog.wa_counties import county_point

    jefferson = county_point("Jefferson")
    fence = Department(id="rr", label="70 cm", lat=jefferson.lat, lon=jefferson.lon, range_miles=jefferson.radius_miles)
    county = Channel(id="rr1", label="K7SCN Buck Analog", freq_mhz=440.95, mode="FM", tx_freq_mhz=445.95,
                     tone="TONE=C110.9", tx_tone="TONE=C110.9")
    acs = Channel(id="a1", label="U92 Buck Mt", freq_mhz=440.95, mode="FM", tx_freq_mhz=445.95,
                  tone="TONE=C110.9", tx_tone="TONE=C110.9")
    # A machine around home on the same pair names a copy only from a better source.
    federal_way = Channel(id="w1", label="WA7FW - Federal Way", freq_mhz=146.84, mode="FM", tx_freq_mhz=146.24,
                          lat=47.31, lon=-122.33)
    larch = Channel(id="a2", label="V86 Larch Mt", freq_mhz=146.84, mode="FM", tx_freq_mhz=146.24)
    imported = Channel(id="f1", label="W7LT", freq_mhz=146.84, mode="FM", tx_freq_mhz=146.24)
    # With the access tone to say it is that machine, the coordinated call wins.
    psr = Channel(id="w2", label="WW7PSR Seattle 2m", freq_mhz=146.96, mode="FM", tx_freq_mhz=146.36,
                  tone="TONE=C103.5", tx_tone="TONE=C103.5", lat=47.6, lon=-122.33)
    v01 = Channel(id="a3", label="V01 PSRG", freq_mhz=146.96, mode="FM", tx_freq_mhz=146.36,
                  tone="TONE=C103.5", tx_tone="TONE=C103.5")
    labels = StationLabels(
        [("RRC-JEFFERSON", fence, county), ("SEAACS", None, acs), ("PSHAM01", None, federal_way),
         ("SEAACS", None, larch), ("FTX01", None, imported), ("PSHAM01", None, psr), ("SEAACS", None, v01)],
        home=(47.6351, -121.9954),
    )
    assert labels.label(None, acs) == "U92 Buck Mt"
    # The tone says the county list's copy is the same machine; the curated name wins.
    assert labels.label(fence, county) == "U92 Buck Mt"
    assert labels.label(None, larch) == "V86 Larch Mt"
    assert labels.label(None, imported) == "WA7FW - Federal Way"  # a radio's own import defers to WWARA
    assert labels.label(None, v01) == "WW7PSR Seattle 2m"
