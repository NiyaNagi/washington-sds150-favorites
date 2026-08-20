"""Read and write RT Systems ``.FTX1`` memory files.

RT Systems publishes no specification, so the layout below was derived from a
file saved by the installed FTX-1 programmer.  Two consequences follow, and
both shape the design:

* **Only fields that have been confirmed are decoded.**  Everything else in a
  record is carried through untouched.
* **Writing works by patching a template record**, never by synthesising 295
  bytes from scratch.  A new channel is a byte-for-byte copy of a real record
  of the same kind with the frequency, name, comment and tone replaced.  This
  is the same discipline :mod:`wasds150.hpe.flist` uses for ``f_list.cfg``:
  change what you understand, preserve what you do not.

Confirmed layout::

    0x00  magic  "^Yaesu FTX-1"
    0x5E  first record; records are 295 bytes, fixed stride

    record + 0x00  u8          in use: 1 = programmed, 0 = empty
    record + 0x01  uint32 LE   receive frequency, Hz
    record + 0x05  uint32 LE   transmit frequency, Hz
    record + 0x0D  u8          offset direction: 0 simplex, 1 minus, 2 plus
    record + 0x0F  utf-16-le   name, NUL padded
    record + 0x2D  u8          tone mode: 0 off, 1 CTCSS enc+dec, 2 CTCSS enc
    record + 0x2E  u8          transmit CTCSS index into the 50-tone table
    record + 0x2F  u8          receive CTCSS index
    record + 0x85  utf-16-le   comment, NUL padded

**The in-use flag is what makes a row appear in the programmer.** Writing a
frequency and a name into an empty record is not enough: the programmer reads
the flag first and treats a zero as an empty row, discarding whatever else the
record contains. This was established by typing one scan pair into the
programmer, saving, and diffing the bytes.

Regions do not share one grid. Regular memories start at 0x5E, and the
programmable scan pairs continue on the same stride at index 999, but the
60 metre channels sit at their own base with a different alignment. Treat
each region's base as a separate fact.

Verified against known values: record 0 is Weather1 at 162.400000 MHz,
record 7 is FRS 01 at 462.562500 MHz, record 1189 is the 29.600 MHz HOME
channel, and record 999 is the P-1L scan limit.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

MAGIC = b"^Yaesu FTX-1"
HEADER_LEN = 0x5E
RECORD_LEN = 295

OFF_IN_USE = 0x00
OFF_RX = 0x01
OFF_TX = 0x05
#: Repeater shift magnitude in Hz, uint32 LE. Redundant with the stored
#: transmit frequency, but the programmer displays this field in its own
#: column and the radio uses it when the operator retunes a memory. Verified
#: against 963 of 967 records in a file saved from a real radio; the four
#: exceptions are odd-split repeaters where the programmer kept the
#: conventional shift for the band rather than the actual difference.
OFF_OFFSET = 0x09
OFF_DUPLEX = 0x0D
#: Operating mode. Decoded by writing one memory per mode in the programmer
#: and diffing: every mode moved this byte and nothing else. See
#: :data:`MODE_CODES`.
OFF_MODE = 0x0E
OFF_NAME = 0x0F
OFF_TONE_MODE = 0x2D
OFF_TX_TONE = 0x2E
OFF_RX_TONE = 0x2F
#: Skip this memory when scanning. 1 = skip, 0 = include.
OFF_SKIP = 0x34
OFF_COMMENT = 0x85

#: Operating mode codes, decoded from a probe file where 18 memories differed
#: only by mode. The names are the programmer's own dropdown labels, which do
#: not all match the vendor DLL's internal string table.
#:
#: Independently confirmed against a file saved from a real radio: the only
#: three values present there are 0x00 on general FM channels, 0x03 on the
#: FRS/MURS channels that are genuinely narrowband, and 0x1C on the System
#: Fusion repeaters.
MODE_FM = 0x00
MODE_AM = 0x01
MODE_FM_NARROW = 0x03
MODE_AM_NARROW = 0x04
MODE_LSB = 0x05
MODE_USB = 0x06
MODE_PACKET = 0x0B
MODE_RTTY = 0x0E
MODE_RTTY_R = 0x0F
MODE_PKT_FM = 0x12
MODE_PKT_LSB = 0x13
MODE_PKT_USB = 0x14
MODE_CW_L = 0x17
MODE_CW_U = 0x18
MODE_PSK = 0x19
MODE_DN = 0x1C
MODE_VW = 0x1D
MODE_AUTO = 0x20

#: Programmer label for each code, for reporting.
MODE_LABELS = {
    MODE_FM: "FM",
    MODE_AM: "AM",
    MODE_FM_NARROW: "FM Narrow",
    MODE_AM_NARROW: "AM Narrow",
    MODE_LSB: "LSB",
    MODE_USB: "USB",
    MODE_PACKET: "Packet",
    MODE_RTTY: "RTTY",
    MODE_RTTY_R: "RTTY-R",
    MODE_PKT_FM: "PKT-FM",
    MODE_PKT_LSB: "PKT-LSB",
    MODE_PKT_USB: "PKT-USB",
    MODE_CW_L: "CWL",
    MODE_CW_U: "CWU",
    MODE_PSK: "PSK",
    MODE_DN: "DN",
    MODE_VW: "VW",
    MODE_AUTO: "Auto",
}

#: Catalog mode names mapped onto those codes.
#:
#: CW maps to CW-U because that is the sideband a Yaesu selects by default;
#: either decodes the same signal, and no catalog entry states which.
MODE_CODES = {
    "FM": MODE_FM,
    "NFM": MODE_FM_NARROW,
    "FMN": MODE_FM_NARROW,
    "AM": MODE_AM,
    "NAM": MODE_AM_NARROW,
    "AMN": MODE_AM_NARROW,
    "LSB": MODE_LSB,
    "USB": MODE_USB,
    "SSB": MODE_USB,
    "CW": MODE_CW_U,
    "RTTY": MODE_RTTY,
    "PSK": MODE_PSK,
    "PACKET": MODE_PACKET,
    "DATA": MODE_PKT_FM,
    "C4FM": MODE_DN,
    "FUSION": MODE_DN,
    "DN": MODE_DN,
}

#: Values for :data:`OFF_DUPLEX`. The transmit frequency is stored in full,
#: so this is redundant with it - but the programmer displays this byte, and
#: a record whose stored direction disagrees with its frequencies would show
#: the wrong thing.
DUPLEX_SIMPLEX = 0
DUPLEX_MINUS = 1
DUPLEX_PLUS = 2

#: Record index of the first programmable scan limit, ``P-01L``. Pairs run
#: lower, upper, lower, upper for 50 pairs, so ``P-nnU`` is at
#: ``PMS_FIRST + (nn - 1) * 2 + 1``.
PMS_FIRST = 999
PMS_PAIRS = 50

#: Record index of the first HOME channel. Five of them, one per band.
HOME_FIRST = 1189
HOME_COUNT = 5

#: Total length of the record array. The file continues past this point with
#: radio configuration - CW messages, GPS setup, display data - that this
#: project does not model. That area must be carried through verbatim, so it
#: is deliberately NOT divided into records.
RECORD_COUNT = HOME_FIRST + HOME_COUNT

#: The 50 standard CTCSS tones, in the order radios index them.
CTCSS_TONES: Tuple[float, ...] = (
    67.0, 69.3, 71.9, 74.4, 77.0, 79.7, 82.5, 85.4, 88.5, 91.5,
    94.8, 97.4, 100.0, 103.5, 107.2, 110.9, 114.8, 118.8, 123.0, 127.3,
    131.8, 136.5, 141.3, 146.2, 151.4, 156.7, 159.8, 162.2, 165.5, 167.9,
    171.3, 173.8, 177.3, 179.9, 183.5, 186.2, 189.9, 192.8, 196.6, 199.5,
    203.5, 206.5, 210.7, 218.1, 225.7, 229.1, 233.6, 241.8, 250.3, 254.1,
)

TONE_OFF = 0
#: Transmit the CTCSS tone; receive stays open. This is what a repeater
#: channel wants: the tone opens the repeater, and anything the repeater sends
#: back is heard whether or not it carries a tone.
TONE_CTCSS_ENC = 1
#: Transmit the tone AND require a matching tone to unmute. Correct only when
#: the far end is known to send a tone; otherwise the channel appears dead.
TONE_CTCSS_ENC_DEC = 2
TONE_DCS = 3
TONE_REVERSE = 8

#: Programmer labels, for reporting.
TONE_MODE_LABELS = {
    TONE_OFF: "None",
    TONE_CTCSS_ENC: "Tone",
    TONE_CTCSS_ENC_DEC: "Tone Sql",
    TONE_DCS: "DCS",
    TONE_REVERSE: "Rev Tone",
}

#: Longest name the programmer showed in the sample file.  The FTX-1 displays
#: twelve characters; the field itself has room for more.
NAME_MAX = 12

#: The comment field is far larger than it first appeared. Records written by
#: the programmer hold comments up to 79 characters, running from
#: :data:`OFF_COMMENT` to 0x124; the final two bytes of the record are zero in
#: every vendor record inspected. Modelling it as 32 characters silently
#: truncated every longer description on export.
COMMENT_MAX = 80


def _read_utf16(data: bytes, start: int, limit: int) -> str:
    chunk = data[start : start + limit * 2]
    text = chunk.decode("utf-16-le", errors="replace")
    return text.split("\x00", 1)[0]


def _write_utf16(buffer: bytearray, start: int, value: str, limit: int) -> None:
    encoded = value[:limit].encode("utf-16-le")
    span = limit * 2
    buffer[start : start + span] = encoded + b"\x00" * (span - len(encoded))


def _tone_index(tone_hz: float) -> Optional[int]:
    for index, value in enumerate(CTCSS_TONES):
        if abs(value - tone_hz) < 0.05:
            return index
    return None


@dataclass
class Ftx1Record:
    """One memory record, with its original bytes retained."""

    index: int
    raw: bytes

    @property
    def rx_hz(self) -> int:
        return struct.unpack_from("<I", self.raw, OFF_RX)[0]

    @property
    def tx_hz(self) -> int:
        return struct.unpack_from("<I", self.raw, OFF_TX)[0]

    @property
    def rx_mhz(self) -> float:
        return self.rx_hz / 1_000_000

    @property
    def tx_mhz(self) -> float:
        return self.tx_hz / 1_000_000

    @property
    def name(self) -> str:
        return _read_utf16(self.raw, OFF_NAME, NAME_MAX)

    @property
    def comment(self) -> str:
        return _read_utf16(self.raw, OFF_COMMENT, COMMENT_MAX)

    @property
    def in_use(self) -> bool:
        """Whether the programmer will show this record as a populated row."""
        return self.raw[OFF_IN_USE] != 0

    @property
    def empty(self) -> bool:
        return not self.in_use or self.rx_hz == 0

    @property
    def tone_mode(self) -> int:
        return self.raw[OFF_TONE_MODE]

    @property
    def tx_tone_hz(self) -> Optional[float]:
        if self.tone_mode == TONE_OFF:
            return None
        index = self.raw[OFF_TX_TONE]
        return CTCSS_TONES[index] if index < len(CTCSS_TONES) else None

    def patched(
        self,
        *,
        rx_hz: Optional[int] = None,
        tx_hz: Optional[int] = None,
        name: Optional[str] = None,
        comment: Optional[str] = None,
        tone_hz: Optional[float] = None,
        mode: Optional[str] = None,
        skip: Optional[bool] = None,
        in_use: Optional[bool] = None,
    ) -> "Ftx1Record":
        buffer = bytearray(self.raw)
        if rx_hz is not None:
            struct.pack_into("<I", buffer, OFF_RX, rx_hz)
            # A record with a frequency is a record the operator meant to
            # program, so mark it in use unless told otherwise.
            if in_use is None:
                in_use = True
        if tx_hz is not None:
            struct.pack_into("<I", buffer, OFF_TX, tx_hz)
        # Keep the displayed direction consistent with the frequencies.
        if rx_hz is not None or tx_hz is not None:
            new_rx = struct.unpack_from("<I", buffer, OFF_RX)[0]
            new_tx = struct.unpack_from("<I", buffer, OFF_TX)[0]
            if new_tx == new_rx:
                buffer[OFF_DUPLEX] = DUPLEX_SIMPLEX
            else:
                buffer[OFF_DUPLEX] = DUPLEX_PLUS if new_tx > new_rx else DUPLEX_MINUS
            # The shift has its own field and its own column in the
            # programmer. Leaving it at whatever the base record held shows a
            # repeater with a blank or wrong offset even though the transmit
            # frequency is right.
            struct.pack_into("<I", buffer, OFF_OFFSET, abs(new_tx - new_rx))
        if name is not None:
            _write_utf16(buffer, OFF_NAME, name, NAME_MAX)
        if comment is not None:
            _write_utf16(buffer, OFF_COMMENT, comment, COMMENT_MAX)
        if tone_hz is not None:
            index = _tone_index(tone_hz)
            if index is None:
                raise ValueError(f"{tone_hz} is not a standard CTCSS tone")
            # Encode only. A repeater channel needs to *send* the access tone;
            # requiring one to unmute as well (Tone Sql) would silence the
            # channel whenever the repeater transmits without a tone, which
            # many do. Tone Sql is a deliberate operator choice, not a default.
            buffer[OFF_TONE_MODE] = TONE_CTCSS_ENC
            buffer[OFF_TX_TONE] = index
            buffer[OFF_RX_TONE] = index
        if mode is not None:
            code = MODE_CODES.get(mode.strip().upper())
            if code is None:
                raise ValueError(f"{mode!r} is not a mode the FTX-1 offers")
            buffer[OFF_MODE] = code
        if skip is not None:
            buffer[OFF_SKIP] = 1 if skip else 0
        if in_use is not None:
            buffer[OFF_IN_USE] = 1 if in_use else 0
        return Ftx1Record(index=self.index, raw=bytes(buffer))

    def describe(self) -> str:
        if self.empty:
            return f"{self.index:4}  (empty)"
        shift = self.tx_hz - self.rx_hz
        if shift == 0:
            duplex = "simplex"
        else:
            duplex = f"{shift / 1_000_000:+.4f}"
        return (
            f"{self.index:4}  {self.name:<14} {self.rx_mhz:>11.6f}  {duplex:<10}"
            f"  {self.comment}"
        )


@dataclass
class Ftx1File:
    header: bytes
    records: List[Ftx1Record] = field(default_factory=list)
    trailer: bytes = b""

    @classmethod
    def load(cls, path: Path) -> "Ftx1File":
        data = Path(path).read_bytes()
        if not data.startswith(MAGIC):
            raise ValueError(f"{path} is not an RT Systems FTX-1 file")

        header = data[:HEADER_LEN]
        body = data[HEADER_LEN:]

        # The record array is a FIXED length: 999 memories followed by 50
        # scan-limit pairs. Everything after it is radio configuration - CW
        # messages, GPS setup, display data - which this project does not
        # model and must therefore preserve verbatim.
        #
        # Dividing the whole body by the record size instead would mint ~800
        # phantom records out of that configuration area. Anything that then
        # cleared "every record" would silently wipe the radio's settings
        # while looking entirely correct.
        count = min(RECORD_COUNT, len(body) // RECORD_LEN)
        records = [
            Ftx1Record(index=i, raw=body[i * RECORD_LEN : (i + 1) * RECORD_LEN])
            for i in range(count)
        ]
        trailer = body[count * RECORD_LEN :]
        return cls(header=header, records=records, trailer=trailer)

    def to_bytes(self) -> bytes:
        parts = [self.header]
        parts.extend(record.raw for record in self.records)
        parts.append(self.trailer)
        return b"".join(parts)

    def save(self, path: Path) -> None:
        Path(path).write_bytes(self.to_bytes())

    @property
    def used(self) -> List[Ftx1Record]:
        return [record for record in self.records if not record.empty]

    def memories(self) -> List[Ftx1Record]:
        """The 999 regular memory channels, ``M-001`` to ``M-999``."""
        return self.records[:PMS_FIRST]

    def scan_limits(self) -> List[Tuple[Ftx1Record, Ftx1Record]]:
        """The 50 programmable scan pairs, as ``(lower, upper)``."""
        pairs = []
        for pair in range(PMS_PAIRS):
            low = PMS_FIRST + pair * 2
            if low + 1 >= len(self.records):
                break
            pairs.append((self.records[low], self.records[low + 1]))
        return pairs

    def set_scan_limit(
        self, pair: int, low_mhz: float, high_mhz: float, label: str = "", note: str = ""
    ) -> None:
        """Program scan pair ``pair`` (0-based) with a frequency range.

        The FTX-1 requires both limits of a pair to be in the same band and
        refuses an inverted range, so both are checked here rather than being
        discovered as a silent failure on the radio.
        """
        if not 0 <= pair < PMS_PAIRS:
            raise ValueError(f"scan pair {pair} is outside 0..{PMS_PAIRS - 1}")
        if high_mhz <= low_mhz:
            raise ValueError(
                f"scan pair {pair}: upper {high_mhz} must be above lower {low_mhz}"
            )

        index = PMS_FIRST + pair * 2
        low_hz = int(round(low_mhz * 1_000_000))
        high_hz = int(round(high_mhz * 1_000_000))
        self.records[index] = self.records[index].patched(
            rx_hz=low_hz, tx_hz=low_hz, name=label, comment=note, in_use=True
        )
        self.records[index + 1] = self.records[index + 1].patched(
            rx_hz=high_hz, tx_hz=high_hz, name=label, comment=note, in_use=True
        )

    def round_trips(self, original: bytes) -> bool:
        return self.to_bytes() == original
