"""Write an Anytone AT-D890UV CPS import bundle.

The Anytone CPS (D890UV CPS 1.05) reads and writes its codeplug as a set of
CSV files plus a ``.LST`` manifest naming them ("Tool > Import > Import
All").  The formats below were taken from a real ``Export All`` of a 1.0x
codeplug and cross-checked against the column names in the CPS's own
``english.ini``:

* every field on every line is double-quoted, lines end in CRLF;
* the first column is a 1-based ``No.``;
* channel frequencies carry five decimals, AM air four, FM broadcast three;
* zone and scan-list members are ``|``-joined channel names, with parallel
  ``|``-joined RX/TX frequency columns;
* foreign keys (contact, radio id, scan list, receive group) are the exact
  name written in the other file.

``Channel.CSV`` has 77 columns. Most of them are options this project never
sets, so each row starts from :data:`CHANNEL_DEFAULTS` - a real analog export
row - and only the columns the plan decides are overwritten. That keeps the
file byte-compatible with what the CPS itself writes.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from wasds150.export.atd890_bundle import (
    RADIO_ID_NAME,
    RADIO_ID_PLACEHOLDER,
    Atd890Bundle,
    build_bundle,
)
from wasds150.plan.resolve import PlannedChannel, ResolvedPlan
from wasds150.radios.tones import TONE_CTCSS, TONE_DCS, ToneSpec

CHANNEL_HEADER: Tuple[str, ...] = (
    "No.", "Channel Name", "Receive Frequency", "Transmit Frequency", "Channel Type",
    "Transmit Power", "Band Width", "CTCSS/DCS Decode", "CTCSS/DCS Encode",
    "Contact/Talk Group", "Contact/Talk Group Call Type", "Contact/Talk Group TG/DMR ID",
    "Radio ID", "Busy Lock/TX Permit", "Squelch Mode", "Optional Signal", "DTMF ID",
    "2Tone ID", "5Tone ID", "PTT ID", "RX Color Code", "Slot", "Scan List",
    "Receive Group List", "PTT Prohibit", "Reverse", "Digital Duplex", "Slot Suit",
    "AES Digital Encryption", "Digital Encryption", "Call Confirmation",
    "Talk Around(Simplex)", "Work Alone", "Custom CTCSS", "2TONE Decode", "Ranging",
    "Idle TX", "APRS RX", "Analog APRS PTT Mode", "Digital APRS PTT Mode",
    "APRS Report Type", "Digital APRS Report Channel", "Correct Frequency[Hz]",
    "SMS Confirmation", "Exclude channel from roaming", "DMR MODE", "DataACK Disable",
    "R5toneBot", "R5ToneEot", "Auto Scan", "Ana APRS Mute", "Send Talker Alias DMR/NX",
    "AnaAprsTxPath", "ARC4", "ex_emg_kind", "Rpga_Mdc", "DisturEn", "DisturFreq",
    "dmr_crc_ignore", "compand", "tx_talkalaes", "dup_call", "tx_int", "BtRxState",
    "idle_tx", "nxdn_wn", "NxdnRpga", "nxdnSqCon", "NxdnTxBusy", "NxDnPttId", "EnRan",
    "DeRan", "NxdnEncry", "NxdnGroupId", "NxdnIdNum", "NxdnStateNum", "txcc",
)

#: A real analog channel row from a CPS 1.0x "Export All", used as the
#: template every generated row starts from.
CHANNEL_DEFAULTS: Tuple[str, ...] = (
    "1", "WX-Athens", "144.85000", "144.85000", "A-Analog", "High", "12.5K", "Off", "Off",
    "202", "Group Call", "202", "SV2", "Off", "Carrier", "Off", "1", "1", "1", "Off", "1", "1",
    "None", "None", "Off", "Off", "Off", "Off", "Normal Encryption", "Off", "Off", "Off", "Off",
    "131.8", "1", "Off", "Off", "On", "Off", "Off", "Off", "1", "0", "Off", "0", "1", "1", "0",
    "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0",
    "0", "0", "0", "0", "0", "0", "0", "0", "0", "1",
)

# Column indexes in Channel.CSV that the plan decides.
_COL = {name: index for index, name in enumerate(CHANNEL_HEADER)}

ZONE_HEADER = (
    "No.", "Zone Name", "Zone Channel Member", "Zone Channel Member RX Frequency",
    "Zone Channel Member TX Frequency", "A Channel", "A Channel RX Frequency",
    "A Channel TX Frequency", "B Channel", "B Channel RX Frequency", "B Channel TX Frequency",
    "Zone Hide ",
)
SCANLIST_HEADER = (
    "No.", "Scan List Name", "Scan Channel Member", "Scan Channel Member RX Frequency",
    "Scan Channel Member TX Frequency", "Scan Mode", "Priority Channel Select",
    "Priority Channel 1", "Priority Channel 1 RX Frequency", "Priority Channel 1 TX Frequency",
    "Priority Channel 2", "Priority Channel 2 RX Frequency", "Priority Channel 2 TX Frequency",
    "Revert Channel", "Look Back Time A[s]", "Look Back Time B[s]", "Dropout Delay Time[s]",
    "Dwell Time[s]",
)
SCANLIST_TAIL = ("Off", "Off", "Off", "", "", "Off", "", "", "Selected", "0.5", "0.5", "0.1", "0.1")
TALKGROUP_HEADER = ("No.", "Radio ID", "Name", "Call Type", "Call Alert")
RADIOID_HEADER = ("No.", "Radio ID", "Name")
RXGROUP_HEADER = ("No.", "Group Name", "Contact", "Contact TG/DMR ID")
AMAIR_HEADER = ("No.", "Frequency[MHz]", "Name")
AMZONE_HEADER = ("No.", "Zone Name", "Zone Channel Member", "A Channel", "Scan Channel ")
FM_HEADER = ("No.", "Frequency[MHz]", "Scan", "Name")

#: Order the CPS lists them in its own manifest.
BUNDLE_FILES = (
    "Channel.CSV",
    "RadioIDList.CSV",
    "DMRZone.CSV",
    "ScanList.CSV",
    "DMRTalkGroups.CSV",
    "FM.CSV",
    "DMRReceiveGroupCallList.CSV",
    "AMAir.CSV",
    "AMZone.CSV",
)

POWER_LEVELS = ("Low", "Mid", "High", "Turbo")
_POWER_ALIASES = {"0.2W": "Low", "1.0W": "Low", "2.5W": "Mid", "5.0W": "High", "7.0W": "Turbo", "6.0W": "Turbo"}


@dataclass
class Atd890ExportResult:
    text: str
    rows: int
    files: List[Path] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _f5(mhz: float) -> str:
    return f"{mhz:.5f}"


def _f4(mhz: float) -> str:
    return f"{mhz:.4f}"


def _f3(mhz: float) -> str:
    return f"{mhz:.3f}"


def _tone(spec: ToneSpec) -> str:
    if spec.kind == TONE_CTCSS and spec.ctcss_hz is not None:
        return f"{spec.ctcss_hz:.1f}"
    if spec.kind == TONE_DCS and spec.dcs_code:
        return f"D{spec.dcs_code}N"
    return "Off"


def _power(label: str, warnings: List[str]) -> str:
    if label in POWER_LEVELS:
        return label
    mapped = _POWER_ALIASES.get(label)
    if mapped is None:
        note = f"power {label!r} is not an AT-D890UV level; using High"
        if note not in warnings:
            warnings.append(note)
        return "High"
    return mapped


def _csv(rows: List[List[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerows(rows)
    return buffer.getvalue()


def _tx_frequency(channel: PlannedChannel) -> float:
    """What goes in the Transmit Frequency column.

    A transmit-enabled memory uses the resolved transmit frequency. A
    receive-only digital memory keeps the published repeater input so the
    CPS treats it as a repeater channel (DMR MODE 1); PTT Prohibit stops it
    keying. Receive-only analog memories simply mirror the receive frequency.
    """
    if channel.transmit and channel.tx_freq_mhz is not None:
        return channel.tx_freq_mhz
    if channel.digital is not None and channel.input_freq_mhz is not None:
        return channel.input_freq_mhz
    return channel.rx_freq_mhz


def channel_row(channel: PlannedChannel, number: int, bundle: Atd890Bundle, warnings: List[str]) -> List[str]:
    row = list(CHANNEL_DEFAULTS)
    spec = channel.digital
    digital = spec is not None and spec.protocol in ("DMR", "NXDN")
    tx = _tx_frequency(channel)
    contact_name = bundle.contact_by_channel.get(channel.name, "")
    contact = next((c for c in bundle.contacts if c.name == contact_name), bundle.contacts[0])

    row[_COL["No."]] = str(number)
    row[_COL["Channel Name"]] = channel.name
    row[_COL["Receive Frequency"]] = _f5(channel.rx_freq_mhz)
    row[_COL["Transmit Frequency"]] = _f5(tx)
    row[_COL["Channel Type"]] = "D-Digital" if digital else "A-Analog"
    row[_COL["Transmit Power"]] = _power(channel.power, warnings) if channel.transmit else "Low"
    row[_COL["Band Width"]] = "25K" if channel.mode == "FM" else "12.5K"
    row[_COL["CTCSS/DCS Decode"]] = _tone(channel.rx_tone)
    row[_COL["CTCSS/DCS Encode"]] = _tone(channel.tx_tone) if channel.transmit else "Off"
    row[_COL["Contact/Talk Group"]] = contact.name
    row[_COL["Contact/Talk Group Call Type"]] = contact.call_type
    row[_COL["Contact/Talk Group TG/DMR ID"]] = str(contact.dmr_id)
    row[_COL["Radio ID"]] = RADIO_ID_NAME
    if digital and channel.transmit:
        row[_COL["Busy Lock/TX Permit"]] = "Same Color Code" if tx != channel.rx_freq_mhz else "ChannelFree"
    else:
        row[_COL["Busy Lock/TX Permit"]] = "Off"
    row[_COL["Squelch Mode"]] = "Carrier"
    color = (spec.color_code if spec is not None and spec.color_code is not None else 1)
    row[_COL["RX Color Code"]] = str(color)
    row[_COL["txcc"]] = str(color)
    row[_COL["Slot"]] = str(spec.timeslot if spec is not None and spec.timeslot in (1, 2) else 1)
    row[_COL["Scan List"]] = bundle.scan_list_by_channel.get(channel.name) or "None"
    row[_COL["Receive Group List"]] = bundle.rx_group_by_channel.get(channel.name) or "None"
    row[_COL["PTT Prohibit"]] = "Off" if channel.transmit else "On"
    row[_COL["Idle TX"]] = "Off"
    row[_COL["APRS RX"]] = "Off"
    row[_COL["DMR MODE"]] = "1" if (digital and tx != channel.rx_freq_mhz) else "0"
    row[_COL["DataACK Disable"]] = "0" if digital else "1"
    row[_COL["Send Talker Alias DMR/NX"]] = "1" if digital else "0"
    if spec is not None and spec.protocol == "NXDN":
        ran = spec.ran if spec.ran is not None else 0
        row[_COL["EnRan"]] = str(ran)
        row[_COL["DeRan"]] = str(ran)
        if spec.group_id is not None:
            row[_COL["NxdnGroupId"]] = str(spec.group_id)
    assert len(row) == len(CHANNEL_HEADER)
    return row


def render_files(resolved: ResolvedPlan) -> Tuple[Dict[str, str], Atd890Bundle]:
    bundle = build_bundle(resolved)
    warnings = list(bundle.warnings)

    channel_rows: List[List[str]] = [list(CHANNEL_HEADER)]
    for number, channel in enumerate(bundle.channels, start=1):
        channel_rows.append(channel_row(channel, number, bundle, warnings))

    def members(channels: List[PlannedChannel]) -> Tuple[str, str, str]:
        names = "|".join(c.name for c in channels)
        rx = "|".join(_f5(c.rx_freq_mhz) for c in channels)
        tx = "|".join(_f5(_tx_frequency(c)) for c in channels)
        return names, rx, tx

    def one(c: PlannedChannel) -> Tuple[str, str, str]:
        return members([c])

    zone_rows: List[List[str]] = [list(ZONE_HEADER)]
    for number, zone in enumerate(bundle.zones, start=1):
        names, rx, tx = members(zone.members)
        a_name, a_rx, a_tx = one(zone.a_channel)
        b_name, b_rx, b_tx = one(zone.b_channel)
        zone_rows.append([str(number), zone.name, names, rx, tx, a_name, a_rx, a_tx, b_name, b_rx, b_tx, "0"])

    scan_rows: List[List[str]] = [list(SCANLIST_HEADER)]
    for number, scan in enumerate(bundle.scan_lists, start=1):
        names, rx, tx = members(scan.members)
        scan_rows.append([str(number), scan.name, names, rx, tx, *SCANLIST_TAIL])

    talkgroup_rows: List[List[str]] = [list(TALKGROUP_HEADER)]
    for number, contact in enumerate(bundle.contacts, start=1):
        talkgroup_rows.append([str(number), str(contact.dmr_id), contact.name, contact.call_type, "None"])

    radio_rows: List[List[str]] = [list(RADIOID_HEADER), ["1", str(RADIO_ID_PLACEHOLDER), RADIO_ID_NAME]]

    rx_group_rows: List[List[str]] = [list(RXGROUP_HEADER)]
    for number, group in enumerate(bundle.rx_groups, start=1):
        rx_group_rows.append([
            str(number), group.name,
            "|".join(c.name for c in group.contacts),
            "|".join(str(c.dmr_id) for c in group.contacts),
        ])

    am_rows: List[List[str]] = [list(AMAIR_HEADER)]
    for entry in bundle.am_air:
        am_rows.append([str(entry.index), _f4(entry.freq_mhz), entry.name])

    am_zone_rows: List[List[str]] = [list(AMZONE_HEADER)]
    for number, zone in enumerate(bundle.am_zones, start=1):
        am_zone_rows.append([
            str(number), zone.name,
            "|".join(m.name for m in zone.members),
            zone.members[0].name,
            "|".join(m.name for m in zone.scan_members),
        ])

    fm_rows: List[List[str]] = [list(FM_HEADER)]
    for entry in bundle.fm:
        fm_rows.append([str(entry.index), _f3(entry.freq_mhz), "Add" if entry.scan else "Del", entry.name])

    files = {
        "Channel.CSV": _csv(channel_rows),
        "RadioIDList.CSV": _csv(radio_rows),
        "DMRZone.CSV": _csv(zone_rows),
        "ScanList.CSV": _csv(scan_rows),
        "DMRTalkGroups.CSV": _csv(talkgroup_rows),
        "FM.CSV": _csv(fm_rows),
        "DMRReceiveGroupCallList.CSV": _csv(rx_group_rows),
        "AMAir.CSV": _csv(am_rows),
        "AMZone.CSV": _csv(am_zone_rows),
    }
    manifest_lines = [str(len(BUNDLE_FILES))] + [f'{index},"{name}"' for index, name in enumerate(BUNDLE_FILES)]
    files[f"{resolved.plan.id}.LST"] = "\r\n".join(manifest_lines) + "\r\n"
    bundle.warnings = warnings
    return files, bundle


def render_atd890(resolved: ResolvedPlan) -> Atd890ExportResult:
    files, bundle = render_files(resolved)
    summary = "\n".join(f"{name}: {text.count(chr(10)) - 1} rows" for name, text in files.items() if name.endswith(".CSV"))
    return Atd890ExportResult(text=summary, rows=bundle.rows, warnings=bundle.warnings)


def write_atd890(resolved: ResolvedPlan, path: Path) -> Atd890ExportResult:
    """Write the bundle into directory ``path`` (created if needed)."""
    files, bundle = render_files(resolved)
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    for name, text in files.items():
        target = path / name
        target.write_bytes(text.encode("ascii", errors="replace"))
        written.append(target)
    summary = "\n".join(f"{name}: {text.count(chr(10)) - 1} rows" for name, text in files.items() if name.endswith(".CSV"))
    return Atd890ExportResult(text=summary, rows=bundle.rows, files=written, warnings=bundle.warnings)
