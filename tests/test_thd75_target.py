from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from wasds150.catalog.baseline import load_baseline
from wasds150.catalog.puget_broadcast import favorite as puget_broadcast
from wasds150.catalog.thd75_local import favorite as thd75_local
from wasds150.catalog.thd75_user import favorite as thd75_user
from wasds150.catalog.thd75_wwara_snapshot import favorite as thd75_wwara
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_current_operator_artifacts_are_complete_and_consistent() -> None:
    root = _repo_root()
    image_path = root / "radio-configs" / "thd75-current.d75"
    settings_path = root / "radio-configs" / "thd75-current-settings.json"
    bitmap_path = root / "radio-configs" / "thd75-power-on-KM7HKM.bmp"

    image = image_path.read_bytes()
    digest = hashlib.sha256(image).hexdigest().upper()
    assert digest == "03BC9BA3ED4F94F9A3BE68D14ED9245CC1F5EB0C17C61637304F6EFBF4193F07"
    rows = inspect_thd75(image)
    assert len(rows) == 545
    by_memory_name = {row["name"]: row for row in rows}
    assert by_memory_name["N7QTREDMOND"]["slot"] == 96
    assert by_memory_name["W7AUX"]["slot"] == 102
    assert by_memory_name["VAERPT"]["slot"] == 108
    assert all(by_memory_name[name]["tx_value_mhz"] == 5.0 for name in (
        "N7QTREDMOND", "W7AUX", "VAERPT"
    ))
    assert any(
        row["name"] == "WW7MSTSEATTLE" and row["rx_mhz"] == 146.9
        for row in rows
    )
    repeaters = [row for row in rows if row["group"] in (0, 1, 2, 3)]
    assert all(
        (left["group"], left["rx_mhz"], left["name"].upper())
        <= (right["group"], right["rx_mhz"], right["name"].upper())
        for left, right in zip(repeaters, repeaters[1:])
    )

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["source_sha256"] == digest
    assert settings["setting_count"] == 400
    by_name = {entry["name"]: entry["value"] for entry in settings["settings"]}
    assert by_name["aprs.MyCallsign"] == "KM7HKM"
    assert by_name["radio.BluetoothOnOff"] is True
    assert by_name["gps.MyPositionList[0].Name"] == "Home"

    bitmap = bitmap_path.read_bytes()
    assert hashlib.sha256(bitmap).hexdigest().upper() == (
        "D299694C49260914F8BCE8D6A9E6836D07991A0975158DC8B66F3FA05375C785"
    )
    assert struct.unpack_from("<2sIHHI", bitmap, 0) == (
        b"BM", len(bitmap), 0, 0, 66
    )
    assert struct.unpack_from("<IiiHHI", bitmap, 14) == (
        40, 240, 180, 1, 16, 3
    )
    assert struct.unpack_from("<III", bitmap, 54) == (0xF800, 0x07E0, 0x001F)


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
    catalog.favorites.extend((
        puget_broadcast(), thd75_local(), thd75_user(), thd75_wwara()
    ))
    resolved = resolve_plan(THD75_AMES_LAKE, catalog)
    assert resolved.block_counts["D-STAR Local"] == 21
    assert resolved.block_counts["FM Broadcast"] == 32
    assert resolved.block_counts["AM Broadcast"] == 29
    additions = [
        channel for channel in resolved.channels
        if channel.source.startswith("THD75USER/")
    ]
    assert [channel.name for channel in additions] == ["N7QTREDMOND", "W7AUX", "VAERPT"]
    assert all(channel.block == "70cm Repeaters" for channel in additions)
    assert all(channel.bank == "70cm Repeaters" for channel in additions)
    assert [channel.tx_freq_mhz for channel in additions] == [447.325, 447.825, 448.05]
    snapshot = [
        channel for channel in resolved.channels
        if channel.source.startswith("THD75WWARA/")
    ]
    assert {channel.rx_freq_mhz for channel in snapshot} == {
        146.9, 224.68, 443.55, 443.675, 444.825
    }
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
        PlannedChannel(
            slot=5,
            name="USERADD",
            label="User addition",
            rx_freq_mhz=443.05,
            tx_freq_mhz=443.65,
            transmit=True,
            tx_tone=parse_tone("TONE=C103.5"),
            mode="FM",
            block="Operator Additions",
            bank="Analog",
            source="test",
        ),
    ]
    resolved = ResolvedPlan(plan=plan, profile=TH_D75, channels=channels)

    data, result = render_thd75(resolved, template=template)
    rows = inspect_thd75(data)

    assert result.rows == 5
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
    assert rows[4]["group"] == rows[0]["group"] == 0

    mcp_saved = bytearray(data)
    unrelated = 0x3700
    dstar = 0x100 + 0x2A000
    mcp_saved[unrelated] ^= 0xFF
    mcp_saved[dstar] ^= 0xFF
    restored, count = restore_unowned_regions(bytes(mcp_saved), original)
    assert count == 1
    assert restored[unrelated] == original[unrelated]
    assert restored[dstar] == mcp_saved[dstar]
