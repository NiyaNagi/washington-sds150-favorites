"""Independent cross-checks of wasds150.hpe.hpdb against a real, third-party
synthetic HPDB fixture pair (see NOTICE.md). Never vendored; fetched on
demand via scripts/fetch_hpe_fixtures.py into .fixture-cache/. Every test
here skips cleanly if its fixture is absent.
"""
from __future__ import annotations

import pytest

from wasds150.hpe import hpdb
from wasds150.hpe.schema import validate_schema


def _require_fixture(fixture_cache_dir, name):
    path = fixture_cache_dir / name
    if not path.exists():
        pytest.skip(f"external fixture {name} not fetched; run scripts/fetch_hpe_fixtures.py")
    return path


def test_real_hpdb_cfg_county_index(fixture_cache_dir):
    path = _require_fixture(fixture_cache_dir, "platypus_hpdb.cfg")
    doc = hpdb.read_hpdb_cfg(path)
    index = hpdb.CountyIndex.from_hpdb_cfg(doc)
    assert index.state_by_id[90] == "Example State"
    assert index.by_id[9001] == "Alpha"
    assert index.by_id[9002] == "Bravo"
    assert index.by_id[9003] == "Cedar"


def test_real_hpdb_cfg_lm_record_arity(fixture_cache_dir):
    path = _require_fixture(fixture_cache_dir, "platypus_hpdb.cfg")
    doc = hpdb.read_hpdb_cfg(path)
    lm = doc.find_first("LM")
    assert lm is not None
    assert lm.arity == 9


def test_real_state_hpd_segments_into_four_systems(fixture_cache_dir):
    path = _require_fixture(fixture_cache_dir, "platypus_s_000090.hpd")
    doc = hpdb.read_state_hpd(path)
    systems = hpdb.segment_systems(doc)
    assert len(systems) == 4
    names = [s.name() for s in systems]
    assert "Alpha County Public Safety" in names
    assert "Regional Transit" in names
    assert "Example Statewide P25" in names
    assert "Example Business Radio" in names


def test_real_state_hpd_agency_id_quirk_confirmed(fixture_cache_dir):
    """Confirms the documented pitfall directly against the real fixture:
    'Regional Transit' has an AgencyId (not a CountyId) as its own id, but
    county_ids() must still resolve its real county from AreaCounty."""
    path = _require_fixture(fixture_cache_dir, "platypus_s_000090.hpd")
    doc = hpdb.read_state_hpd(path)
    systems = hpdb.segment_systems(doc)
    transit = next(s for s in systems if s.name() == "Regional Transit")
    assert transit.identity() == ("AgencyId", 9101)
    assert transit.county_ids() == [9002]


def test_real_state_hpd_multi_county_trunk(fixture_cache_dir):
    path = _require_fixture(fixture_cache_dir, "platypus_s_000090.hpd")
    doc = hpdb.read_state_hpd(path)
    systems = hpdb.segment_systems(doc)
    statewide = next(s for s in systems if s.name() == "Example Statewide P25")
    assert sorted(statewide.county_ids()) == [9001, 9003]


def test_real_state_hpd_all_arities_match_our_schema(fixture_cache_dir):
    path = _require_fixture(fixture_cache_dir, "platypus_s_000090.hpd")
    doc = hpdb.read_state_hpd(path)
    for r in doc.records:
        schema = hpdb.BCDX36HP_SCHEMA.get(r.tag) or hpdb.HPDB_ONLY_SCHEMA.get(r.tag)
        if schema is None:
            continue
        assert r.arity in schema.arities, f"{r.tag}: real fixture arity {r.arity} not in {schema.arities}"


def test_real_state_hpd_converts_and_validates_cleanly(fixture_cache_dir):
    path = _require_fixture(fixture_cache_dir, "platypus_s_000090.hpd")
    doc = hpdb.read_state_hpd(path)
    fav = hpdb.to_favorites_dialect(doc)
    assert validate_schema(fav) == []
    assert fav.find_first("AreaState") is None
    assert fav.find_first("AreaCounty") is None
    assert len(fav.find_all("DQKs_Status")) == 4  # one per system
