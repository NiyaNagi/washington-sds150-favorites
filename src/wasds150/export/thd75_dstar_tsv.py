"""The TH-D75's DR repeater list, in Kenwood's repeater-list TSV format.

MCP-D75 imports Kenwood's worldwide list (``KWD_*.tsv``) under Repeater List.
This writes the same 31 columns for the D-STAR memories a plan programmed, so
the radio's DR list and its memories come from the same registry records
(:mod:`wasds150.catalog.repeater_registry`) instead of an older Kenwood file
that had, for one, K7LWH C on 146.125.
"""
from __future__ import annotations

import codecs
import struct
from typing import Iterable, List, Tuple

HEADER = (
    "Wn", "World Region", "Cn", "Country", "Gn", "Group", "Callsign", "Gateway", "Lockout", "Name", "Sub Name",
    "Frequency", "Shift", "Offset", "Mode", "Uplink Tone", "Downlink Tone", "Position", "Lat DD", "Lat MM.mm", "N/S",
    "Lon DDD", "Lon MM.mm", "E/W", "Time Zone", "TH-D74A", "TH-D74E", "TH-D74", "Aux 1", "Aux 2", "Aux 3",
)
FILENAME = "th-d75-dstar-repeaters.tsv"
#: Kenwood's region, country and group codes for Washington (its W7 group).
_WASHINGTON = ("4", "North America", "51", "USA", "157", "W7")
NAME_MAX = 16


def _degrees_minutes(value: float) -> Tuple[str, str]:
    degrees = int(abs(value))
    return str(degrees), f"{(abs(value) - degrees) * 60:.2f}"


#: Where the radio keeps its repeater list inside an MCP-D75 file (after the
#: 0x100-byte file header): pages of 0x100 bytes, three 0x50-byte records each.
LIST_START = 0x2A000
LIST_END = 0x4A000
_PAGE, _PER_PAGE, _RECORD = 0x100, 3, 0x50
_FILE_HEADER = 0x100
#: Kenwood's 1-based region, country and group numbers are stored less one.
_KNOWN_GROUPS = {(3, 50, 156): _WASHINGTON}


def _text(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("ascii", "replace")


def read_repeater_list(image: bytes) -> List[Tuple[str, ...]]:
    """The DR repeater list already in an MCP-D75 file, as TSV rows.

    Each record: name (16 bytes), sub name (16), repeater call (8), gateway
    call (8), output Hz and offset Hz (u32 LE), latitude and longitude as
    degrees, minutes and hundredths of a minute x100 (u8, u8, u16 LE), then
    ``+0x43`` shift (2 up, 1 down), ``+0x46..0x48`` region, country and group
    less one, ``+0x4B`` bit 0x02 TH-D74 and 0x04 TH-D74E. Records in a group
    this module has no names for are skipped."""
    rows: List[Tuple[str, ...]] = []
    index = 0
    while True:
        page, within = divmod(index, _PER_PAGE)
        start = _FILE_HEADER + LIST_START + page * _PAGE + within * _RECORD
        if start + _RECORD > _FILE_HEADER + LIST_END or start + _RECORD > len(image):
            break
        record = image[start:start + _RECORD]
        if record[0x20] in (0x00, 0xFF):
            break
        index += 1
        group = _KNOWN_GROUPS.get((record[0x46], record[0x47], record[0x48]))
        if group is None:
            continue
        freq, offset = struct.unpack_from("<II", record, 0x30)
        lat_minutes = record[0x39] + struct.unpack_from("<H", record, 0x3A)[0] / 10000
        lon_minutes = record[0x3D] + struct.unpack_from("<H", record, 0x3E)[0] / 10000
        flags = record[0x4B]
        rows.append((
            *group, _text(record[0x20:0x28]), _text(record[0x28:0x30]), "Off", _text(record[0x00:0x10]),
            _text(record[0x10:0x20]), f"{freq / 1e6:.4f}", "-" if record[0x43] == 1 else "+", f"{offset / 1e6:g}",
            "Digital", "Off", "Off", "Approx.", str(record[0x38]), f"{lat_minutes:.2f}", "N", str(record[0x3C]),
            f"{lon_minutes:.2f}", "W", "-08:00", "On", "On" if flags & 0x04 else "Off", "On" if flags & 0x02 else "Off",
            "USA", group[-1], "",
        ))
    return rows


def render_dstar_tsv(channels: Iterable, existing: Iterable[Tuple[str, ...]] = ()) -> str:
    """One row per D-STAR repeater among ``channels`` (planned channels) that
    carries routing, an input and a position, plus every row of ``existing``
    (the radio's own list, :func:`read_repeater_list`) for a repeater the plan
    does not program. MCP-D75's import replaces the whole list, so a list
    with only the plan's repeaters would drop the rest."""
    rows: List[Tuple[str, ...]] = []
    seen = set()
    for channel in channels:
        rpt1 = getattr(channel, "dv_rpt1", "") or ""
        if (channel.mode or "").upper() != "DV" or not rpt1.strip() or rpt1 in seen:
            continue
        if channel.lat is None or channel.lon is None or channel.tx_freq_mhz is None:
            continue
        seen.add(rpt1)
        offset = round(channel.tx_freq_mhz - channel.rx_freq_mhz, 4)
        lat_d, lat_m = _degrees_minutes(channel.lat)
        lon_d, lon_m = _degrees_minutes(channel.lon)
        label = channel.label or rpt1
        name = (label.split(" - ", 1)[1] if " - " in label else label)[:NAME_MAX]
        rows.append((
            *_WASHINGTON, rpt1, getattr(channel, "dv_rpt2", "") or f"{rpt1[:7]}G", "Off", name, "Washington",
            f"{channel.rx_freq_mhz:.4f}", "+" if offset >= 0 else "-", f"{abs(offset):g}", "Digital", "Off", "Off",
            "Approx.", lat_d, lat_m, "N" if channel.lat >= 0 else "S", lon_d, lon_m, "E" if channel.lon >= 0 else "W",
            "-08:00", "On", "Off", "On", "USA", "W7", "",
        ))
    # The plan's record of a repeater wins (K7LWH C is on 146.4125, not the
    # radio's old 146.125); the radio keeps every other entry it had.
    rows.extend(row for row in existing if row[6] not in seen)
    rows.sort(key=lambda row: (row[9].upper(), row[6]))
    return "\r\n".join(["\t".join(HEADER)] + ["\t".join(row) for row in rows]) + "\r\n"


def encode_dstar_tsv(text: str) -> bytes:
    """The bytes MCP-D75 accepts: UTF-16 LE with a byte-order mark, as
    Kenwood's own lists are. An ASCII file is refused with "the language of
    the selected repeater list differs from the language setting"."""
    return codecs.BOM_UTF16_LE + text.encode("utf-16-le")
