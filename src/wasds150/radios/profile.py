"""Per-radio capability profiles.

The catalog is radio-neutral: it records what a signal *is*, not what any
particular receiver can do with it.  A :class:`RadioProfile` records what one
radio model can do, so the same catalog can be targeted at an SDS150 scanner,
a TD-H9 handheld, or an FTX-1 transceiver without any of those models being
hard-coded into the validation or export paths.

Nothing here decides *policy* (what a user is licensed to transmit on, or
which channels are worth a memory slot).  A profile answers only capability
questions: can this radio tune this frequency, demodulate this mode, store
this many channels, hold a name this long.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Optional, Sequence, Tuple

#: Frequencies are compared in MHz with a small tolerance so that a channel
#: sitting exactly on a band edge (for example 512.000000) is not rejected by
#: floating point representation error.
_EDGE_TOLERANCE_MHZ = 1e-6

BandRanges = Tuple[Tuple[float, float], ...]


def _normalize_bands(bands: Sequence[Sequence[float]]) -> BandRanges:
    normalized = []
    for entry in bands:
        low, high = float(entry[0]), float(entry[1])
        if high < low:
            raise ValueError(f"band ({low}, {high}) has high below low")
        normalized.append((low, high))
    return tuple(sorted(normalized))


def _in_bands(freq_mhz: float, bands: BandRanges) -> bool:
    return any(
        low - _EDGE_TOLERANCE_MHZ <= freq_mhz <= high + _EDGE_TOLERANCE_MHZ
        for low, high in bands
    )


@dataclass(frozen=True)
class RadioProfile:
    """Capabilities of a single radio model.

    ``rx_bands``/``tx_bands`` are inclusive MHz ranges.  An empty ``tx_bands``
    means the radio is receive-only, which is the correct description of a
    scanner and is what keeps the SDS150 from ever being handed a plan that
    assumes it can key up.
    """

    id: str
    vendor: str
    model: str
    rx_bands: BandRanges
    modes: FrozenSet[str]
    tx_bands: BandRanges = ()
    #: ``None`` means "no fixed ceiling this project needs to enforce".
    max_channels: Optional[int] = None
    name_max_len: Optional[int] = None
    #: Characters the radio can store in a channel name.  ``None`` means the
    #: profile does not constrain the character set beyond printable ASCII.
    name_charset: Optional[str] = None
    supports_trunking: bool = False
    supports_talkgroups: bool = False
    #: Named groups/zones/banks that the operator can select on the radio.
    #: The TD-H9 has none, which is why memory *order* is its only structure.
    supports_banks: bool = False
    supports_per_channel_tone: bool = True
    supports_per_channel_mode: bool = True
    #: Some radios store a tuning step globally rather than per memory.
    supports_per_channel_step: bool = True
    notes: str = ""
    #: False when the profile is derived from documentation that has not been
    #: confirmed against hardware.  Consumers may warn rather than fail.
    verified: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "rx_bands", _normalize_bands(self.rx_bands))
        object.__setattr__(self, "tx_bands", _normalize_bands(self.tx_bands))
        object.__setattr__(self, "modes", frozenset(m.upper() for m in self.modes))
        if self.max_channels is not None and self.max_channels <= 0:
            raise ValueError(f"{self.id}: max_channels must be positive")
        if self.name_max_len is not None and self.name_max_len <= 0:
            raise ValueError(f"{self.id}: name_max_len must be positive")

    @property
    def label(self) -> str:
        return f"{self.vendor} {self.model}"

    @property
    def receive_only(self) -> bool:
        return not self.tx_bands

    def can_receive(self, freq_mhz: Optional[float]) -> bool:
        if freq_mhz is None:
            return False
        return _in_bands(freq_mhz, self.rx_bands)

    def can_transmit(self, freq_mhz: Optional[float]) -> bool:
        if freq_mhz is None:
            return False
        return _in_bands(freq_mhz, self.tx_bands)

    def supports_mode(self, mode: Optional[str]) -> bool:
        if not mode:
            return True
        return mode.upper() in self.modes

    def rx_coverage_summary(self) -> str:
        return ", ".join(f"{low:g}-{high:g}" for low, high in self.rx_bands) + " MHz"
