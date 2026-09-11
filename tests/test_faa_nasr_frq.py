"""FAA NASR facility frequencies (FRQ) with discovered columns."""
from __future__ import annotations

import io
import zipfile
from types import SimpleNamespace

import pytest

from wasds150.sources.base import RawDoc
from wasds150.sources.faa_nasr import CYCLE_ZIP_TTL_SECONDS, NASR_INDEX_URL, FaaNasrSource, discover_columns

EXPECTED_HEADER = "EFF_DATE,FAC_ID,FAC_TYPE,SERVICED_FACILITY,SERVICED_STATE,TOWER_OR_COMM_CALL,FREQ,FREQ_USE,LAT_DECIMAL,LONG_DECIMAL"
EXPECTED_ROWS = [
    "2026/09/03,BFI,ATCT,BFI,WA,BOEING TOWER,120.6,LCL/P,47.53,-122.30",
    "2026/09/03,RNT,ATCT,RNT,WA,RENTON TOWER,124.7,LCL/P,,",
    "2026/09/03,PDX,ATCT,PDX,OR,PORTLAND TOWER,118.1,LCL/P,45.59,-122.60",
    "2026/09/03,S43,NON-ATCT,S43,WA,HARVEY,N/A,CTAF,,",
    "2026/09/03,ZSE,ARTCC,ZSE,WA,SEATTLE CENTER,5000.0,HF,,",
]
APT_BASE = "ARPT_ID,STATE_CODE,ARPT_NAME,LAT_DECIMAL,LONG_DECIMAL\nRNT,WA,RENTON MUNI,47.49,-122.21\n"


def _nasr(files):
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w") as z:
        z.writestr("CSV_Data/10_Sep_2026_CSV.zip", inner.getvalue())
    return outer.getvalue()


def _normalize(source, files):
    raw = RawDoc(
        source_adapter="faa_nasr",
        payload={"zip_bytes": _nasr(files), "zip_url": "https://example.org/nasr.zip"},
        fetched_at="2026-09-10T00:00:00+00:00",
    )
    return source.normalize(raw)


def _frq_only():
    return FaaNasrSource(subjects=("FRQ",))


def test_expected_columns_give_located_facility_frequencies():
    files = {"FRQ.csv": EXPECTED_HEADER + "\n" + "\n".join(EXPECTED_ROWS) + "\n", "APT_BASE.csv": APT_BASE}
    result = _normalize(_frq_only(), files)
    assert not result.warnings
    by_freq = {f.freq_mhz: f for f in result.facts}
    assert set(by_freq) == {120.6, 124.7}
    boeing = by_freq[120.6]
    assert boeing.entity_key == "faa_nasr:frq:BFI:120.600:LCL/P"
    assert boeing.mode == "AM" and boeing.name == "BOEING TOWER LCL/P"
    assert (boeing.lat, boeing.lon) == (47.53, -122.30)
    renton = by_freq[124.7]
    assert (renton.lat, renton.lon) == (47.49, -122.21) and renton.location_precision == "exact"


def test_renamed_columns_are_discovered():
    header = "EFF_DATE,FACILITY_ID,STATE_CODE,FREQUENCY,USE,FACILITY_NAME"
    files = {"FRQ_BASE.csv": header + "\n2026/09/03,PAE,WA,132.95,LCL/P,PAINE FIELD TOWER\n"}
    result = _normalize(_frq_only(), files)
    [fact] = result.facts
    assert fact.freq_mhz == 132.95 and fact.name == "PAINE FIELD TOWER LCL/P"
    assert any("APT_BASE.csv not found" in w for w in result.warnings)


def test_a_file_without_a_frequency_column_is_skipped_with_its_header():
    files = {"FRQ.csv": "EFF_DATE,FAC_ID,SERVICED_STATE,CHANNEL\n2026/09/03,BFI,WA,120.6\n", "APT_BASE.csv": APT_BASE}
    result = _normalize(_frq_only(), files)
    assert result.facts == []
    assert any("no column for freq" in w and "CHANNEL" in w for w in result.warnings)


def test_a_cycle_without_frq_warns_and_other_subjects_still_parse():
    result = _normalize(FaaNasrSource(), {"APT_BASE.csv": APT_BASE})
    assert any("FRQ*.csv not found" in w for w in result.warnings)


def test_subjects_choose_what_is_read():
    files = {"FRQ.csv": EXPECTED_HEADER + "\n" + EXPECTED_ROWS[0] + "\n", "APT_BASE.csv": APT_BASE}
    result = _normalize(_frq_only(), files)
    assert not any("NAV_BASE" in w or "COM.csv" in w for w in result.warnings)
    with pytest.raises(ValueError):
        FaaNasrSource(subjects=("FRQ", "TWR"))


def test_an_ndb_frequency_in_kilohertz_is_not_read_as_megahertz():
    header = "EFF_DATE,FACILITY,FACILITY_TYPE,SERVICED_FACILITY,SERVICED_STATE,SERVICED_SITE_TYPE,FREQ,FREQ_USE,LAT_DECIMAL,LONG_DECIMAL"
    rows = [
        "2026/08/06,AW,NAVAID,AW,WA,NDB,382.0,AW NDB,47.9,-122.3",
        "2026/08/06,BFI,ATCT,BFI,WA,AIRPORT,118.3,LCL/P,47.53,-122.30",
    ]
    result = _normalize(_frq_only(), {"FRQ.csv": header + "\n" + "\n".join(rows) + "\n", "APT_BASE.csv": APT_BASE})
    assert [f.freq_mhz for f in result.facts] == [118.3]


CURRENT = "https://nfdc.faa.gov/webContent/28DaySub/28DaySubscription_Effective_2026-08-06.zip"
OLD = "https://nfdc.faa.gov/webContent/28DaySub/28DaySubscription_Effective_2026-07-09.zip"


class _Http:
    def __init__(self, store=None):
        self.calls = []
        self.store = store

    def fetch(self, url, *, ttl_seconds, source_id, max_bytes=None, force=False):
        self.calls.append((url, ttl_seconds))
        if url == NASR_INDEX_URL:
            return SimpleNamespace(content=f'<a href="{CURRENT}">Current</a> <a href="{OLD}">Previous</a>'.encode())
        return SimpleNamespace(content=b"zip")


def test_the_index_is_checked_daily_and_a_cycle_zip_downloaded_once():
    http = _Http()
    FaaNasrSource().fetch(http)
    assert http.calls == [(NASR_INDEX_URL, 24 * 3600), (CURRENT, CYCLE_ZIP_TTL_SECONDS)]
    # So the one-step update refreshes it: no more "tick it once a month".
    assert FaaNasrSource.bulk is False


def test_discover_columns_is_case_insensitive():
    assert discover_columns(["freq", "Serviced_State"], {"freq": ("FREQ",), "state": ("SERVICED_STATE",), "x": ("X",)}) == {
        "freq": "freq", "state": "Serviced_State", "x": None,
    }
