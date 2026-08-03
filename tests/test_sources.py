import pytest

from wasds150.sources.registry import get_source_class, list_sources
from wasds150.sources.static_pack import StaticPackSource


def test_list_sources_includes_static_pack_as_available():
    sources = list_sources()
    assert "static_pack" in sources
    assert sources["static_pack"].available is True


def test_placeholder_sources_marked_unavailable():
    sources = list_sources()
    for name in ("radioreference_free", "repeaterbook"):
        assert name in sources
        assert sources[name].available is False


def test_implemented_sources_marked_available():
    sources = list_sources()
    for name in (
        "sentinel_local",
        "radioreference_premium",
        "noaa_nwr",
        "uscg_navcen",
        "amsat",
        "wwara",
        "iacc",
        "faa_nasr",
        "fcc_uls",
        "nwac",
        "wa_emd",
        "wa_dnr",
        "nifc",
    ):
        assert name in sources
        assert sources[name].available is True


def test_get_source_class_unknown_raises():
    with pytest.raises(KeyError):
        get_source_class("does_not_exist")


def test_static_pack_fetch_and_normalize_round_trip(sample_csv_path):
    source = StaticPackSource(sample_csv_path)
    raw = source.fetch()
    assert raw.source_adapter == "static_pack"
    assert raw.fetched_at  # non-empty ISO timestamp

    favorites = source.normalize(raw)
    assert len(favorites) == 3
    assert favorites[0].slug == "fl01"


def test_sentinel_local_no_data_configured_produces_no_facts():
    from wasds150.sources.sentinel_local import SentinelLocalSource

    source = SentinelLocalSource(hpdb_cfg_path="/nonexistent/hpdb.cfg")
    raw = source.fetch()
    result = source.normalize(raw)
    assert result.facts == []
    assert result.warnings
