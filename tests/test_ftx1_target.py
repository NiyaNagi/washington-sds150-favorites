"""Tests for the native ``.FTX1`` export target.

These run against the blank structural template that ships in the repository,
so they exercise the real write path without needing a file from the vendor
programmer.
"""
from __future__ import annotations

import pytest

from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.export.ftx1_file import PMS_PAIRS, Ftx1File
from wasds150.export.ftx1_target import (
    Ftx1ExportError,
    MEMORY_CAPACITY,
    NAME_LEN,
    render_ftx1,
    template_path,
    write_ftx1,
)
from wasds150.plan.service import resolve_named_plan


@pytest.fixture()
def ctx(tmp_path, repo_csv_path):
    config = AppConfig(home=tmp_path / "home")
    config.ensure_dirs()
    return build_context(config, csv_override=repo_csv_path)


@pytest.fixture()
def resolved(ctx):
    _plan, resolved = resolve_named_plan(ctx, "ftx1-wa")
    return resolved


def _template_or_skip():
    path = template_path()
    if not path.is_file():
        pytest.skip(f"blank FTX-1 template not present at {path}")
    return path


# -------------------------------------------------------------- template --
def test_template_ships_with_the_repository():
    path = _template_or_skip()
    assert path.stat().st_size > 0


def test_template_carries_no_channel_data():
    """The template is structure only. If this fails, we are shipping someone
    else's channel list."""
    path = _template_or_skip()
    ftx1 = Ftx1File.load(path)
    populated = [record for record in ftx1.memories() if not record.empty]
    assert populated == []
    for record in ftx1.records:
        assert not record.name.strip()
        assert not record.comment.strip()


def test_template_round_trips():
    path = _template_or_skip()
    original = path.read_bytes()
    assert Ftx1File.load(path).round_trips(original)


# ---------------------------------------------------------------- render --
def test_render_writes_every_resolved_channel(resolved):
    _template_or_skip()
    ftx1, result = render_ftx1(resolved)
    assert result.rows == len(resolved.channels)
    populated = [r for r in ftx1.memories() if not r.empty]
    assert len(populated) == result.rows


def test_render_programs_scan_pairs(resolved):
    _template_or_skip()
    ftx1, result = render_ftx1(resolved)
    assert result.scan_pairs > 0
    assert result.scan_pairs <= PMS_PAIRS
    used = [pair for pair in ftx1.scan_limits() if not pair[0].empty]
    assert len(used) == result.scan_pairs
    for low, high in used:
        assert low.rx_hz < high.rx_hz, "a scan pair must span upwards"


def test_scan_pairs_do_not_consume_memories(resolved):
    """Scan limits live in their own region, so they cost no channel slots."""
    _template_or_skip()
    ftx1, result = render_ftx1(resolved)
    assert len(ftx1.memories()) == MEMORY_CAPACITY
    assert result.rows <= MEMORY_CAPACITY


def test_render_preserves_frequencies(resolved):
    _template_or_skip()
    ftx1, _result = render_ftx1(resolved)
    memories = [r for r in ftx1.memories() if not r.empty]
    for planned, record in zip(resolved.channels, memories):
        assert abs(record.rx_mhz - planned.rx_freq_mhz) < 1e-6


def test_names_are_truncated_to_the_display_width(resolved):
    _template_or_skip()
    ftx1, _result = render_ftx1(resolved)
    for record in ftx1.memories():
        assert len(record.name) <= NAME_LEN


def test_repeater_shift_is_written_for_transmit_channels(resolved):
    _template_or_skip()
    ftx1, _result = render_ftx1(resolved)
    memories = [r for r in ftx1.memories() if not r.empty]
    pairs = [
        (planned, record)
        for planned, record in zip(resolved.channels, memories)
        if planned.transmit
        and planned.tx_freq_mhz
        and abs(planned.tx_freq_mhz - planned.rx_freq_mhz) > 1e-6
    ]
    assert pairs, "expected at least one repeater channel in the plan"
    for planned, record in pairs:
        assert abs(record.tx_mhz - planned.tx_freq_mhz) < 1e-6


def test_receive_only_channels_get_no_shift(resolved):
    """A receive-only memory must not carry a transmit offset."""
    _template_or_skip()
    ftx1, _result = render_ftx1(resolved)
    memories = [r for r in ftx1.memories() if not r.empty]
    for planned, record in zip(resolved.channels, memories):
        if not planned.transmit:
            assert record.tx_hz == record.rx_hz


def test_missing_template_raises_a_useful_error(resolved, tmp_path):
    with pytest.raises(Ftx1ExportError, match="template not found"):
        render_ftx1(resolved, template=tmp_path / "absent.FTX1")


# ----------------------------------------------------------------- write --
def test_write_produces_a_loadable_file(resolved, tmp_path):
    _template_or_skip()
    out = tmp_path / "plan.FTX1"
    result = write_ftx1(resolved, out)
    assert out.is_file()

    reloaded = Ftx1File.load(out)
    populated = [r for r in reloaded.memories() if not r.empty]
    assert len(populated) == result.rows


def test_written_file_keeps_the_container_size(resolved, tmp_path):
    """The format is fixed-size; a size change means the record model is wrong."""
    template = _template_or_skip()
    out = tmp_path / "plan.FTX1"
    write_ftx1(resolved, out)
    assert out.stat().st_size == template.stat().st_size


def test_written_file_round_trips(resolved, tmp_path):
    _template_or_skip()
    out = tmp_path / "plan.FTX1"
    write_ftx1(resolved, out)
    assert Ftx1File.load(out).round_trips(out.read_bytes())


def test_export_registry_serves_the_right_radio():
    from wasds150.export.registry import get_target

    target = get_target("ftx1-file")
    assert target.radio_id == "ftx1"
    assert target.extension == ".FTX1"
    assert target.available is True


def test_ftx1_target_refuses_a_plan_for_another_radio(ctx):
    from wasds150.export.registry import get_target

    _plan, tdh9 = resolve_named_plan(ctx, "h9-ozette")
    with pytest.raises(ValueError):
        get_target("ftx1-file").check_radio(tdh9)
