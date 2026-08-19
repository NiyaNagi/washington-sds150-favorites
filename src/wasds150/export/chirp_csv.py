"""Write a resolved plan as a CHIRP Generic CSV file.

CHIRP's generic CSV is the interchange format for this project's transceiver
targets.  It is plain text, diffable, parsed by a real implementation we do
not control, and accepted by CHIRP, RT Systems and the TIDRADIO factory CPS
alike - so the durable artifact never depends on one driver's byte layout.

Column semantics follow ``chirp_common.Memory.CSV_FORMAT`` and the parser in
``chirp/drivers/generic_csv.py``.  Two of its behaviours drive decisions here:

* A blank ``Power`` column silently defaults to 50 W.  Power is therefore
  always written, never left empty.
* ``Tone`` selects a *tone mode*, not a value.  ``Tone`` means "transmit a
  CTCSS tone, receive with an open squelch", which is what a repeater channel
  wants; programming ``TSQL`` instead would mute everything not carrying the
  tone.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from wasds150.plan.resolve import PlannedChannel, ResolvedPlan
from wasds150.radios.tones import TONE_CTCSS, TONE_DCS, ToneSpec

#: The exact 21-column header CHIRP writes and detects files by.
CSV_HEADER: Tuple[str, ...] = (
    "Location", "Name", "Frequency", "Duplex", "Offset", "Tone", "rToneFreq",
    "cToneFreq", "DtcsCode", "DtcsPolarity", "RxDtcsCode", "CrossMode", "Mode",
    "TStep", "Skip", "Power", "Comment", "URCALL", "RPT1CALL", "RPT2CALL",
    "DVCODE",
)

#: The 50 standard CTCSS tones CHIRP accepts.  A tone outside this table is a
#: data error somewhere upstream, not something to round to the nearest value.
CTCSS_TONES: Tuple[float, ...] = (
    67.0, 69.3, 71.9, 74.4, 77.0, 79.7, 82.5, 85.4, 88.5, 91.5, 94.8, 97.4,
    100.0, 103.5, 107.2, 110.9, 114.8, 118.8, 123.0, 127.3, 131.8, 136.5,
    141.3, 146.2, 151.4, 156.7, 159.8, 162.2, 165.5, 167.9, 171.3, 173.8,
    177.3, 179.9, 183.5, 186.2, 189.9, 192.8, 196.6, 199.5, 203.5, 206.5,
    210.7, 218.1, 225.7, 229.1, 233.6, 241.8, 250.3, 254.1,
)

#: The 104 standard DCS codes CHIRP accepts.
DCS_CODES: Tuple[int, ...] = (
    23, 25, 26, 31, 32, 36, 43, 47, 51, 53, 54, 65, 71, 72, 73, 74, 114, 115,
    116, 122, 125, 131, 132, 134, 143, 145, 152, 155, 156, 162, 165, 172, 174,
    205, 212, 223, 225, 226, 243, 244, 245, 246, 251, 252, 255, 261, 263, 265,
    266, 271, 274, 306, 311, 315, 325, 331, 332, 343, 346, 351, 356, 364, 365,
    371, 411, 412, 413, 423, 431, 432, 445, 446, 452, 454, 455, 462, 464, 465,
    466, 503, 506, 516, 523, 526, 532, 546, 565, 606, 612, 624, 627, 631, 632,
    654, 662, 664, 703, 712, 723, 731, 732, 734, 743, 754,
)

_DEFAULT_TONE = "88.5"
_DEFAULT_DTCS = "023"
_DEFAULT_TSTEP = "5.00"


@dataclass
class ChirpCsvResult:
    text: str
    rows: int
    warnings: List[str] = field(default_factory=list)


def _format_freq(mhz: float) -> str:
    return f"{mhz:.6f}"


def _tone_columns(channel: PlannedChannel) -> Tuple[str, str, str, str, str, List[str]]:
    """Return ``(tmode, rtone, dtcs, cross_mode, ctone)`` plus warnings."""
    warnings: List[str] = []
    tmode = ""
    rtone = _DEFAULT_TONE
    ctone = _DEFAULT_TONE
    dtcs = _DEFAULT_DTCS
    cross = "Tone->Tone"

    tone: ToneSpec = channel.tx_tone
    if not channel.transmit or tone.kind not in (TONE_CTCSS, TONE_DCS):
        return tmode, rtone, dtcs, cross, ctone, warnings

    if tone.kind == TONE_CTCSS:
        value = tone.ctcss_hz
        if value is None or not any(abs(value - t) < 0.05 for t in CTCSS_TONES):
            warnings.append(
                f"slot {channel.slot} {channel.name}: CTCSS {value} is not a standard "
                "tone and was not programmed"
            )
            return tmode, rtone, dtcs, cross, ctone, warnings
        # "Tone" transmits the tone and receives with an open squelch.
        tmode = "Tone"
        rtone = f"{value:.1f}"
        return tmode, rtone, dtcs, cross, ctone, warnings

    code = tone.dcs_code or ""
    try:
        numeric = int(code)
    except ValueError:
        numeric = -1
    if numeric not in DCS_CODES:
        warnings.append(
            f"slot {channel.slot} {channel.name}: DCS {code} is not a standard code "
            "and was not programmed"
        )
        return tmode, rtone, dtcs, cross, ctone, warnings

    # "DTCS->" transmits DCS and leaves the receive squelch open, matching the
    # CTCSS behaviour above.
    tmode = "Cross"
    cross = "DTCS->"
    dtcs = f"{numeric:03d}"
    return tmode, rtone, dtcs, cross, ctone, warnings


def _duplex_columns(channel: PlannedChannel) -> Tuple[str, str]:
    if not channel.transmit:
        # "off" is CHIRP's explicit transmit inhibit, which is what makes a
        # monitoring channel physically unable to key up.
        return "off", _format_freq(0.0)
    if channel.tx_freq_mhz is None:
        return "", _format_freq(0.0)
    shift = round(channel.tx_freq_mhz - channel.rx_freq_mhz, 6)
    if shift == 0:
        return "", _format_freq(0.0)
    return ("+" if shift > 0 else "-"), _format_freq(abs(shift))


def channel_to_row(channel: PlannedChannel) -> Tuple[List[str], List[str]]:
    tmode, rtone, dtcs, cross, ctone, warnings = _tone_columns(channel)
    duplex, offset = _duplex_columns(channel)
    row = [
        str(channel.slot),
        channel.name,
        _format_freq(channel.rx_freq_mhz),
        duplex,
        offset,
        tmode,
        rtone,
        ctone,
        dtcs,
        "NN",
        _DEFAULT_DTCS,
        cross,
        channel.mode,
        _DEFAULT_TSTEP,
        "S" if channel.skip_scan else "",
        channel.power,
        channel.comment.replace("\n", " ").strip(),
        "", "", "", "",
    ]
    return row, warnings


def render_chirp_csv(resolved: ResolvedPlan) -> ChirpCsvResult:
    """Render ``resolved`` as CHIRP Generic CSV text."""
    warnings: List[str] = []
    buffer = io.StringIO()
    # CHIRP reads with the default dialect; "\n" keeps the file diffable.
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_HEADER)

    for channel in resolved.channels:
        row, row_warnings = channel_to_row(channel)
        if len(row) != len(CSV_HEADER):
            raise AssertionError(
                f"row for slot {channel.slot} has {len(row)} columns, expected {len(CSV_HEADER)}"
            )
        writer.writerow(row)
        warnings.extend(row_warnings)

    return ChirpCsvResult(
        text=buffer.getvalue(), rows=len(resolved.channels), warnings=warnings
    )


def write_chirp_csv(resolved: ResolvedPlan, path: Path) -> ChirpCsvResult:
    result = render_chirp_csv(resolved)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.text, encoding="utf-8", newline="")
    return result
