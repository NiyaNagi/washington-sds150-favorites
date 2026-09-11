"""FCC ULS: emission designators, filters, column detection and FCCDIG."""
from __future__ import annotations

import datetime
import io
import zipfile

import pytest

from conftest import FIXTURES_DIR
from wasds150.sources.base import RawDoc
from wasds150.sources.fcc_uls import FccUlsSource, is_emission_designator, mode_from_emission

HOME = (47.6351, -121.9954)
TODAY = datetime.date(2026, 9, 10)


def _row(values, length=30):
    cells = [""] * length
    for index, value in values.items():
        cells[index] = value
    return "|".join(cells)


def _licence(usi, call, status, service, expires, name, freq, emission, lat, lon, county="KING", state="WA"):
    """One licence in the FCC public-access (documented) layout."""
    return {
        "HD": _row({0: "HD", 1: usi, 4: call, 5: status, 6: service, 7: "01/01/2020", 8: expires}),
        "EN": _row({0: "EN", 1: usi, 4: call, 7: name, 16: "SEATTLE", 17: state}),
        "LO": _row({0: "LO", 1: usi, 8: "1", 11: "1 MAIN ST", 12: "TOWN", 13: county, 14: state,
                    19: lat[0], 20: lat[1], 21: lat[2], 22: "N", 23: lon[0], 24: lon[1], 25: lon[2], 26: "W"}),
        "FR": _row({0: "FR", 1: usi, 4: call, 6: "1", 7: "1", 8: "FB2", 10: freq}),
        "EM": _row({0: "EM", 1: usi, 4: call, 5: "1", 6: "1", 7: freq, 9: emission}),
    }


LICENCES = [
    _licence("1", "WQAA111", "A", "IG", "01/01/2034", "ACME DMR", "451.125000", "7K60FXE", ("47", "38", "6.0"), ("121", "59", "43.0")),
    _licence("2", "WQBB222", "A", "PW", "01/01/2034", "SPOKANE FIRE", "154.250000", "11K2F3E",
             ("47", "39", "30.0"), ("117", "25", "30.0"), county="SPOKANE"),
    _licence("3", "WQCC333", "A", "IG", "01/01/2020", "EXPIRED CO", "452.000000", "4K00F1E", ("47", "38", "0.0"), ("122", "0", "0.0")),
    _licence("4", "WQDD444", "C", "IG", "01/01/2034", "CANCELLED CO", "453.000000", "8K10F1E", ("47", "38", "0.0"), ("122", "0", "0.0")),
]


def _zip(licences=LICENCES, em_override=None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for table in ("HD", "EN", "LO", "FR", "EM"):
            lines = [lic[table] for lic in licences]
            if table == "EM" and em_override is not None:
                lines = em_override
            z.writestr(f"{table}.dat", "\r\n".join(lines) + "\r\n")
    return buf.getvalue()


def _normalize(source, payload):
    return source.normalize(RawDoc(source_adapter="fcc_uls", payload=payload, fetched_at="2026-09-10T00:00:00+00:00"))


def test_emission_designators_become_modes():
    assert mode_from_emission("7K60FXE") == "DMR"
    assert mode_from_emission("4k00f1e") == "NXDN"
    assert mode_from_emission("8K30F7W") == "NXDN"
    assert mode_from_emission("8K10F1E") == "P25"
    assert mode_from_emission("11K2F3E") == "NFM"
    assert mode_from_emission("20K0F3E") == "FM"
    assert mode_from_emission("12K5F3E") == "NFM"
    assert mode_from_emission("25K0F3E") == "FM"
    assert mode_from_emission("16K0F1D") is None
    assert is_emission_designator("7K60FXE") and not is_emission_designator("FB2")


def test_documented_layout_reads_modes_positions_and_active_licences():
    result = _normalize(FccUlsSource(state="WA", today=TODAY), _zip())
    assert not result.warnings
    by_call = {f.raw["call_sign"]: f for f in result.facts}
    assert set(by_call) == {"WQAA111", "WQBB222"}  # expired and cancelled dropped
    acme = by_call["WQAA111"]
    assert acme.mode == "DMR" and acme.freq_mhz == pytest.approx(451.125)
    assert acme.raw["emissions"] == ["7K60FXE"]
    assert acme.lat == pytest.approx(47.635, abs=0.001) and acme.lon == pytest.approx(-121.995, abs=0.001)
    assert acme.county == "KING"
    assert by_call["WQBB222"].mode == "NFM"


def test_inactive_licences_can_be_kept():
    result = _normalize(FccUlsSource(state="WA", active_only=False, today=TODAY), _zip())
    assert {f.raw["call_sign"] for f in result.facts} == {"WQAA111", "WQBB222", "WQCC333", "WQDD444"}


def test_emission_filter_by_mode_or_designator():
    by_mode = _normalize(FccUlsSource(emissions=("dmr", "P25"), active_only=False, today=TODAY), _zip())
    assert {f.raw["call_sign"] for f in by_mode.facts} == {"WQAA111", "WQDD444"}
    by_code = _normalize(FccUlsSource(emissions=("11K2F3E",), today=TODAY), _zip())
    assert [f.raw["call_sign"] for f in by_code.facts] == ["WQBB222"]


def test_distance_filter_keeps_licences_near_home():
    result = _normalize(FccUlsSource(home=HOME, within_miles=60, today=TODAY), _zip())
    assert [f.raw["call_sign"] for f in result.facts] == ["WQAA111"]
    with pytest.raises(ValueError):
        FccUlsSource(within_miles=60)


def test_a_garbage_emission_column_warns_and_keeps_analog_facts():
    garbage = [_row({0: "EM", 1: lic["HD"].split("|")[1], 7: "x", 9: "NOTACODE"}) for lic in LICENCES]
    result = _normalize(FccUlsSource(today=TODAY), _zip(em_override=garbage))
    assert any("EM.dat emission" in w and "no candidate column" in w for w in result.warnings)
    assert {f.mode for f in result.facts} == {None}


def test_the_legacy_fixture_layout_still_parses_and_says_so():
    data = (FIXTURES_DIR / "sources" / "fcc_uls_lmpriv_sample.zip").read_bytes()
    result = _normalize(FccUlsSource(active_only=False), data)
    [fact] = result.facts
    assert fact.freq_mhz == pytest.approx(154.13) and fact.county == "THURSTON"
    assert any("FR.dat frequency" in w and "read column 8" in w for w in result.warnings)
    assert any("legacy layout" in w for w in result.warnings)


def test_several_services_in_one_payload():
    second = _licence("9", "WQZZ999", "A", "YG", "01/01/2034", "COMMERCIAL SMR", "856.1125", "8K10F1E",
                      ("47", "40", "0.0"), ("122", "10", "0.0"))
    source = FccUlsSource(services=("lmpriv", "lmcomm"), today=TODAY)
    result = _normalize(source, {"zips": {"lmpriv": _zip(), "lmcomm": _zip([second])}})
    assert {f.raw["call_sign"] for f in result.facts} == {"WQAA111", "WQBB222", "WQZZ999"}
    assert any(f.source_url.endswith("l_LMcomm.zip") for f in result.facts)
    with pytest.raises(ValueError):
        FccUlsSource(services=("lmpriv", "pw"))


def test_fcc_digital_list_holds_only_digital_voice():
    from wasds150.recipes.fcc_digital import build_fcc_digital_favorite

    facts = _normalize(FccUlsSource(active_only=False, today=TODAY), _zip()).facts
    favorite = build_fcc_digital_favorite(facts)
    assert favorite.favorite_key == "FCCDIG" and favorite.enabled and not favorite.licensed
    departments = {d.label: [c.mode for c in d.channels] for d in favorite.systems[0].departments}
    assert departments == {"Industrial/Business Pool": ["DMR", "NXDN", "P25"]}
    channels = [c for d in favorite.systems[0].departments for c in d.channels]
    assert "SPOKANE FIRE" not in " ".join(c.label for c in channels)  # analog NFM is not digital voice
    assert all(c.lat is not None for c in channels)
    assert build_fcc_digital_favorite([]) is None


def _channel_counts(catalog):
    counts = {}
    for favorite in catalog.favorites:
        departments = [d for s in favorite.systems for d in list(s.departments) + [d for site in s.sites for d in site.departments]]
        counts[favorite.slug] = sum(len(d.channels) for d in departments)
    return counts


def test_land_mobile_frequencies_enrich_no_baseline_row_and_fccdig_is_built():
    """County and keyword matching would otherwise pour every licence in King
    or Spokane County into the public rows that name those counties."""
    from wasds150.catalog import baseline
    from wasds150.recipes.default_recipes import build_default_recipes
    from wasds150.recipes.engine import enrich_catalog

    catalog = baseline.load_baseline()
    recipes = build_default_recipes(catalog)
    # Enrichment also fills rollups, so compare against a run with no facts.
    before = _channel_counts(enrich_catalog(catalog, [], recipes).catalog)
    facts = _normalize(FccUlsSource(today=TODAY), _zip()).facts
    after = _channel_counts(enrich_catalog(catalog, facts, recipes).catalog)
    assert after.pop("fccdig") == 1
    assert after == before
