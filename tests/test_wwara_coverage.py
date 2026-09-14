"""Every WWARA repeater is kept, NXDN is read, and coverage files repeaters
into the county and city lists it names."""
import csv
import io
import zipfile

from wasds150.catalog.puget_ham import favorite, system_from_wwara_facts
from wasds150.catalog.wwara_coverage import place_for, place_wwara_repeaters
from wasds150.models.catalog import CSV_FIELDS, Catalog, FavoritesList
from wasds150.sources.base import RawDoc
from wasds150.sources.wwara import WwaraSource

FIELDS = [
    "FC_RECORD_ID", "OUTPUT_FREQ", "INPUT_FREQ", "STATE", "CITY", "LOCALE", "CALL", "CTCSS_IN", "CTCSS_OUT",
    "DCS_CDCSS", "FM_WIDE", "FM_NARROW", "DSTAR_DV", "DMR", "DMR_COLOR_CODE", "FUSION", "P25_PHASE_1",
    "P25_PHASE_2", "P25_NAC", "NXDN_DIGITAL", "NXDN_MIXED", "NXDN_RAN", "LATITUDE", "LONGITUDE",
]


def _csv(rows):
    text = io.StringIO()
    text.write("DATA_SPEC_VERSION=2015.2.2\n")
    writer = csv.DictWriter(text, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return text.getvalue()


def _facts(current, pending=()):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("WWARA-rptrlist-20260913.csv", _csv(current))
        archive.writestr("WWARA-pending-rptrlist-20260913.csv", _csv(pending))
    return WwaraSource().normalize(RawDoc(source_adapter="wwara", payload=payload.getvalue(), fetched_at="2026-09-13")).facts


def _row(record, call, output, inp, locale, lat="47.6", lon="-122.3", **fields):
    row = dict(FC_RECORD_ID=record, CALL=call, OUTPUT_FREQ=output, INPUT_FREQ=inp, STATE="WA", CITY="Somewhere",
               LOCALE=locale, LATITUDE=lat, LONGITUDE=lon, FM_WIDE="Y", CTCSS_IN="100", CTCSS_OUT="100")
    row.update(fields)
    return row


def _channels(system):
    return [(d.label, c) for d in system.departments for c in d.channels]


def test_a_pending_dual_mode_record_gives_an_fm_and_an_nxdn_channel():
    bremerton = _row("5649", "N7MTC", "443.0500", "448.0500", "KITSAP COUNTY", lat="47.63", lon="-122.61")
    tiger = _row("5668", "KC7BAE", "443.0500", "448.0500", "PUGET SOUND", lat="47.48888", lon="-121.9455",
                 CTCSS_IN="103.5", CTCSS_OUT="103.5", NXDN_DIGITAL="Y", NXDN_MIXED="N", NXDN_RAN="5")
    facts = _facts([bremerton], pending=[tiger, dict(bremerton)])  # a pending copy of a current record is not doubled
    assert sorted((f.raw["CALL"], f.mode, f.nxdn_ran) for f in facts) == [
        ("KC7BAE", "FM", None), ("KC7BAE", "NXDN", 5), ("N7MTC", "FM", None)]

    channels = _channels(system_from_wwara_facts(favorite(), facts))
    nxdn = [(label, c) for label, c in channels if c.mode == "NXDN"]
    assert len(nxdn) == 1
    label, channel = nxdn[0]
    assert label.endswith("NXDN Digital")
    assert (channel.nxdn_ran, channel.tx_freq_mhz, channel.tone) == (5, 448.05, "")
    # Its FM twin shares the output, so the scanner needs the two told apart.
    assert channel.label.endswith(" NXDN")
    assert "coordination pending" in channel.notes and "RAN 5" in channel.notes


def test_links_are_their_own_department_and_the_southwest_is_kept():
    facts = _facts([
        _row("1", "W7AVM", "430.7750", "439.7750", "LINK", lat="48.2", lon="-122.68"),
        _row("2", "NM7R", "147.1800", "147.7800", "PACIFIC COUNTY", lat="46.26", lon="-123.9"),
    ])
    by_call = {c.label.split(" - ")[0]: (label, c) for label, c in _channels(system_from_wwara_facts(favorite(), facts))}
    assert by_call["W7AVM"][0].endswith("Link Frequencies")
    assert by_call["W7AVM"][1].avoid  # never programmed on a transceiver
    assert by_call["NM7R"][0] == "Southwest & Coast - Analog 2 Meter"


def test_coverage_names_a_county_a_city_or_nothing():
    assert place_for("KING COUNTY-SOUTH") == ("King", None)
    assert place_for("COWLITZCOUNTY") == ("Cowlitz", None)
    assert place_for("KING COUNY") == ("King", None)
    assert place_for("GRAYS HARBOR COUNTY") == ("Grays Harbor", None)
    assert place_for("REDMOND") == ("King", "Redmond")
    assert place_for("PUGET SOUND-SOUTH") is None
    assert place_for("LINK") is None


def _list(key, name):
    row = {field: "" for field in CSV_FIELDS}
    row.update(favorite_key=key, favorite_name=name)
    return FavoritesList.from_csv_row(row)


def test_repeaters_join_the_county_and_city_lists_their_coverage_names():
    facts = _facts([
        _row("1", "KC7IYE", "53.0700", "51.3700", "REDMOND"),
        _row("2", "K7LWH", "443.0625", "448.0625", "KING COUNTY", FM_WIDE="N", DSTAR_DV="Y"),
        _row("3", "W7DMR", "440.1000", "445.1000", "KING COUNTY", FM_WIDE="N", DMR="Y", DMR_COLOR_CODE="1"),
        _row("4", "KF7T", "53.1300", "51.4300", "SNOHOMISH COUNTY"),
        _row("5", "WW7PSR", "146.9600", "146.3600", "PUGET SOUND"),
    ])
    psham = favorite()
    psham.systems.append(system_from_wwara_facts(psham, facts))
    king, redmond = _list("RRC-KING", "RadioReference - King County"), _list("KC29", "Redmond Local")
    catalog = Catalog(favorites=[psham, king, redmond])

    assert place_wwara_repeaters(catalog) == 2
    assert place_wwara_repeaters(catalog) == 2  # rebuilt, never doubled
    for item in (king, redmond):
        [system] = item.systems
        assert [c.label for d in system.departments for c in d.channels] == ["KC7IYE - Somewhere"]
        assert system.departments[0].label == "WWARA Analog 6 Meter"
    # A D-STAR or DMR machine, a county with no list, and a regional machine stay in PSHAM01 alone.
