"""The shipped ``atd890-scan`` plan: structure, transmit policy and export."""
from __future__ import annotations

import pytest

from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.export.atd890_bundle import build_bundle
from wasds150.models.plan import TX_NONE
from wasds150.plan.service import export_plan, resolve_named_plan
from wasds150.plans import get_plan
from wasds150.plans.atd890_scan import ATD890_SCAN, HOME, RADIUS_MILES


@pytest.fixture()
def real_ctx(tmp_path, repo_csv_path):
    config = AppConfig(home=tmp_path / "home")
    config.ensure_dirs()
    return build_context(config, csv_override=repo_csv_path)


def test_registered_for_the_anytone():
    plan = get_plan("atd890-scan")
    assert plan is ATD890_SCAN and plan.radio_id == "at-d890uv"


def test_banks_fit_the_display_and_are_unique():
    banks = [block.bank for block in ATD890_SCAN.blocks]
    assert all(bank and len(bank) <= 16 for bank in banks)
    assert len(set(banks)) == len(banks)
    assert all(len(group.name) <= 13 for group in ATD890_SCAN.scan_groups)


def test_only_amateur_blocks_transmit():
    for block in ATD890_SCAN.blocks:
        if block.tx_policy != TX_NONE:
            assert block.label.startswith(("Ham", "DMR Puget", "Simplex", "Seattle ACS")), block.label
        if block.label.startswith("Ham"):
            for selector in block.selectors:
                assert selector.within_miles == (HOME[0], HOME[1], RADIUS_MILES)


def test_noaa_and_broadcast_never_scan():
    skipped = {block.label for block in ATD890_SCAN.blocks if block.skip_scan}
    assert {"NOAA Weather", "FM Broadcast"} <= skipped
    for group in ATD890_SCAN.scan_groups:
        assert not (set(group.blocks) & skipped)


def test_resolves_and_exports_against_the_shipped_catalog(real_ctx, tmp_path):
    _plan, resolved = resolve_named_plan(real_ctx, "atd890-scan")
    assert resolved.slots_used > 300
    for channel in resolved.channels:
        if channel.transmit:
            freq = channel.tx_freq_mhz if channel.tx_freq_mhz is not None else channel.rx_freq_mhz
            assert 144.0 <= freq <= 148.0 or 420.0 <= freq <= 450.0, channel.label
            if channel.digital is not None:
                assert channel.digital.talkgroup, channel.label
    bundle = build_bundle(resolved)
    assert bundle.am_air, "expected air band rows in the AM list"
    assert bundle.fm, "expected FM broadcast rows"
    assert any(s.name.startswith("Ham All") for s in bundle.scan_lists)
    export = export_plan(real_ctx, "atd890-scan", target_id="atd890-cps", out_dir=tmp_path)
    assert export.csv_path.is_dir() and len(export.files) == 10
    assert (export.csv_path / "Channel.CSV").is_file()
    assert export.report_path.is_file()
    payload = export.to_dict()
    assert len(payload["files"]) == 12


def test_directory_export_copies_the_whole_bundle(real_ctx, tmp_path):
    export = export_plan(real_ctx, "atd890-scan", target_id="atd890-cps", out_dir=tmp_path / "a", copy_to=tmp_path / "b")
    assert (tmp_path / "b" / "atd890-scan" / "Channel.CSV").is_file()
    assert export.copies
