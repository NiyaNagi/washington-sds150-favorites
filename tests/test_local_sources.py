"""Tests for the local-only sources: Sentinel HPDB reader and
RadioReference Premium safe import (see each module's docstring for the
"user-local only / no redistribution" and "no unverified SOAP" safety
constraints these tests also help enforce)."""
from __future__ import annotations

from pathlib import Path

import pytest

from wasds150.sources.base import RawDoc

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# ------------------------------------------------------------ sentinel_local
def test_sentinel_local_via_mount_point(tmp_path, synthetic_hpdb_cfg_path, synthetic_hpdb_state_path):
    from wasds150.sources.sentinel_local import SentinelLocalSource

    hpdb_dir = tmp_path / "SDCARD" / "BCDx36HP" / "HPDB"
    hpdb_dir.mkdir(parents=True)
    (hpdb_dir / "hpdb.cfg").write_bytes(synthetic_hpdb_cfg_path.read_bytes())
    (hpdb_dir / "s_000053.hpd").write_bytes(synthetic_hpdb_state_path.read_bytes())

    source = SentinelLocalSource(mount_point=tmp_path / "SDCARD")
    raw = source.fetch()
    result = source.normalize(raw)
    assert result.facts
    assert all(f.source_id == "sentinel_local" for f in result.facts)
    assert not result.warnings


def test_sentinel_local_via_hpdb_cfg_path(tmp_path, synthetic_hpdb_cfg_path, synthetic_hpdb_state_path):
    from wasds150.sources.sentinel_local import SentinelLocalSource

    hpdb_dir = tmp_path / "copied_hpdb"
    hpdb_dir.mkdir()
    (hpdb_dir / "hpdb.cfg").write_bytes(synthetic_hpdb_cfg_path.read_bytes())
    (hpdb_dir / "s_000053.hpd").write_bytes(synthetic_hpdb_state_path.read_bytes())

    source = SentinelLocalSource(hpdb_cfg_path=hpdb_dir / "hpdb.cfg")
    raw = source.fetch()
    result = source.normalize(raw)
    assert result.facts


def test_sentinel_local_no_card_no_facts(tmp_path):
    from wasds150.sources.sentinel_local import SentinelLocalSource

    source = SentinelLocalSource(mount_point=tmp_path / "not-a-card")
    raw = source.fetch()
    assert raw.payload is None
    result = source.normalize(raw)
    assert result.facts == []
    assert result.warnings


def test_sentinel_local_rejects_both_paths(tmp_path):
    from wasds150.sources.sentinel_local import SentinelLocalSource

    with pytest.raises(ValueError):
        SentinelLocalSource(mount_point=tmp_path, hpdb_cfg_path=tmp_path / "hpdb.cfg")


def test_discover_local_hpdb_paths_finds_card_with_marker(tmp_path, synthetic_hpdb_cfg_path):
    from wasds150.sources.sentinel_local import discover_local_hpdb_paths

    card = tmp_path / "MYCARD"
    hpdb_dir = card / "BCDx36HP" / "HPDB"
    hpdb_dir.mkdir(parents=True)
    (hpdb_dir / "hpdb.cfg").write_bytes(synthetic_hpdb_cfg_path.read_bytes())
    not_a_card = tmp_path / "OTHERDIR"
    not_a_card.mkdir()

    found = discover_local_hpdb_paths([card, not_a_card])
    assert found == [card]


# ------------------------------------------------------ radioreference_premium
def test_rr_premium_csv_import(tmp_path):
    from wasds150.sources.radioreference_premium import RadioReferencePremiumSource

    csv_path = tmp_path / "export.csv"
    csv_path.write_text(
        "County,System,Site,Description,Tag,Frequency,Tone\n"
        "King,King Co Sheriff,Site 1,Dispatch,Main,154.905000,127.3\n",
        encoding="utf-8",
    )
    source = RadioReferencePremiumSource(export_path=csv_path)
    raw = source.fetch()
    result = source.normalize(raw)
    assert len(result.facts) == 1
    fact = result.facts[0]
    assert fact.freq_mhz == pytest.approx(154.905)
    assert fact.county == "King"
    assert fact.source_id == "radioreference_premium"
    assert result.warnings  # always reminds caller mapping is best-effort


def test_rr_premium_xml_import(tmp_path):
    from wasds150.sources.radioreference_premium import RadioReferencePremiumSource

    xml_path = tmp_path / "export.xml"
    xml_path.write_text(
        "<Export><Record><County>King</County><System>King Co Sheriff</System>"
        "<Description>Dispatch</Description><Frequency>154.905000</Frequency>"
        "<Tone>127.3</Tone></Record></Export>",
        encoding="utf-8",
    )
    source = RadioReferencePremiumSource(export_path=xml_path)
    raw = source.fetch()
    result = source.normalize(raw)
    assert len(result.facts) == 1
    assert result.facts[0].freq_mhz == pytest.approx(154.905)


def test_rr_premium_no_export_configured():
    from wasds150.sources.radioreference_premium import RadioReferencePremiumSource

    source = RadioReferencePremiumSource()
    raw = source.fetch()
    result = source.normalize(raw)
    assert result.facts == []
    assert result.warnings


def test_rr_premium_missing_file_raises(tmp_path):
    from wasds150.sources.radioreference_premium import RadioReferencePremiumSource

    source = RadioReferencePremiumSource(export_path=tmp_path / "nope.csv")
    with pytest.raises(FileNotFoundError):
        source.fetch()


def test_rr_premium_soap_not_implemented_raises_precise_error():
    from wasds150.sources.radioreference_premium import (
        RadioReferenceCredentials,
        RadioReferencePremiumSource,
        RadioReferenceSoapNotImplemented,
    )

    creds = RadioReferenceCredentials(username="u", password="p", app_key="k")
    source = RadioReferencePremiumSource(credentials=creds)
    with pytest.raises(RadioReferenceSoapNotImplemented) as excinfo:
        source.fetch()
    assert "export" in str(excinfo.value).lower()


def test_rr_premium_credentials_never_repr_secrets():
    from wasds150.sources.radioreference_premium import RadioReferenceCredentials

    creds = RadioReferenceCredentials(username="u", password="hunter2", app_key="k")
    assert "hunter2" not in repr(creds)
    assert "hunter2" not in str(creds)


def test_rr_premium_incomplete_credentials_not_configured():
    from wasds150.sources.radioreference_premium import RadioReferenceCredentials

    creds = RadioReferenceCredentials(username="u", password="", app_key="k")
    assert creds.is_configured() is False
