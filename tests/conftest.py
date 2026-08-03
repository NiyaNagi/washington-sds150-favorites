"""Shared pytest fixtures for the wasds150 test suite."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from wasds150.models.catalog import CSV_FIELDS

REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_CSV_PATH = REPO_ROOT / "washington-sds150-favorites.csv"
FIXTURE_CACHE_DIR = REPO_ROOT / ".fixture-cache"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SYNTHETIC_HPD_PATH = FIXTURES_DIR / "wasds150_synthetic_bcdx36hp.hpd"
SYNTHETIC_HPDB_CFG_PATH = FIXTURES_DIR / "wasds150_synthetic_hpdb.cfg"
SYNTHETIC_HPDB_STATE_PATH = FIXTURES_DIR / "wasds150_synthetic_s_000053.hpd"


@pytest.fixture()
def repo_csv_path() -> Path:
    """Path to this repository's real, hand-curated catalog CSV."""
    assert REPO_CSV_PATH.exists(), f"expected repo CSV at {REPO_CSV_PATH}"
    return REPO_CSV_PATH


@pytest.fixture()
def synthetic_hpdb_cfg_path() -> Path:
    """This project's own, fully-original synthetic hpdb.cfg fixture."""
    assert SYNTHETIC_HPDB_CFG_PATH.exists(), f"expected synthetic fixture at {SYNTHETIC_HPDB_CFG_PATH}"
    return SYNTHETIC_HPDB_CFG_PATH


@pytest.fixture()
def synthetic_hpdb_state_path() -> Path:
    """This project's own, fully-original synthetic s_<state>.hpd fixture."""
    assert SYNTHETIC_HPDB_STATE_PATH.exists(), f"expected synthetic fixture at {SYNTHETIC_HPDB_STATE_PATH}"
    return SYNTHETIC_HPDB_STATE_PATH


@pytest.fixture()
def synthetic_bcdx36hp_path() -> Path:
    """This project's own, fully-original synthetic BCDx36HP fixture (see
    NOTICE.md) — always available, no network required."""
    assert SYNTHETIC_HPD_PATH.exists(), f"expected synthetic fixture at {SYNTHETIC_HPD_PATH}"
    return SYNTHETIC_HPD_PATH


@pytest.fixture()
def fixture_cache_dir() -> Path:
    """Directory populated by ``scripts/fetch_hpe_fixtures.py``. Never
    committed to version control (see .gitignore/NOTICE.md); tests that
    depend on its contents must ``pytest.skip`` if the relevant file is
    absent rather than fail."""
    return FIXTURE_CACHE_DIR


_SAMPLE_ROWS = [
    {
        "favorite_key": "FL01",
        "favorite_name": "Alpha Statewide",
        "region": "Statewide",
        "counties": "All 39 counties",
        "scenario": "Public safety/SAR",
        "source_type": "conventional",
        "system_or_category": "Alpha Net",
        "sites_or_coverage": "Statewide",
        "departments_or_channels": "ALPHA1 155.000",
        "mode": "FM",
        "monitorability": "Full - unencrypted",
        "upgrade_required": "None",
        "source_url": "https://example.org/alpha",
        "notes": "Sample row one\nwith an embedded newline",
    },
    {
        "favorite_key": "FL02",
        "favorite_name": "Bravo Trunked",
        "region": "Western WA",
        "counties": "King",
        "scenario": "Interop",
        "source_type": "trunked P25 Phase II",
        "system_or_category": "Bravo SID 1234",
        "sites_or_coverage": "King County sites",
        "departments_or_channels": "Bravo Dispatch, [E]-ENCRYPTED",
        "mode": "P25 Phase II",
        "monitorability": "Mixed",
        "upgrade_required": "None (P25 native)",
        "source_url": "https://example.org/bravo",
        "notes": "Has \"quotes\" and, a comma",
    },
    {
        "favorite_key": "FL09a",
        "favorite_name": "Charlie Split List",
        "region": "Eastern WA",
        "counties": "Spokane",
        "scenario": "Aviation",
        "source_type": "conventional",
        "system_or_category": "Charlie Air",
        "sites_or_coverage": "Spokane area",
        "departments_or_channels": "CTAF 122.800",
        "mode": "AM",
        "monitorability": "Full - unencrypted",
        "upgrade_required": "None",
        "source_url": "https://example.org/charlie",
        "notes": "",
    },
]


def write_sample_csv(path: Path) -> Path:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(CSV_FIELDS), quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        writer.writeheader()
        for row in _SAMPLE_ROWS:
            writer.writerow(row)
    return path


@pytest.fixture()
def sample_csv_path(tmp_path: Path) -> Path:
    """A small, synthetic 3-row catalog CSV (same shape/quoting as the real
    one) for fast, isolated unit tests that don't need all 78 real rows."""
    return write_sample_csv(tmp_path / "sample.csv")


@pytest.fixture()
def wasds_home(tmp_path: Path, monkeypatch) -> Path:
    """Point WASDS150_HOME at an isolated temp directory for this test."""
    home = tmp_path / "wasds150-home"
    monkeypatch.setenv("WASDS150_HOME", str(home))
    return home
