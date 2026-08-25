"""Puget Sound amateur repeater curation and HPE regressions."""
from __future__ import annotations

import csv
import io
import zipfile

from wasds150.bundle.hpe_export import build_per_list_hpe
from wasds150.catalog.baseline import load_baseline
from wasds150.catalog.puget_ham import favorite, system_from_wwara_facts
from wasds150.hpe.validation import require_valid_hpe_bytes
from wasds150.sources.base import RawDoc
from wasds150.sources.facts import NormalizedFact
from wasds150.sources.wwara import WwaraSource


def _fact(
    entity_key: str,
    frequency: float,
    mode: str,
    *,
    lat: float = 47.62,
    lon: float = -122.33,
    tone: str = "TONE=C103.5",
    raw=None,
) -> NormalizedFact:
    return NormalizedFact(
        entity_key=entity_key,
        fact_type="coordination",
        name="K7TEST",
        freq_mhz=frequency,
        offset_mhz=-0.6,
        tone=tone,
        mode=mode,
        lat=lat,
        lon=lon,
        source_id="wwara",
        source_url="https://example.test/repeater",
        raw=raw or {"CALL": "K7TEST", "CITY": "Seattle", "FM_WIDE": "Y"},
    )


def test_psham01_is_a_deterministic_baseline_extension_with_fallback_channels():
    catalog = load_baseline()
    item = next(favorite for favorite in catalog.favorites if favorite.favorite_key == "PSHAM01")
    channels = [channel for system in item.systems for department in system.departments for channel in department.channels]

    assert len(catalog.favorites) == 141
    assert len(channels) == 10
    assert {channel.freq_mhz for channel in channels} >= {52.87, 146.56, 146.82, 440.775}
    assert any("Saturday 20:00" in channel.notes for channel in channels)
    assert any(channel.mode == "DMR" and channel.tone == "ColorCode=2" for channel in channels)


def test_wwara_curation_filters_geography_frequency_and_duplicates_and_groups_modes():
    item = favorite()
    facts = [
        _fact("analog", 146.96, "FM"),
        _fact("analog-copy", 146.96, "FM"),
        _fact("p25", 442.1, "P25", tone="NAC=293", raw={"CALL": "K7P25", "CITY": "Tacoma", "P25_PHASE_1": "Y"}),
        _fact("dmr", 440.775, "DMR", tone="ColorCode=2", raw={"CALL": "K7DMR", "CITY": "Bellevue", "DMR": "Y"}),
        _fact("dstar", 443.5, "AUTO", tone="", raw={"CALL": "K7DSTAR", "CITY": "Caf\u00e9", "DSTAR_DV": "Y", "COMMENT": "Unicode \u2014 sanitized"}),
        _fact("outside", 147.0, "FM", lat=46.0),
        _fact("gap", 700.0, "FM"),
    ]
    system = system_from_wwara_facts(item, facts)

    assert system is not None
    departments = system.departments
    channels = [channel for department in departments for channel in department.channels]
    assert {channel.freq_mhz for channel in channels} == {146.96, 440.775, 442.1, 443.5}
    assert len([channel for channel in channels if channel.freq_mhz == 146.96]) == 1
    assert any(department.label.endswith("P25 Digital") for department in departments)
    assert any(department.label.endswith("DMR (Upgrade Required)") for department in departments)
    unsupported = next(department for department in departments if "Unsupported Digital" in department.label)
    assert unsupported.avoid is True
    assert all(channel.avoid for channel in unsupported.channels)
    assert all((channel.label + channel.notes).isascii() for channel in channels)
    assert all(department.lat is not None and department.range_miles for department in departments)


def _wwara_zip(rows):
    fields = [
        "FC_RECORD_ID", "OUTPUT_FREQ", "INPUT_FREQ", "STATE", "CITY", "CALL",
        "CTCSS_OUT", "DCS_CDCSS", "FM_WIDE", "FM_NARROW", "DSTAR_DV",
        "DMR", "DMR_COLOR_CODE", "FUSION", "P25_PHASE_1", "P25_PHASE_2",
        "P25_NAC", "URL", "LATITUDE", "LONGITUDE",
    ]
    text = io.StringIO()
    text.write("DATA_SPEC_VERSION=2015.2.2\n")
    writer = csv.DictWriter(text, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("WWARA-rptrlist-20260806.csv", text.getvalue())
    return payload.getvalue()


def test_wwara_normalizes_scanner_modes_and_signaling_metadata():
    common = {"STATE": "WA", "CITY": "Seattle", "LATITUDE": "47.6", "LONGITUDE": "-122.3"}
    rows = [
        dict(common, FC_RECORD_ID="1", CALL="K7FM", OUTPUT_FREQ="146.96", INPUT_FREQ="146.36", FM_WIDE="Y", CTCSS_OUT="103.5"),
        dict(common, FC_RECORD_ID="2", CALL="K7NFM", OUTPUT_FREQ="442.1", INPUT_FREQ="447.1", FM_NARROW="Y", DCS_CDCSS="023"),
        dict(common, FC_RECORD_ID="3", CALL="K7P25", OUTPUT_FREQ="443.1", INPUT_FREQ="448.1", P25_PHASE_1="Y", P25_NAC="293"),
        dict(common, FC_RECORD_ID="4", CALL="K7DMR", OUTPUT_FREQ="444.1", INPUT_FREQ="449.1", DMR="Y", DMR_COLOR_CODE="CC 7"),
        dict(common, FC_RECORD_ID="5", CALL="K7DS", OUTPUT_FREQ="445.1", INPUT_FREQ="440.1", DSTAR_DV="Y"),
    ]
    result = WwaraSource().normalize(RawDoc(source_adapter="wwara", payload=_wwara_zip(rows), fetched_at="2026-08-06T00:00:00+00:00"))
    by_call = {fact.raw["CALL"]: fact for fact in result.facts}

    assert (by_call["K7FM"].mode, by_call["K7FM"].tone) == ("FM", "TONE=C103.5")
    assert (by_call["K7NFM"].mode, by_call["K7NFM"].tone) == ("NFM", "D023")
    assert (by_call["K7P25"].mode, by_call["K7P25"].tone) == ("P25", "NAC=293")
    assert (by_call["K7DMR"].mode, by_call["K7DMR"].tone) == ("DMR", "ColorCode=7")
    assert (by_call["K7DS"].mode, by_call["K7DS"].tone) == ("AUTO", None)
    assert all(fact.source_updated == "2026-08-06" for fact in result.facts)


def test_combined_puget_ham_hpe_passes_semantic_validation():
    item = favorite()
    system = system_from_wwara_facts(item, [_fact("analog", 146.96, "FM"), _fact("dmr", 440.775, "DMR", tone="ColorCode=2", raw={"CALL": "K7DMR", "CITY": "Seattle", "DMR": "Y"})])
    assert system is not None
    item.systems.append(system)

    exported = build_per_list_hpe([item])
    data = exported.files["PSHAM01.hpe"]
    require_valid_hpe_bytes(item, data)
    assert not exported.warnings

