"""Adapter-level tests for every phase-4 online/local source, each using
an offline fixture derived from real data captured during implementation
(see each adapter module's docstring for provenance/verification notes).
No test in this file touches the network.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from wasds150.sources.base import RawDoc

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sources"


# ------------------------------------------------------------------ NOAA ---
def test_noaa_nwr_parses_ccl_data_js():
    from wasds150.sources.noaa_wx import NoaaNwrSource

    source = NoaaNwrSource()
    text = (FIXTURES / "noaa_nwr_ccl_data_sample.js").read_text(encoding="utf-8")
    raw = RawDoc(source_adapter="noaa_nwr", payload=text, fetched_at="2026-01-01T00:00:00+00:00")
    result = source.normalize(raw)
    assert result.facts
    assert all(f.fact_type == "station" for f in result.facts)
    assert all(f.freq_mhz for f in result.facts)
    assert not result.warnings


# -------------------------------------------------------------- USCG NAVCEN
def test_uscg_navcen_parses_two_tables():
    from wasds150.sources.uscg_navcen import UscgNavcenSource

    source = UscgNavcenSource()
    text = (FIXTURES / "uscg_navcen_vhf_sample.html").read_text(encoding="utf-8")
    raw = RawDoc(source_adapter="uscg_navcen", payload=text, fetched_at="2026-01-01T00:00:00+00:00")
    result = source.normalize(raw)
    assert result.facts
    kinds = {f.fact_type for f in result.facts}
    assert kinds <= {"channel_plan", "frequency"}


# ------------------------------------------------------------------- AMSAT-
def test_amsat_parses_catalog_json():
    from wasds150.sources.amsat import AmsatSource

    source = AmsatSource()
    data = (FIXTURES / "amsat_catalog_sample.json").read_bytes().decode("utf-8")
    raw = RawDoc(source_adapter="amsat", payload=data, fetched_at="2026-01-01T00:00:00+00:00")
    result = source.normalize(raw)
    assert len(result.facts) == 3
    assert {f.entity_key for f in result.facts} == {"amsat:153", "amsat:2", "amsat:7"}


# ------------------------------------------------------------------- WWARA-
def test_wwara_parses_wa_repeaters_from_zip():
    from wasds150.sources.wwara import WwaraSource

    source = WwaraSource()
    data = (FIXTURES / "wwara_sample_extract.zip").read_bytes()
    raw = RawDoc(source_adapter="wwara", payload=data, fetched_at="2026-01-01T00:00:00+00:00")
    result = source.normalize(raw)
    assert result.facts
    assert all(f.fact_type == "coordination" for f in result.facts)
    assert all(f.freq_mhz for f in result.facts)


# --------------------------------------------------------------------- IACC
def test_iacc_parses_wa_only_from_mixed_wa_id_table():
    from wasds150.sources.iacc import IaccSource

    source = IaccSource()
    text = (FIXTURES / "iacc_repeaters_sample.html").read_text(encoding="utf-8")
    raw = RawDoc(source_adapter="iacc", payload=text, fetched_at="2026-01-01T00:00:00+00:00")
    result = source.normalize(raw)
    assert len(result.facts) == 4  # fixture has 4 WA rows + 1 Idaho row that must be excluded
    assert all(f.fact_type == "coordination" for f in result.facts)
    counties = {f.county for f in result.facts}
    assert "Kootenai" not in counties  # Idaho county must never leak through


# ----------------------------------------------------------------- FAA NASR
def test_faa_nasr_parses_nav_and_com_facts():
    from wasds150.sources.faa_nasr import FaaNasrSource

    source = FaaNasrSource()
    data = (FIXTURES / "faa_nasr_sample.zip").read_bytes()
    raw = RawDoc(
        source_adapter="faa_nasr",
        payload={"zip_bytes": data, "zip_url": "https://example.org/test.zip"},
        fetched_at="2026-01-01T00:00:00+00:00",
    )
    result = source.normalize(raw)
    station_facts = [f for f in result.facts if f.fact_type == "station"]
    doc_ref_facts = [f for f in result.facts if f.fact_type == "doc_ref"]
    assert station_facts
    assert doc_ref_facts
    walla_walla = next(f for f in station_facts if "WALLA WALLA" in f.name)
    assert walla_walla.freq_mhz == pytest.approx(116.4)


# ------------------------------------------------------------------ FCC ULS
def test_fcc_uls_parses_hd_en_lo_fr_join():
    from wasds150.sources.fcc_uls import FccUlsSource

    source = FccUlsSource(service="lmpriv", state="WA")
    data = (FIXTURES / "fcc_uls_lmpriv_sample.zip").read_bytes()
    raw = RawDoc(source_adapter="fcc_uls", payload=data, fetched_at="2026-01-01T00:00:00+00:00")
    result = source.normalize(raw)
    assert len(result.facts) == 1
    fact = result.facts[0]
    assert fact.fact_type == "frequency"
    assert fact.freq_mhz == pytest.approx(154.13)
    assert fact.county == "THURSTON"
    assert fact.lat is not None and fact.lon is not None
    assert "WASHINGTON STATE PATROL" in fact.name


def test_fcc_uls_unknown_service_rejected():
    from wasds150.sources.fcc_uls import FccUlsSource

    with pytest.raises(ValueError):
        FccUlsSource(service="not_a_real_service")


def test_fcc_uls_filters_out_of_state(tmp_path):
    import io
    import zipfile

    from wasds150.sources.fcc_uls import FccUlsSource

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("HD.dat", "HD|1|f||CALL1|A|PW|||\r\n")
        z.writestr("EN.dat", "EN|1||||L|LX|Some Entity|||||||street|city|OR|97000\r\n")
        z.writestr("LO.dat", "")
        z.writestr("FR.dat", "")
    source = FccUlsSource(state="WA")
    raw = RawDoc(source_adapter="fcc_uls", payload=buf.getvalue(), fetched_at="2026-01-01T00:00:00+00:00")
    result = source.normalize(raw)
    assert result.facts == []


# -------------------------------------------------------------------- NWAC-
def _fake_http_client(seen=None):
    class FakeResult:
        def __init__(self, status):
            self.status = status

    class FakeStore:
        def __init__(self, seen):
            self.seen = seen

        def get(self, url):
            return {"x": 1} if url in self.seen else None

    class FakeHttpClient:
        def __init__(self, seen):
            self.store = FakeStore(seen)

        def fetch(self, url, ttl_seconds=0, source_id=None, max_bytes=None):
            was_new = url not in self.store.seen
            self.store.seen.add(url)
            return FakeResult("fetched" if was_new else "cached-fresh")

    return FakeHttpClient(seen if seen is not None else set())


def test_nwac_reports_og_image_as_new_change():
    from wasds150.sources.nwac import NwacSource

    source = NwacSource()
    html = (FIXTURES / "nwac_backcountry_radio_sample.html").read_text(encoding="utf-8")
    fake_client = _fake_http_client()
    raw = RawDoc(
        source_adapter="nwac", payload={"html": html, "http_client": fake_client}, fetched_at="2026-01-01T00:00:00+00:00"
    )
    result = source.normalize(raw)
    assert result.facts == []
    assert len(result.alerts) == 1
    assert result.alerts[0].kind == "new"
    assert "RadioChannelGraphic" in result.alerts[0].url


def test_nwac_missing_og_image_warns():
    from wasds150.sources.nwac import NwacSource

    source = NwacSource()
    fake_client = _fake_http_client()
    raw = RawDoc(
        source_adapter="nwac",
        payload={"html": "<html><body>no image here</body></html>", "http_client": fake_client},
        fetched_at="2026-01-01T00:00:00+00:00",
    )
    result = source.normalize(raw)
    assert result.warnings


# --------------------------------------------------------- change-detection
@pytest.mark.parametrize(
    "module_name,class_name,html,expected_url_fragment",
    [
        (
            "wa_emd",
            "WaEmdSource",
            '<html><a href="/asset/610b02188b53e/ESF4.pdf">ESF4</a></html>',
            "/asset/610b02188b53e/ESF4.pdf",
        ),
        (
            "wa_dnr",
            "WaDnrSource",
            '<html><a href="/documents/rp_fire_radio_frequencies.pdf">Radio Freqs</a></html>',
            "rp_fire_radio_frequencies.pdf",
        ),
        (
            "nifc",
            "NifcSource",
            '<html><a href="/docs/NIRSC_User_Guide_2026.pdf">User Guide</a></html>',
            "NIRSC_User_Guide_2026.pdf",
        ),
    ],
)
def test_document_change_detection_sources(module_name, class_name, html, expected_url_fragment):
    import importlib

    module = importlib.import_module(f"wasds150.sources.{module_name}")
    cls = getattr(module, class_name)
    source = cls()
    fake_client = _fake_http_client()
    raw = RawDoc(
        source_adapter=module_name, payload={"html": html, "http_client": fake_client}, fetched_at="2026-01-01T00:00:00+00:00"
    )
    result = source.normalize(raw)
    assert result.facts == []
    assert len(result.alerts) == 1
    assert result.alerts[0].kind == "new"
    assert expected_url_fragment in result.alerts[0].url


def test_document_change_detection_reports_unchanged_on_second_check():
    from wasds150.sources.wa_dnr import WaDnrSource

    source = WaDnrSource()
    html = '<html><a href="/documents/rp_fire_radio_frequencies.pdf">Radio Freqs</a></html>'
    seen = set()
    fake1 = _fake_http_client(seen)
    result1 = source.normalize(
        RawDoc(source_adapter="wa_dnr", payload={"html": html, "http_client": fake1}, fetched_at="t1")
    )
    assert result1.alerts[0].kind == "new"

    fake2 = _fake_http_client(seen)  # seen now contains the URL from fake1's mutation
    result2 = source.normalize(
        RawDoc(source_adapter="wa_dnr", payload={"html": html, "http_client": fake2}, fetched_at="t2")
    )
    assert result2.alerts[0].kind == "unchanged"
