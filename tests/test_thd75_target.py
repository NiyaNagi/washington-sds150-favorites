from __future__ import annotations

from pathlib import Path

from wasds150.catalog.baseline import load_baseline
from wasds150.catalog.puget_broadcast import favorite as puget_broadcast
from wasds150.catalog.thd75_local import favorite as thd75_local
from wasds150.export.thd75_target import (
    FILE_SIZE,
    MODE_CODES,
    RX_ONLY_TX_HZ,
    inspect_thd75,
    render_thd75,
    restore_unowned_regions,
)
from wasds150.models.plan import ChannelPlan
from wasds150.plan.resolve import PlannedChannel, ResolvedPlan, resolve_plan
from wasds150.plans.thd75_ames_lake import THD75_AMES_LAKE
from wasds150.radios.registry import TH_D75
from wasds150.radios.tones import parse_tone


def _template(path: Path) -> bytes:
    data = bytearray(b"\xA5" * FILE_SIZE)
    header = b"MCP-D75\xFFV1.00\xFF\xFF\xFFTH-D75"
    data[: len(header)] = header
    path.write_bytes(data)
    return bytes(data)


def test_thd75_profile_matches_verified_capabilities() -> None:
    assert TH_D75.max_channels == 1000
    assert TH_D75.name_max_len == 16
    assert TH_D75.can_receive(0.1)
    assert TH_D75.can_receive(524.0)
    assert TH_D75.can_transmit(223.5)
    assert not TH_D75.can_transmit(162.55)
    assert {"DV", "AM", "USB", "LSB", "CW", "WFM"} <= TH_D75.modes
    assert TH_D75.verified


def test_local_extensions_resolve_into_thd75_plan() -> None:
    catalog = load_baseline()
    catalog.favorites.extend((puget_broadcast(), thd75_local()))
    resolved = resolve_plan(THD75_AMES_LAKE, catalog)
    assert resolved.block_counts["D-STAR Local"] == 21
    assert resolved.block_counts["FM Broadcast"] == 32
    assert resolved.block_counts["AM Broadcast"] == 29
    assert any(channel.rx_freq_mhz == 223.5 for channel in resolved.channels)
    assert all(channel.mode != "P25" for channel in resolved.channels)
    assert all(channel.mode != "DMR" for channel in resolved.channels)


def test_native_export_preserves_settings_and_encodes_modes(tmp_path: Path) -> None:
    template = tmp_path / "radio.d75"
    original = _template(template)
    plan = ChannelPlan(id="test", radio_id="th-d75", label="Test")
    channels = [
        PlannedChannel(
            slot=1,
            name="ANALOG",
            label="Analog repeater",
            rx_freq_mhz=146.96,
            tx_freq_mhz=146.36,
            transmit=True,
            tx_tone=parse_tone("TONE=C103.5"),
            mode="FM",
            block="Analog",
            source="test",
        ),
        PlannedChannel(
            slot=2,
            name="DSTAR",
            label="D-STAR repeater",
            rx_freq_mhz=443.575,
            tx_freq_mhz=448.575,
            transmit=True,
            mode="DV",
            block="D-STAR",
            source="test",
            dv_urcall="CQCQCQ",
            dv_rpt1="N7IH   B",
            dv_rpt2="N7IH   G",
        ),
        PlannedChannel(
            slot=3,
            name="SAT-RX",
            label="Satellite downlink",
            rx_freq_mhz=436.795,
            transmit=False,
            mode="FM",
            block="Satellite",
            source="test",
        ),
        PlannedChannel(
            slot=4,
            name="BROADCAST",
            label="Broadcast",
            rx_freq_mhz=94.9,
            transmit=False,
            mode="WFM",
            block="Broadcast",
            source="test",
            skip_scan=True,
        ),
    ]
    resolved = ResolvedPlan(plan=plan, profile=TH_D75, channels=channels)

    data, result = render_thd75(resolved, template=template)
    rows = inspect_thd75(data)

    assert result.rows == 4
    assert result.groups == 4
    assert len(data) == FILE_SIZE
    assert data[:0x100] == original[:0x100]
    # A byte well outside memory, names and D-STAR regions is untouched.
    assert data[0x70000] == original[0x70000]
    assert rows[0]["shift"] == 2
    assert rows[0]["tx_value_mhz"] == 0.6
    assert rows[1]["mode_code"] == 7  # routed D-STAR repeater / DR
    assert rows[1]["rpt1"] == "N7IH   B"
    assert rows[1]["rpt2"] == "N7IH   G"
    assert rows[2]["split"] is True
    assert rows[2]["tx_value_mhz"] == RX_ONLY_TX_HZ / 1_000_000
    assert rows[3]["mode_code"] == MODE_CODES["WFM"]
    assert rows[3]["skip"] is True

    mcp_saved = bytearray(data)
    unrelated = 0x3700
    dstar = 0x100 + 0x2A000
    mcp_saved[unrelated] ^= 0xFF
    mcp_saved[dstar] ^= 0xFF
    restored, count = restore_unowned_regions(bytes(mcp_saved), original)
    assert count == 1
    assert restored[unrelated] == original[unrelated]
    assert restored[dstar] == mcp_saved[dstar]
