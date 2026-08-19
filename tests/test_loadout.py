"""Tests for the per-radio loadout service.

The point of this module is that the three radios do *not* share a shape, so
these tests assert the differences rather than papering over them.
"""
from __future__ import annotations

import json

import pytest

from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.plan.loadout import (
    KIND_FAVORITES,
    KIND_MEMORY_LIST,
    diff_against_snapshot,
    get_loadout,
    list_snapshots,
    loadout_index,
    save_snapshot,
)


@pytest.fixture()
def ctx(tmp_path, repo_csv_path):
    config = AppConfig(home=tmp_path / "home")
    config.ensure_dirs()
    return build_context(config, csv_override=repo_csv_path)


# ----------------------------------------------------------------- index --
def test_index_has_one_entry_per_supported_radio():
    entries = loadout_index()
    radios = {entry["radio_id"] for entry in entries}
    assert {"sds150", "td-h9", "ftx1"} <= radios


def test_index_declares_the_right_shape_per_radio():
    by_radio = {entry["radio_id"]: entry for entry in loadout_index()}
    # A scanner's config is a tree of Favorites Lists.
    assert by_radio["sds150"]["kind"] == KIND_FAVORITES
    # A transceiver's config is a flat, ordered memory list.
    assert by_radio["td-h9"]["kind"] == KIND_MEMORY_LIST
    assert by_radio["ftx1"]["kind"] == KIND_MEMORY_LIST


def test_index_surfaces_unverified_profiles():
    by_radio = {entry["radio_id"]: entry for entry in loadout_index()}
    assert by_radio["ftx1"]["verified"] is False
    assert by_radio["td-h9"]["verified"] is True


# -------------------------------------------------------------- loadouts --
def test_scanner_loadout_is_hierarchical(ctx):
    loadout = get_loadout(ctx, "sds150")
    assert loadout.kind == KIND_FAVORITES
    assert loadout.favorites, "expected Favorites Lists"
    assert not loadout.channels, "a scanner must not be flattened into memories"
    assert loadout.summary["favorites_lists"] == len(loadout.favorites)
    for row in loadout.favorites:
        assert "key" in row and "channels" in row and "talkgroups" in row


def test_scanner_loadout_counts_talkgroups_separately(ctx):
    """Talkgroups are the thing a flat memory list would destroy.

    The packaged catalog carries no talkgroups - they arrive only with local
    Sentinel enrichment, which is never committed - so this builds a trunked
    system by hand and checks that its TGID entries are counted as talkgroups
    rather than being lumped in with conventional channels.
    """
    from wasds150.models.catalog import Channel, Department, Site, System, TrunkFrequency

    favorite = ctx.catalog.favorites[0]
    favorite.systems.append(
        System(
            id="sys-trunk",
            label="Synthetic P25",
            tech="P25Standard",
            trunk_frequencies=[TrunkFrequency(id="lcn-1", freq_mhz=851.0125)],
            sites=[
                Site(
                    id="site-1",
                    label="Site 1",
                    departments=[
                        Department(
                            id="dept-1",
                            label="Ops",
                            channels=[
                                Channel(id="tg-1", label="Dispatch", tgid=1001),
                                Channel(id="tg-2", label="Tac 1", tgid=1002),
                                Channel(id="ch-1", label="Simplex", freq_mhz=155.010),
                            ],
                        )
                    ],
                )
            ],
        )
    )

    loadout = get_loadout(ctx, "sds150")
    row = next(r for r in loadout.favorites if r["key"] == favorite.favorite_key)
    assert row["talkgroups"] >= 2, "TGID entries must be counted as talkgroups"
    assert row["trunked_systems"] >= 1, "a system with sites and LCNs is trunked"
    assert loadout.summary["talkgroups"] >= 2


def test_transceiver_loadout_is_a_memory_list(ctx):
    loadout = get_loadout(ctx, "h9-ozette")
    assert loadout.kind == KIND_MEMORY_LIST
    assert loadout.channels
    assert not loadout.favorites
    slots = [c["slot"] for c in loadout.channels]
    assert slots == sorted(slots), "memories must be in slot order"
    assert loadout.summary["memories_used"] == len(loadout.channels)


def test_transceiver_loadout_splits_transmit_and_receive(ctx):
    loadout = get_loadout(ctx, "h9-ozette")
    total = loadout.summary["transmit_enabled"] + loadout.summary["receive_only"]
    assert total == loadout.summary["memories_used"]


def test_ftx1_loadout_resolves(ctx):
    loadout = get_loadout(ctx, "ftx1-wa")
    assert loadout.kind == KIND_MEMORY_LIST
    assert loadout.radio_id == "ftx1"
    assert loadout.verified is False
    assert loadout.summary["memories_used"] <= loadout.summary["memories_available"]


def test_ftx1_loadout_never_transmits_outside_amateur_bands(ctx):
    """The FTX-1 transmits only on amateur allocations."""
    from wasds150.radios.registry import FTX1

    loadout = get_loadout(ctx, "ftx1-wa")
    for row in loadout.channels:
        if row["transmit"]:
            freq = row["tx_mhz"] or row["rx_mhz"]
            assert FTX1.can_transmit(freq), f"{row['name']} transmits at {freq}"


def test_every_index_entry_resolves(ctx):
    for entry in loadout_index():
        loadout = get_loadout(ctx, entry["id"])
        assert loadout.kind == entry["kind"]


def test_unknown_loadout_raises(ctx):
    with pytest.raises(KeyError):
        get_loadout(ctx, "not-a-radio")


def test_loadout_is_json_serializable(ctx):
    for loadout_id in ("sds150", "h9-ozette", "ftx1-wa"):
        payload = json.loads(json.dumps(get_loadout(ctx, loadout_id).to_dict()))
        assert payload["radio_id"]


# -------------------------------------------------------------- snapshots --
def test_save_snapshot_writes_files(ctx):
    info = save_snapshot(ctx, "h9-ozette")
    from pathlib import Path

    assert Path(info["path"]).is_file()
    assert Path(info["latest"]).is_file()
    assert info["catalog_hash"]


def test_snapshots_are_listed_newest_first(ctx):
    save_snapshot(ctx, "h9-ozette")
    save_snapshot(ctx, "sds150")
    rows = list_snapshots(ctx)
    assert len(rows) >= 2
    stamps = [row["saved_at"] for row in rows]
    assert stamps == sorted(stamps, reverse=True)


def test_snapshots_can_be_filtered_by_loadout(ctx):
    save_snapshot(ctx, "h9-ozette")
    save_snapshot(ctx, "sds150")
    rows = list_snapshots(ctx, "sds150")
    assert rows
    assert all(row["loadout_id"] == "sds150" for row in rows)


def test_diff_without_snapshot_says_so(ctx):
    diff = diff_against_snapshot(ctx, "h9-ozette")
    assert diff["has_snapshot"] is False


def test_diff_against_own_snapshot_is_empty(ctx):
    """Saving then immediately diffing must report no change."""
    save_snapshot(ctx, "h9-ozette")
    diff = diff_against_snapshot(ctx, "h9-ozette")
    assert diff["has_snapshot"] is True
    assert diff["added"] == 0
    assert diff["removed"] == 0


def test_diff_detects_a_removed_channel(ctx, tmp_path):
    """Edit a saved snapshot, then confirm the diff notices."""
    from pathlib import Path

    info = save_snapshot(ctx, "h9-ozette")
    latest = Path(info["latest"])
    saved = json.loads(latest.read_text(encoding="utf-8"))
    # Pretend the previous snapshot had one extra channel.
    saved["loadout"]["channels"].append(
        {"slot": 999, "name": "GHOST", "rx_mhz": 151.005, "transmit": False}
    )
    latest.write_text(json.dumps(saved), encoding="utf-8")

    diff = diff_against_snapshot(ctx, "h9-ozette")
    assert diff["removed"] == 1
    assert diff["detail"]["removed"][0]["name"] == "GHOST"


def test_diff_for_scanner_reports_list_changes(ctx):
    from pathlib import Path

    info = save_snapshot(ctx, "sds150")
    latest = Path(info["latest"])
    saved = json.loads(latest.read_text(encoding="utf-8"))
    saved["loadout"]["favorites"].append(
        {"key": "ZZ99", "name": "Ghost list", "channels": 5, "talkgroups": 0}
    )
    latest.write_text(json.dumps(saved), encoding="utf-8")

    diff = diff_against_snapshot(ctx, "sds150")
    assert diff["removed"] == 1
    assert diff["detail"]["removed"][0]["key"] == "ZZ99"
