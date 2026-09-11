"""The shared source factory used by the CLI, the web UI and the fleet wizard."""
from __future__ import annotations

import pytest

from wasds150 import cli
from wasds150.sources.base import OnlineSourceAdapter
from wasds150.sources.config import SourcesConfig
from wasds150.sources.factory import instantiate_all, instantiate_source, runnable_source_names
from wasds150.sources.noaa_wx import NoaaNwrSource
from wasds150.sources.radioreference_premium import RadioReferencePremiumSource
from wasds150.sources.registry import list_sources
from wasds150.sources.sentinel_local import SentinelLocalSource
from wasds150.webui import api


def test_plain_online_source_is_built_without_configuration():
    source = instantiate_source(NoaaNwrSource.name, SourcesConfig())
    assert isinstance(source, NoaaNwrSource)


def test_legacy_adapter_is_not_runnable():
    assert instantiate_source("static_pack", SourcesConfig()) is None


def test_unknown_source_raises_key_error():
    with pytest.raises(KeyError):
        instantiate_source("no_such_source", SourcesConfig())


def test_sentinel_local_needs_a_configured_path(tmp_path):
    assert instantiate_source("sentinel_local", SourcesConfig()) is None
    configured = SourcesConfig(sentinel_local_mount=str(tmp_path))
    assert isinstance(instantiate_source("sentinel_local", configured), SentinelLocalSource)


def test_radioreference_needs_an_export_or_both_identifiers(tmp_path):
    assert instantiate_source("radioreference_premium", SourcesConfig()) is None
    username_only = SourcesConfig(radioreference_username="me")
    assert instantiate_source("radioreference_premium", username_only) is None
    export = SourcesConfig(radioreference_export_path=str(tmp_path / "rr.json"))
    assert isinstance(instantiate_source("radioreference_premium", export), RadioReferencePremiumSource)
    both = SourcesConfig(radioreference_username="me", radioreference_app_key="key")
    assert isinstance(instantiate_source("radioreference_premium", both), RadioReferencePremiumSource)


def test_runnable_names_are_available_online_adapters_in_registry_order():
    expected = [
        name
        for name, cls in list_sources().items()
        if issubclass(cls, OnlineSourceAdapter) and cls.available
    ]
    assert runnable_source_names() == expected
    assert "static_pack" not in expected


def test_runnable_names_respect_only_and_skip():
    assert runnable_source_names(only={"wwara", "amsat"}) == [
        n for n in runnable_source_names() if n in {"wwara", "amsat"}
    ]
    assert "wwara" not in runnable_source_names(skip={"wwara"})
    assert runnable_source_names(only={"wwara"}, skip={"wwara"}) == []


def test_instantiate_all_skips_unconfigured_local_sources():
    names = {source.name for source in instantiate_all(SourcesConfig())}
    assert "sentinel_local" not in names
    assert "radioreference_premium" not in names
    assert NoaaNwrSource.name in names


def test_bulk_source_options_reach_the_adapters():
    from wasds150.sources.faa_nasr import FaaNasrSource
    from wasds150.sources.fcc_uls import FccUlsSource

    config = SourcesConfig(
        faa_nasr_subjects=["FRQ"], fcc_uls_services=["lmpriv", "lmcomm"], fcc_uls_emissions=["DMR", "7K60FXE"],
        fcc_uls_within_miles=60.0, fcc_uls_active_only=False,
    )
    nasr = instantiate_source("faa_nasr", config)
    assert isinstance(nasr, FaaNasrSource) and nasr.subjects == ("FRQ",)
    uls = instantiate_source("fcc_uls", config)
    assert isinstance(uls, FccUlsSource)
    assert uls.services == ("lmpriv", "lmcomm") and uls.within_miles == 60.0 and uls.home is not None
    assert uls.emission_codes == {"7K60FXE"} and uls.emission_modes == {"DMR"} and uls.active_only is False
    assert FccUlsSource.bulk and FaaNasrSource.bulk and not NoaaNwrSource.bulk


def test_choice_lists_are_cleaned_and_checked():
    from wasds150.sources.config import parse_choice_list

    assert parse_choice_list("frq, com", ("NAV_BASE", "COM", "FRQ"), upper=True) == ["FRQ", "COM"]
    assert parse_choice_list("") is None
    with pytest.raises(ValueError):
        parse_choice_list("lmpriv,pw", ("lmpriv", "lmcomm"))


def test_sources_configure_sets_the_bulk_options(wasds_home, sample_csv_path, capsys):
    import json

    argv = [
        "--csv", str(sample_csv_path), "sources", "configure",
        "--fcc-services", "lmpriv,lmcomm", "--fcc-emissions", "dmr,7k60fxe", "--fcc-within-miles", "60",
        "--faa-subjects", "frq", "--fcc-all-licences", "--json",
    ]
    assert cli.main(argv) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["fcc_uls"] == {
        "services": ["lmpriv", "lmcomm"], "emissions": ["DMR", "7K60FXE"], "within_miles": 60.0, "active_only": False,
    }
    assert data["faa_nasr_subjects"] == ["FRQ"]
    assert cli.main(["--csv", str(sample_csv_path), "sources", "configure", "--fcc-services", "pw"]) == 1


def test_entry_points_no_longer_carry_their_own_copies():
    assert not hasattr(cli, "_instantiate_source")
    assert not hasattr(cli, "_build_http_client")
    assert not hasattr(api, "_instantiate_source_for_ui")
