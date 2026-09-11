"""Icom ID-52A: the CSV set CS-52 and the radio's microSD card read.

These build :class:`PlannedChannel` rows directly rather than resolving a
catalog, the way the TH-D75 target's tests do: what is under test is the file
layout Icom's software expects, not the planner that chose the channels.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from wasds150.export.id52_csv import (
    GROUP_MEMBER_MAX,
    MEMORY_HEADER,
    REPEATER_HEADER,
    Id52ExportError,
    render_files,
    write_id52,
)
from wasds150.models.plan import ChannelPlan
from wasds150.plan.resolve import PlannedChannel, ResolvedPlan
from wasds150.radios.registry import ID52A
from wasds150.radios.tones import parse_tone


def _channel(slot: int, name: str, rx: float, mode: str, block: str, **kw) -> PlannedChannel:
    return PlannedChannel(
        slot=slot, name=name, label=kw.pop("label", name), rx_freq_mhz=rx, mode=mode,
        block=block, source="test", **kw
    )


def _resolved(*channels: PlannedChannel) -> ResolvedPlan:
    plan = ChannelPlan(id="id-52a-test", radio_id="id-52a", label="Test")
    return ResolvedPlan(plan=plan, profile=ID52A, channels=list(channels))


def _rows(text: str):
    return [line.split(",") for line in text.rstrip("\r\n").split("\r\n")]


def test_a_memory_group_carries_icoms_own_columns() -> None:
    files, rows, warnings = render_files(_resolved(
        _channel(1, "KE7DX RPT", 146.96, "NFM", "Ham 2m", bank="Ham 2m", transmit=True,
                 tx_freq_mhz=146.36, tx_tone=parse_tone("TONE=C103.5")),
        _channel(2, "BFI TWR", 118.3, "AM", "Ham 2m", bank="Ham 2m"),
        _channel(3, "NOAA WX2", 162.4, "FM", "Ham 2m", bank="Ham 2m", skip_scan=True),
        _channel(4, "DCS BIZ", 464.5, "NFM", "Ham 2m", bank="Ham 2m", tx_tone=parse_tone("D023")),
    ))
    assert rows == 4 and not warnings
    assert [n for n in files if n.startswith("Csv/MemoryCh")] == ["Csv/MemoryCh/01_Ham_2m.csv"]

    header, *body = _rows(files["Csv/MemoryCh/01_Ham_2m.csv"])
    assert header == list(MEMORY_HEADER)
    by_freq = {row[4]: row for row in body}

    # A repeater: minus duplex from the published input, and the tone that
    # input needs. Receive stays open, so SKIP is the only scan control.
    assert by_freq["146.96"] == [
        "01", "Ham 2m", "00", "KE7DX RPT", "146.96", "DUP-", "0.6", "12.5kHz", "FM-N", "OFF",
        "TONE", "103.5Hz", "103.5Hz", "23", "BOTH N", "", "", "", "", "",
    ]
    # Airband sits on the 8.33 kHz raster; nothing to transmit into.
    assert by_freq["118.3"][5:10] == ["OFF", "0.000000", "8.33kHz", "AM", "OFF"]
    # A locked-out channel is programmed but left out of the scan.
    assert by_freq["162.4"][7:10] == ["25kHz", "FM", "SKIP"]
    # DCS reaches the DTCS column with Icom's leading zero dropped.
    assert by_freq["464.5"][10:14] == ["DTCS", "88.5Hz", "88.5Hz", "23"]


def test_a_d_star_memory_carries_its_routing_and_reaches_the_repeater_list() -> None:
    files, _rows_written, warnings = render_files(_resolved(
        _channel(1, "W7RNK  C", 147.995, "DV", "Ham D-STAR", bank="Ham D-STAR",
                 label="W7RNK  C Newcastle", transmit=True, tx_freq_mhz=147.395,
                 lat=47.542, lon=-122.10883,
                 dv_urcall="CQCQCQ", dv_rpt1="W7RNK  C", dv_rpt2="W7RNK  G"),
    ))
    assert not warnings
    memory = _rows(files["Csv/MemoryCh/01_Ham_D-STAR.csv"])[1]
    assert memory[8] == "DV"
    assert memory[15:] == ["OFF", "00", "CQCQCQ", "W7RNK  C", "W7RNK  G"]

    header, entry = _rows(files["Csv/RptList/DSTAR_Near_Home.csv"])
    assert header == list(REPEATER_HEADER)
    assert entry == [
        "01", "Near Home", "Newcastle", "W7RNK", "W7RNK  C", "W7RNK  G", "147.995", "DUP-", "0.6",
        "DV", "OFF", "88.5Hz", "YES", "Approximate", "47.54200", "-122.10883", "-8:00",
    ]


def test_a_repeater_without_a_position_is_reported_not_listed() -> None:
    files, _rows_written, warnings = render_files(_resolved(
        _channel(1, "N7IH   B", 443.575, "DV", "Ham D-STAR", bank="Ham D-STAR",
                 label="N7IH   B Seattle", dv_rpt1="N7IH   B"),
    ))
    assert warnings == ["N7IH   B Seattle: no position, left out of the repeater list"]
    # The memory is still programmed; only the DR list, which needs a position
    # to steer by, goes without it.
    assert "Csv/MemoryCh/01_Ham_D-STAR.csv" in files
    assert "Csv/RptList/DSTAR_Near_Home.csv" not in files


def test_a_block_longer_than_a_group_is_split() -> None:
    channels = [
        _channel(i + 1, f"Ch {i}", 150.0 + i * 0.0125, "NFM", "Business", bank="Business")
        for i in range(GROUP_MEMBER_MAX + 5)
    ]
    files, rows, _warnings = render_files(_resolved(*channels))
    names = sorted(n for n in files if n.startswith("Csv/MemoryCh"))
    assert names == ["Csv/MemoryCh/01_Business.csv", "Csv/MemoryCh/02_Business_2.csv"]
    assert [len(_rows(files[n])) - 1 for n in names] == [GROUP_MEMBER_MAX, 5]
    # The overflow group names itself, and its members number from zero again.
    assert _rows(files[names[1]])[1][:3] == ["02", "Business 2", "00"]
    assert rows == GROUP_MEMBER_MAX + 5


def test_a_mode_the_radio_cannot_store_is_refused() -> None:
    resolved = _resolved(_channel(1, "P25 talk", 155.1, "P25", "Public Safety", bank="Public Safety"))
    with pytest.raises(Id52ExportError, match="cannot store mode"):
        render_files(resolved)


def test_the_files_land_where_the_radio_reads_them(tmp_path: Path) -> None:
    out = tmp_path / "id-52a-fleet"
    result = write_id52(_resolved(
        _channel(1, "Marine 16", 156.8, "FM", "Marine", bank="Marine"),
    ), out)
    assert {p.relative_to(out).as_posix() for p in result.files} == {
        "Csv/MemoryCh/01_Marine.csv", "IMPORT.txt"
    }
    raw = (out / "Csv" / "MemoryCh" / "01_Marine.csv").read_bytes()
    # CRLF and plain ASCII, as an English-locale CS-52 writes them; a BOM or a
    # bare LF is what makes Icom's importer reject a file.
    assert raw.endswith(b"\r\n") and b"\r\r" not in raw
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert raw.decode("ascii").startswith("Group No,Group Name,CH No,Name,Frequency,")
