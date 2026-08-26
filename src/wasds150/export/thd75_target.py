"""Write a resolved plan into a settings-preserving Kenwood ``.d75`` file.

The output starts from a real MCP-D75 read of the operator's radio. Only the
three documented ordinary-memory regions are changed: flags, 40-byte channel
records, and 16-byte channel/group names. APRS identity, D-STAR MYCALL,
Bluetooth, GPS, audio, display, menu and special-memory settings remain byte
for byte as read from the radio.

The record layout is independently implemented from the hardware-validated
``swiftraccoon/kenwood`` TH-D75 library and CHIRP's TH-D74/75 driver. A native
MCP-D75 file is a 256-byte header followed by the 500,480-byte MCP image.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from wasds150.plan.resolve import PlannedChannel, ResolvedPlan
from wasds150.radios.tones import TONE_CTCSS, TONE_DCS

HEADER_SIZE = 0x100
IMAGE_SIZE = 0x7A300
FILE_SIZE = HEADER_SIZE + IMAGE_SIZE
MEMORY_COUNT = 1000
GROUP_COUNT = 30
FLAGS_OFFSET = 0x2000
DATA_OFFSET = 0x4000
NAMES_OFFSET = 0x10000
GROUP_NAME_INDEX = 1152
FLAG_SIZE = 4
RECORD_SIZE = 40
NAME_SIZE = 16
CHANNELS_PER_PAGE = 6
PAGE_SIZE = 256
# Valid Band A receive frequency, but outside every TH-D75A transmit band.
# MCP-D75 preserves this value; 0.1 MHz is inside Band B receive coverage but
# the programmer normalizes it back to the channel's receive frequency.
RX_ONLY_TX_HZ = 410_000_000
DSTAR_REGION_START = 0x2A000
DSTAR_REGION_END = 0x4D100

MODE_CODES = {
    "FM": 0,
    "DV": 1,
    "AM": 2,
    "LSB": 3,
    "USB": 4,
    "CW": 5,
    "NFM": 6,
    "WFM": 8,
}

CTCSS_TONES = (
    67.0, 69.3, 71.9, 74.4, 77.0, 79.7, 82.5, 85.4, 88.5, 91.5,
    94.8, 97.4, 100.0, 103.5, 107.2, 110.9, 114.8, 118.8, 123.0,
    127.3, 131.8, 136.5, 141.3, 146.2, 151.4, 156.7, 159.8, 162.2,
    165.5, 167.9, 171.3, 173.8, 177.3, 179.9, 183.5, 186.2, 189.9,
    192.8, 196.6, 199.5, 203.5, 206.5, 210.7, 218.1, 225.7, 229.1,
    233.6, 241.8, 250.3, 254.1,
)
DCS_CODES = (
    23, 25, 26, 31, 32, 36, 43, 47, 51, 53, 54, 65, 71, 72, 73, 74,
    114, 115, 116, 122, 125, 131, 132, 134, 143, 145, 152, 155, 156,
    162, 165, 172, 174, 205, 212, 223, 225, 226, 243, 244, 245, 246,
    251, 252, 255, 261, 263, 265, 266, 271, 274, 306, 311, 315, 325,
    331, 332, 343, 346, 351, 356, 364, 365, 371, 411, 412, 413, 423,
    431, 432, 445, 446, 452, 454, 455, 462, 464, 465, 466, 503, 506,
    516, 523, 526, 532, 546, 565, 606, 612, 624, 627, 631, 632, 654,
    662, 664, 703, 712, 723, 731, 732, 734, 743, 754,
)


class Thd75ExportError(RuntimeError):
    """The source image or requested memory cannot be written safely."""


@dataclass
class Thd75ExportResult:
    rows: int = 0
    groups: int = 0
    warnings: List[str] = field(default_factory=list)


def template_path(root: Optional[Path] = None) -> Path:
    """Return the newest private pre-write radio backup."""
    if root is None:
        here = Path(__file__).resolve()
        for candidate in here.parents:
            if (candidate / "pyproject.toml").is_file():
                root = candidate
                break
        else:
            root = Path.cwd()
    backup_dir = Path(root) / "radio-backups" / "th-d75"
    candidates = sorted(backup_dir.glob("*.d75"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise Thd75ExportError(
            f"no MCP-D75 backup found in {backup_dir}; read the radio before exporting"
        )
    return candidates[0]


def _validate_template(data: bytes) -> None:
    if len(data) != FILE_SIZE:
        raise Thd75ExportError(
            f"TH-D75 template is {len(data):,} bytes; expected exactly {FILE_SIZE:,}"
        )
    header = data[:HEADER_SIZE]
    if not (
        data.startswith(b"Data For TH-D75")
        or (data.startswith(b"MCP-D75\xFFV1.") and b"TH-D75" in header[:32])
    ):
        raise Thd75ExportError("template header does not identify a TH-D75 MCP file")


def _data_offset(slot: int) -> int:
    page, within = divmod(slot, CHANNELS_PER_PAGE)
    return HEADER_SIZE + DATA_OFFSET + page * PAGE_SIZE + within * RECORD_SIZE


def _flag_offset(slot: int) -> int:
    return HEADER_SIZE + FLAGS_OFFSET + slot * FLAG_SIZE


def _name_offset(slot: int) -> int:
    return HEADER_SIZE + NAMES_OFFSET + slot * NAME_SIZE


def _name_bytes(text: str) -> bytes:
    encoded = text.encode("ascii", "replace")[:NAME_SIZE]
    return encoded.ljust(NAME_SIZE, b"\x00")


def _flash_call(text: str) -> bytes:
    encoded = text.encode("ascii", "strict")
    if len(encoded) > 8:
        raise Thd75ExportError(f"D-STAR callsign {text!r} exceeds eight bytes")
    return encoded.ljust(8, b"\x00")


def _band_code(frequency: float) -> int:
    if 50.0 <= frequency < 54.0:
        return 5
    if 216.0 <= frequency < 400.0:
        return 1
    if frequency >= 400.0:
        return 2
    return 0


def _step_code(channel: PlannedChannel) -> int:
    frequency = channel.rx_freq_mhz
    if channel.mode == "WFM":
        return 11  # 100 kHz
    if 0.53 <= frequency <= 1.71 and channel.mode == "AM":
        return 4  # 10 kHz North American broadcast spacing
    if 108.0 <= frequency < 137.0:
        return 2  # 8.33 kHz airband raster
    if channel.mode == "NFM":
        return 5  # 12.5 kHz
    if 462.0 <= frequency <= 468.0:
        return 1  # 6.25 kHz FRS/GMRS/business raster
    return 0  # 5 kHz


def _tone_fields(channel: PlannedChannel) -> Tuple[int, int, int]:
    """Return tone-mode nibble, tone-code index and DCS index."""
    tone = channel.tx_tone
    if not channel.transmit or not tone or tone.kind == "none":
        return 0, 0, 0
    if tone.kind == TONE_CTCSS and tone.ctcss_hz is not None:
        for index, value in enumerate(CTCSS_TONES):
            if abs(value - tone.ctcss_hz) < 0.05:
                return 8, index, 0  # Tone: transmit encoder, open receive squelch
        raise Thd75ExportError(f"{channel.name}: unsupported CTCSS {tone.ctcss_hz:g} Hz")
    if tone.kind == TONE_DCS and tone.dcs_code:
        code = int(tone.dcs_code)
        try:
            return 2, 0, DCS_CODES.index(code)
        except ValueError as exc:
            raise Thd75ExportError(f"{channel.name}: unsupported DCS {tone.dcs_code}") from exc
    return 0, 0, 0


def _record(channel: PlannedChannel, result: Thd75ExportResult) -> bytes:
    record = bytearray(RECORD_SIZE)
    rx_hz = round(channel.rx_freq_mhz * 1_000_000)
    tx_value_hz = 0
    shift = 0
    split = False

    if channel.transmit:
        tx_hz = round((channel.tx_freq_mhz or channel.rx_freq_mhz) * 1_000_000)
        difference = tx_hz - rx_hz
        if difference > 0:
            shift = 1
            tx_value_hz = difference
        elif difference < 0:
            shift = 2
            tx_value_hz = -difference
    elif any(low <= channel.rx_freq_mhz <= high for low, high in ((144.0, 148.0), (222.0, 225.0), (430.0, 450.0))):
        # The radio has no ordinary-memory TX-inhibit bit. An out-of-band odd
        # split makes hardware reject PTT on receive-only amateur memories.
        split = True
        tx_value_hz = RX_ONLY_TX_HZ
        result.warnings.append(
            f"{channel.name}: receive-only memory uses an out-of-band split to inhibit PTT"
        )

    struct.pack_into("<II", record, 0, rx_hz, tx_value_hz)
    step = _step_code(channel)
    record[0x08] = (step << 4) | step
    try:
        mode_code = MODE_CODES[channel.mode]
    except KeyError as exc:
        raise Thd75ExportError(f"{channel.name}: unsupported stored mode {channel.mode!r}") from exc
    if channel.mode == "DV" and channel.dv_rpt1:
        mode_code = 7  # DR: routed D-STAR repeater memory
    fine = channel.mode in {"LSB", "USB", "CW"}
    record[0x09] = (mode_code << 4) | (0x08 if channel.mode == "NFM" else 0) | (0x04 if fine else 0)
    tone_mode, tone_code, dcs_code = _tone_fields(channel)
    record[0x0A] = (tone_mode << 4) | (0x04 if split else 0) | shift
    record[0x0B] = tone_code
    record[0x0C] = 0
    record[0x0D] = dcs_code
    record[0x0E] = 0
    if channel.mode == "DV":
        record[0x0F:0x17] = _flash_call(channel.dv_urcall or "CQCQCQ")
        record[0x17:0x1F] = _flash_call(channel.dv_rpt1)
        record[0x1F:0x27] = _flash_call(channel.dv_rpt2)
    return bytes(record)


def render_thd75(
    resolved: ResolvedPlan,
    *,
    template: Optional[Path] = None,
) -> Tuple[bytes, Thd75ExportResult]:
    if resolved.profile.id != "th-d75":
        raise Thd75ExportError("TH-D75 exporter requires a th-d75 resolved plan")
    path = Path(template) if template is not None else template_path()
    original = path.read_bytes()
    _validate_template(original)
    output = bytearray(original)
    result = Thd75ExportResult()

    # Clear regular memories only. Special/call/weather memories and every
    # other menu setting in the MCP image remain untouched.
    for slot in range(MEMORY_COUNT):
        output[_flag_offset(slot):_flag_offset(slot) + FLAG_SIZE] = b"\xFF" * FLAG_SIZE
        output[_data_offset(slot):_data_offset(slot) + RECORD_SIZE] = b"\xFF" * RECORD_SIZE
        output[_name_offset(slot):_name_offset(slot) + NAME_SIZE] = b"\x00" * NAME_SIZE

    group_by_block: Dict[str, int] = {}
    for planned in resolved.channels:
        bank = planned.bank or planned.block
        if len(group_by_block) >= GROUP_COUNT and bank not in group_by_block:
            raise Thd75ExportError("plan uses more than the TH-D75's 30 memory groups")
        group_by_block.setdefault(bank, len(group_by_block))

    for block, group in group_by_block.items():
        offset = HEADER_SIZE + NAMES_OFFSET + (GROUP_NAME_INDEX + group) * NAME_SIZE
        output[offset:offset + NAME_SIZE] = _name_bytes(block)

    channels = resolved.channels[:MEMORY_COUNT]
    if len(resolved.channels) > MEMORY_COUNT:
        result.warnings.append(
            f"plan resolved {len(resolved.channels)} channels; only the first {MEMORY_COUNT} were written"
        )
    for slot, channel in enumerate(channels):
        group = group_by_block[channel.bank or channel.block]
        output[_flag_offset(slot):_flag_offset(slot) + FLAG_SIZE] = bytes((
            _band_code(channel.rx_freq_mhz),
            1 if channel.skip_scan else 0,
            group,
            0xFF,
        ))
        output[_data_offset(slot):_data_offset(slot) + RECORD_SIZE] = _record(channel, result)
        output[_name_offset(slot):_name_offset(slot) + NAME_SIZE] = _name_bytes(channel.name)

    result.rows = len(channels)
    result.groups = len(group_by_block)
    _validate_template(bytes(output))
    return bytes(output), result


def write_thd75(
    resolved: ResolvedPlan,
    path: Path,
    *,
    template: Optional[Path] = None,
) -> Thd75ExportResult:
    data, result = render_thd75(resolved, template=template)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return result


def inspect_thd75(data: bytes) -> List[Dict[str, object]]:
    """Decode the fields this exporter owns for validation and tests."""
    _validate_template(data)
    rows: List[Dict[str, object]] = []
    for slot in range(MEMORY_COUNT):
        flag = data[_flag_offset(slot):_flag_offset(slot) + FLAG_SIZE]
        if flag[0] == 0xFF:
            continue
        record = data[_data_offset(slot):_data_offset(slot) + RECORD_SIZE]
        name = data[_name_offset(slot):_name_offset(slot) + NAME_SIZE].split(b"\x00", 1)[0].decode("ascii")
        rx_hz, tx_value_hz = struct.unpack_from("<II", record, 0)
        mode_code = record[0x09] >> 4
        rows.append({
            "slot": slot,
            "name": name,
            "rx_mhz": rx_hz / 1_000_000,
            "tx_value_mhz": tx_value_hz / 1_000_000,
            "mode_code": mode_code,
            "split": bool(record[0x0A] & 0x04),
            "shift": record[0x0A] & 0x03,
            "group": flag[2],
            "skip": bool(flag[1] & 0x01),
            "urcall": record[0x0F:0x17].split(b"\x00", 1)[0].decode("ascii"),
            "rpt1": record[0x17:0x1F].split(b"\x00", 1)[0].decode("ascii"),
            "rpt2": record[0x1F:0x27].split(b"\x00", 1)[0].decode("ascii"),
        })
    return rows


def restore_unowned_regions(mcp_saved: bytes, backup: bytes) -> Tuple[bytes, int]:
    """Restore everything MCP-D75 normalized outside intentional regions.

    MCP-D75 rewrites empty special-memory records when it saves a file even
    if the operator edited only the repeater list. This merges the ordinary
    memories and complete native D-STAR region from that save onto the exact
    pre-change radio backup, so unrelated settings remain byte-identical.
    """
    _validate_template(mcp_saved)
    _validate_template(backup)
    output = bytearray(mcp_saved)
    owned = bytearray(FILE_SIZE)

    def mark(start: int, end: int) -> None:
        owned[HEADER_SIZE + start:HEADER_SIZE + end] = b"\x01" * (end - start)

    mark(FLAGS_OFFSET, FLAGS_OFFSET + MEMORY_COUNT * FLAG_SIZE)
    mark(NAMES_OFFSET, NAMES_OFFSET + MEMORY_COUNT * NAME_SIZE)
    mark(
        NAMES_OFFSET + GROUP_NAME_INDEX * NAME_SIZE,
        NAMES_OFFSET + (GROUP_NAME_INDEX + GROUP_COUNT) * NAME_SIZE,
    )
    mark(DSTAR_REGION_START, DSTAR_REGION_END)
    for slot in range(MEMORY_COUNT):
        start = DATA_OFFSET + (slot // CHANNELS_PER_PAGE) * PAGE_SIZE + (slot % CHANNELS_PER_PAGE) * RECORD_SIZE
        mark(start, start + RECORD_SIZE)

    restored = 0
    for index, preserve in enumerate(owned):
        if not preserve and output[index] != backup[index]:
            output[index] = backup[index]
            restored += 1
    return bytes(output), restored
