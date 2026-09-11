"""Icom ID-52A: the CSV files CS-52 and the radio's own SD card read.

Icom's free CS-52 software imports memories one group at a time (Memory CH >
right-click a group > Import > Group) and the D-STAR repeater list the same
way (Digital > Repeater List > Import > Group). The radio reads the same
files from its microSD card, from ``ID-52/Csv/MemoryCh`` and
``ID-52/Csv/RptList``, so this target writes that tree: one CSV per memory
group, plus one repeater-list CSV built from the D-STAR repeaters the plan
programmed.

The columns are the ones real ID-52 CSV files carry:

* memories - ``Group No, Group Name, CH No, Name, Frequency, Dup, Offset,
  TS, Mode, SKIP, TONE, Repeater Tone, TSQL Frequency, DTCS Code, DTCS
  Polarity, DV SQL, DV CSQL Code, Your Call Sign, RPT1 Call Sign, RPT2 Call
  Sign``
* repeater list - ``Group No, Group Name, Name, Sub Name, Repeater Call
  Sign, Gateway Call Sign, Frequency, Dup, Offset, Mode, TONE, Repeater
  Tone, RPT1USE, Position, Latitude, Longitude, UTC Offset``

Fields the catalog cannot know keep Icom's own defaults (DTCS code and
polarity, digital squelch), and files are plain ASCII with comma separators
and dot decimals, as an English-locale CS-52 writes them. A radio holds 100
groups of 100 memories, so a block longer than a group is split into
``Name 2``, ``Name 3`` and so on, the way the Anytone's zones are.

PRELIMINARY: the layout comes from Icom's published documentation and real
ID-52 CSV files, not yet from a file saved by CS-52 itself. Import one group
and check it before writing the radio.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from wasds150.plan.resolve import PlannedChannel, ResolvedPlan
from wasds150.radios.tones import TONE_CTCSS, TONE_DCS

MEMORY_HEADER: Tuple[str, ...] = (
    "Group No", "Group Name", "CH No", "Name", "Frequency", "Dup", "Offset", "TS", "Mode", "SKIP",
    "TONE", "Repeater Tone", "TSQL Frequency", "DTCS Code", "DTCS Polarity",
    "DV SQL", "DV CSQL Code", "Your Call Sign", "RPT1 Call Sign", "RPT2 Call Sign",
)
REPEATER_HEADER: Tuple[str, ...] = (
    "Group No", "Group Name", "Name", "Sub Name", "Repeater Call Sign", "Gateway Call Sign",
    "Frequency", "Dup", "Offset", "Mode", "TONE", "Repeater Tone", "RPT1USE",
    "Position", "Latitude", "Longitude", "UTC Offset",
)

#: Memories per group, and groups, as the ID-52A's manual states them.
GROUP_MEMBER_MAX = 100
GROUP_MAX = 100
#: Entries in the DR repeater list.
REPEATER_MAX = 2500
NAME_MAX = 16
SUB_NAME_MAX = 8
MEMORY_DIR = "Csv/MemoryCh"
REPEATER_DIR = "Csv/RptList"
#: Icom's defaults for fields a monitoring catalog does not carry.
DEFAULT_TONE = "88.5Hz"
DEFAULT_DTCS = "23"
DEFAULT_DTCS_POLARITY = "BOTH N"
#: The DR list stores each repeater's own UTC offset; home is Pacific.
UTC_OFFSET = "-8:00"
#: Every D-STAR position this project holds is the published approximate one.
POSITION = "Approximate"
_MODES = {"FM": "FM", "NFM": "FM-N", "AM": "AM", "WFM": "WFM", "DV": "DV"}
_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9_-]+")


class Id52ExportError(ValueError):
    """The plan cannot be written as ID-52A CSV files."""


@dataclass
class Id52ExportResult:
    text: str
    rows: int
    files: List[Path] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _mhz(value: float) -> str:
    """Icom's own style: dot decimals, no trailing zeros (145.5875, 146.52)."""
    text = f"{float(value):.6f}".rstrip("0")
    return text + "0" if text.endswith(".") else text


def _step(channel: PlannedChannel) -> str:
    if channel.mode in ("AM", "AM-N") and 108.0 <= channel.rx_freq_mhz < 137.0:
        return "8.33kHz"
    if channel.mode == "FM":
        return "25kHz"
    return "12.5kHz"


def _duplex(channel: PlannedChannel) -> Tuple[str, str]:
    """``Dup`` and ``Offset`` from the input frequency the catalog publishes."""
    tx = channel.tx_freq_mhz if channel.transmit else channel.input_freq_mhz
    if tx is None or abs(tx - channel.rx_freq_mhz) < 1e-6:
        return "OFF", "0.000000"
    shift = tx - channel.rx_freq_mhz
    return ("DUP+" if shift > 0 else "DUP-"), _mhz(abs(shift))


def _tones(channel: PlannedChannel) -> Tuple[str, str, str, str]:
    """``TONE``, ``Repeater Tone``, ``TSQL Frequency``, ``DTCS Code``.

    Receive stays open: a monitoring memory with tone squelch would ignore
    every transmission that did not carry it. Only the tone a repeater's
    input needs is programmed."""
    tone = channel.tx_tone
    if tone.kind == TONE_CTCSS and tone.ctcss_hz:
        hertz = f"{tone.ctcss_hz:g}Hz"
        return "TONE", hertz, hertz, DEFAULT_DTCS
    if tone.kind == TONE_DCS and tone.dcs_code:
        return "DTCS", DEFAULT_TONE, DEFAULT_TONE, tone.dcs_code.lstrip("0") or "0"
    return "OFF", DEFAULT_TONE, DEFAULT_TONE, DEFAULT_DTCS


def _group_names(resolved: ResolvedPlan) -> List[Tuple[str, List[PlannedChannel]]]:
    """The plan's blocks as memory groups, in plan order, each within the
    radio's 100-memory group ceiling."""
    ordered: "List[Tuple[str, List[PlannedChannel]]]" = []
    index: Dict[str, int] = {}
    for channel in resolved.channels:
        name = (channel.bank or channel.block)[:NAME_MAX]
        position = index.get(name)
        if position is None:
            index[name] = len(ordered)
            ordered.append((name, [channel]))
        else:
            ordered[position][1].append(channel)
    groups: List[Tuple[str, List[PlannedChannel]]] = []
    for name, members in ordered:
        if len(members) <= GROUP_MEMBER_MAX:
            groups.append((name, members))
            continue
        chunks = [members[i:i + GROUP_MEMBER_MAX] for i in range(0, len(members), GROUP_MEMBER_MAX)]
        for number, chunk in enumerate(chunks, start=1):
            suffix = "" if number == 1 else f" {number}"
            groups.append(((name[: NAME_MAX - len(suffix)] + suffix), chunk))
    if len(groups) > GROUP_MAX:
        raise Id52ExportError(f"{len(groups)} memory groups exceed the radio's {GROUP_MAX}")
    return groups


def _memory_rows(group_no: int, group_name: str, members: Sequence[PlannedChannel]) -> List[List[str]]:
    rows = [list(MEMORY_HEADER)]
    for number, channel in enumerate(members):
        mode = _MODES.get(channel.mode)
        if mode is None:
            raise Id52ExportError(f"{channel.name}: the ID-52A cannot store mode {channel.mode!r}")
        duplex, offset = _duplex(channel)
        tone, repeater_tone, tsql, dtcs = _tones(channel)
        digital = mode == "DV"
        rows.append([
            f"{group_no:02d}", group_name, f"{number:02d}", channel.name[:NAME_MAX], _mhz(channel.rx_freq_mhz),
            duplex, offset, _step(channel), mode, "SKIP" if channel.skip_scan else "OFF",
            tone, repeater_tone, tsql, dtcs, DEFAULT_DTCS_POLARITY,
            "OFF" if digital else "", "00" if digital else "",
            (channel.dv_urcall or "CQCQCQ") if digital else "",
            channel.dv_rpt1 if digital else "",
            channel.dv_rpt2 if digital else "",
        ])
    return rows


def _repeater_rows(resolved: ResolvedPlan, warnings: List[str]) -> List[List[str]]:
    """The DR repeater list: every D-STAR memory the plan programmed that
    carries a repeater call sign and a position."""
    rows = [list(REPEATER_HEADER)]
    seen = set()
    for channel in resolved.channels:
        if channel.mode != "DV" or not channel.dv_rpt1:
            continue
        call = channel.dv_rpt1
        if call in seen:
            continue
        seen.add(call)
        if channel.lat is None or channel.lon is None:
            warnings.append(f"{channel.label}: no position, left out of the repeater list")
            continue
        duplex, offset = _duplex(channel)
        sub_name = call.split()[0][:SUB_NAME_MAX] if call.split() else call[:SUB_NAME_MAX]
        name = channel.label.replace(call, "").strip() or channel.label
        rows.append([
            "01", "Near Home", name[:NAME_MAX], sub_name, call, channel.dv_rpt2 or "",
            _mhz(channel.rx_freq_mhz), duplex, offset, "DV", "OFF", DEFAULT_TONE, "YES",
            POSITION, f"{channel.lat:.5f}", f"{channel.lon:.5f}", UTC_OFFSET,
        ])
    if len(rows) - 1 > REPEATER_MAX:
        raise Id52ExportError(f"{len(rows) - 1} repeaters exceed the radio's {REPEATER_MAX}")
    return rows


def _csv(rows: Sequence[Sequence[str]]) -> str:
    return "".join(",".join(field for field in row) + "\r\n" for row in rows)


def _filename(group_no: int, group_name: str) -> str:
    slug = _FILENAME_SAFE.sub("_", group_name).strip("_") or "Group"
    return f"{group_no:02d}_{slug}"[:23] + ".csv"


def render_files(resolved: ResolvedPlan) -> Tuple[Dict[str, str], int, List[str]]:
    warnings: List[str] = []
    files: Dict[str, str] = {}
    written = 0
    for number, (name, members) in enumerate(_group_names(resolved), start=1):
        files[f"{MEMORY_DIR}/{_filename(number, name)}"] = _csv(_memory_rows(number, name, members))
        written += len(members)
    repeaters = _repeater_rows(resolved, warnings)
    if len(repeaters) > 1:
        files[f"{REPEATER_DIR}/DSTAR_Near_Home.csv"] = _csv(repeaters)
    files["IMPORT.txt"] = (
        "Icom ID-52A\r\n"
        "\r\n"
        "CS-52: Memory CH > right-click the group you want to fill > Import > Group,\r\n"
        f"and choose one file from {MEMORY_DIR}. Repeat per group, in file order.\r\n"
        f"The D-STAR list: Digital > Repeater List > right-click a group > Import > Group,\r\n"
        f"and choose {REPEATER_DIR}/DSTAR_Near_Home.csv. Answer No when asked about USE(FROM).\r\n"
        "\r\n"
        "microSD card: copy the Csv folder into ID-52\\ on the card, then on the radio\r\n"
        "MENU > SD Card > Import/Export > Import.\r\n"
        "\r\n"
        "Close the files in any spreadsheet before importing; Excel keeps them locked.\r\n"
    )
    return files, written, warnings


def render_id52(resolved: ResolvedPlan) -> Id52ExportResult:
    files, rows, warnings = render_files(resolved)
    summary = "\n".join(
        f"{name}: {text.count(chr(10)) - 1} rows" for name, text in sorted(files.items()) if name.endswith(".csv")
    )
    return Id52ExportResult(text=summary, rows=rows, warnings=warnings)


def write_id52(resolved: ResolvedPlan, path: Path) -> Id52ExportResult:
    """Write the CSV tree into directory ``path`` (created if needed)."""
    files, rows, warnings = render_files(resolved)
    path = Path(path)
    written: List[Path] = []
    for name, text in files.items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="ascii", errors="strict", newline="")
        written.append(target)
    summary = "\n".join(
        f"{name}: {text.count(chr(10)) - 1} rows" for name, text in sorted(files.items()) if name.endswith(".csv")
    )
    return Id52ExportResult(text=summary, rows=rows, files=written, warnings=warnings)
