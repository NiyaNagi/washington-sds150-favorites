"""The TH-D75's DR repeater list, in Kenwood's repeater-list TSV format.

MCP-D75 imports Kenwood's worldwide list (``KWD_*.tsv``) under Repeater List.
This writes the same 31 columns for the D-STAR memories a plan programmed, so
the radio's DR list and its memories come from the same registry records
(:mod:`wasds150.catalog.repeater_registry`) instead of an older Kenwood file
that had, for one, K7LWH C on 146.125.
"""
from __future__ import annotations

import codecs
from typing import Iterable, Tuple

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


def render_dstar_tsv(channels: Iterable) -> str:
    """One row per D-STAR repeater among ``channels`` (planned channels) that
    carries routing, an input and a position."""
    rows = ["\t".join(HEADER)]
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
        rows.append("\t".join((
            *_WASHINGTON, rpt1, getattr(channel, "dv_rpt2", "") or f"{rpt1[:7]}G", "Off", name, "Washington",
            f"{channel.rx_freq_mhz:.4f}", "+" if offset >= 0 else "-", f"{abs(offset):g}", "Digital", "Off", "Off",
            "Approx.", lat_d, lat_m, "N" if channel.lat >= 0 else "S", lon_d, lon_m, "E" if channel.lon >= 0 else "W",
            "-08:00", "On", "Off", "On", "USA", "W7", "",
        )))
    return "\r\n".join(rows) + "\r\n"


def encode_dstar_tsv(text: str) -> bytes:
    """The bytes MCP-D75 accepts: UTF-16 LE with a byte-order mark, as
    Kenwood's own lists are. An ASCII file is refused with "the language of
    the selected repeater list differs from the language setting"."""
    return codecs.BOM_UTF16_LE + text.encode("utf-16-le")
