"""Frequency spans worth sweeping, for radios with programmable scan limits.

The FTX-1 offers exactly 50 Programmable Memory Scan pairs, and both limits
of a pair must sit in the same band.  That is a hard budget, so the ranges
here are chosen rather than enumerated: each one has to earn its slot by
being somewhere signals actually appear.

Ranges carry the full band edges rather than the operator's licence
privileges.  A receiver benefits from hearing the whole band - most DX sits
in the Extra segment - and the radio will refuse to transmit outside the
privileges regardless.  Where a General cannot transmit across the whole
span, the restriction is stated in the note so it travels with the channel.
"""
from __future__ import annotations

from typing import List, Tuple

from wasds150.radios.bandplan import (
    BANDS_BY_ID,
    CLASS_GENERAL,
    ScanRange,
    general_class_summary,
)

#: Conventional shortwave broadcast meter bands.  These are the ITU
#: broadcasting allocations as universally published in listening references;
#: they are conventions of the broadcasting service rather than amateur rules.
_SWB = (
    ("swb-49m", "SWL 49m", 5.900, 6.200),
    ("swb-41m", "SWL 41m", 7.200, 7.450),
    ("swb-31m", "SWL 31m", 9.400, 9.900),
    ("swb-25m", "SWL 25m", 11.600, 12.100),
    ("swb-19m", "SWL 19m", 15.100, 15.800),
    ("swb-16m", "SWL 16m", 17.480, 17.900),
    ("swb-13m", "SWL 13m", 21.450, 21.850),
)


def _ham(
    range_id: str,
    label: str,
    band_id: str,
    low: float,
    high: float,
    mode: str,
    note: str = "",
    priority: int = 50,
) -> ScanRange:
    band = BANDS_BY_ID[band_id]
    detail = general_class_summary(band)
    if band.prohibited:
        detail = f"{detail}. {band.prohibited}"
    return ScanRange(
        id=range_id,
        label=label,
        low_mhz=low,
        high_mhz=high,
        mode=mode,
        band_id=band_id,
        note=f"{note}. {detail}" if note else detail,
        priority=priority,
    )


#: Amateur HF, split by where the activity actually is.  CW and digital sit
#: at the bottom of every HF band and phone at the top, so a single sweep of
#: a whole band spends most of its time on empty spectrum.
HF_HAM: Tuple[ScanRange, ...] = (
    _ham("160m-all", "160m", "160m", 1.800, 2.000, "LSB", "CW low, phone high", 40),
    _ham("80m-cw", "80m CW/data", "80m", 3.500, 3.600, "CW", "No phone here", 30),
    _ham("75m-phone", "75m phone", "75m", 3.600, 4.000, "LSB", "", 20),
    _ham("60m-band", "60m", "60m", 5.3515, 5.3665, "USB", "USB only, 2.8 kHz", 45),
    _ham("40m-cw", "40m CW/data", "40m", 7.000, 7.125, "CW", "", 15),
    _ham("40m-phone", "40m phone", "40m", 7.125, 7.300, "LSB", "", 10),
    _ham("30m-band", "30m CW/data", "30m", 10.100, 10.150, "CW", "No phone at all", 35),
    _ham("20m-cw", "20m CW/data", "20m", 14.000, 14.150, "CW", "", 12),
    _ham("20m-phone", "20m phone", "20m", 14.150, 14.350, "USB", "", 5),
    _ham("17m-band", "17m", "17m", 18.068, 18.168, "USB", "Phone above 18.110", 25),
    _ham("15m-cw", "15m CW/data", "15m", 21.000, 21.200, "CW", "", 28),
    _ham("15m-phone", "15m phone", "15m", 21.200, 21.450, "USB", "", 18),
    _ham("12m-band", "12m", "12m", 24.890, 24.990, "USB", "Phone above 24.930", 42),
    _ham("10m-cw", "10m CW/data", "10m", 28.000, 28.300, "CW", "", 32),
    _ham("10m-phone", "10m phone", "10m", 28.300, 29.000, "USB", "", 22),
    _ham("10m-fm", "10m FM", "10m", 29.500, 29.700, "FM", "FM repeaters and simplex", 48),
)

#: Amateur VHF and UHF.  1.25 m is deliberately absent: no radio in this
#: project can reach 222-225 MHz.
VHF_UHF_HAM: Tuple[ScanRange, ...] = (
    _ham("6m-ssb", "6m SSB/CW", "6m", 50.000, 50.300, "USB", "Beacons 50.06-50.08", 26),
    _ham("6m-fm", "6m FM", "6m", 51.000, 54.000, "FM", "Repeaters and simplex", 46),
    _ham("2m-ssb", "2m SSB/CW", "2m", 144.000, 144.300, "USB", "Weak signal and EME", 24),
    _ham("2m-fm", "2m FM", "2m", 144.600, 148.000, "FM", "Repeaters and simplex", 8),
    _ham("2m-sat", "2m satellite", "2m", 145.800, 146.000, "USB", "Satellite only", 44),
    _ham("70cm-ssb", "70cm SSB/CW", "70cm", 432.000, 432.400, "USB", "Weak signal", 34),
    _ham("70cm-fm", "70cm FM", "70cm", 440.000, 450.000, "FM", "Repeaters and simplex", 14),
    _ham("70cm-sat", "70cm satellite", "70cm", 435.000, 438.000, "USB", "Satellite only", 47),
)

#: Non-amateur spans the FTX-1 can receive.  These are where a general
#: coverage receiver earns its keep.
UTILITY: Tuple[ScanRange, ...] = (
    ScanRange(
        "ndb", "NDB beacons", 0.190, 0.530, "AM", "lf",
        "Non-directional aeronautical and marine beacons. Receive only.", 55,
    ),
    ScanRange(
        "am-bcast", "AM broadcast", 0.530, 1.700, "AM", "mw",
        "Medium wave broadcast. Receive only.", 60,
    ),
    ScanRange(
        "cb", "CB 11m", 26.965, 27.405, "AM", "cb",
        "Citizens Band, 40 channels. Receive only on this radio.", 52,
    ),
    ScanRange(
        "fm-bcast", "FM broadcast", 88.000, 108.000, "FM", "fmbc",
        "Wide FM broadcast. Receive only.", 70,
    ),
    ScanRange(
        "airband", "VHF airband", 118.000, 136.975, "AM", "air",
        "Civil aviation voice, amplitude modulated. Receive only.", 16,
    ),
    ScanRange(
        "marine-vhf", "Marine VHF", 156.025, 162.025, "FM", "marine",
        "Marine channels including 16 distress and 22A Coast Guard. Receive only.", 18,
    ),
    ScanRange(
        "noaa-wx", "NOAA weather", 162.400, 162.550, "FM", "wx",
        "NOAA Weather Radio. Receive only.", 36,
    ),
    ScanRange(
        "frs-gmrs", "FRS and GMRS", 462.550, 462.725, "FM", "gmrs",
        "FRS and GMRS output channels. Transmit needs a GMRS licence.", 38,
    ),
    ScanRange(
        "murs", "MURS", 151.820, 154.600, "FM", "murs",
        "Multi-Use Radio Service, five channels. No licence required.", 58,
    ),
)

#: Shortwave broadcast, built from the conventional meter-band table.
SHORTWAVE: Tuple[ScanRange, ...] = tuple(
    ScanRange(
        range_id, label, low, high, "AM", "swl",
        "Shortwave broadcast meter band. Receive only.", 62 + index,
    )
    for index, (range_id, label, low, high) in enumerate(_SWB)
)

#: Extra spans worth a slot once the obvious ones are covered.
#:
#: There is deliberately no WWV range. The standards transmit on five widely
#: separated spot frequencies, so a span containing them would cross several
#: bands - which the FTX-1 forbids in a scan pair - and would be almost
#: entirely empty besides. They belong in memories, not a sweep.
EXTRAS: Tuple[ScanRange, ...] = (
    ScanRange(
        "630m", "630m", 0.472, 0.479, "CW", "630m",
        "Amateur 630 m. General and above after UTC registration, 5 W EIRP.", 75,
    ),
    ScanRange(
        "2200m", "2200m", 0.1357, 0.1378, "CW", "2200m",
        "Amateur 2200 m. General and above after UTC registration, 1 W EIRP.", 76,
    ),
    _ham(
        "6m-beacons", "6m beacons", "6m", 50.060, 50.080, "CW",
        "Propagation beacon sub-band; a band opening shows up here first", 43,
    ),
    _ham(
        "10m-beacons", "10m beacons", "10m", 28.190, 28.300, "CW",
        "Propagation beacons including the NCDXF network on 28.200", 41,
    ),
    _ham(
        "2m-packet", "2m APRS/packet", "2m", 144.300, 144.500, "FM",
        "Satellite sub-band and the national APRS channel on 144.390", 49,
    ),
    ScanRange(
        "uhf-business", "UHF business", 461.000, 470.000, "FM", "uhfbiz",
        "Itinerant and business itinerant channels. Receive only.", 72,
    ),
    ScanRange(
        "vhf-business", "VHF business", 151.000, 159.000, "FM", "vhfbiz",
        "Business, public safety and itinerant VHF. Receive only.", 71,
    ),
)

ALL_RANGES: Tuple[ScanRange, ...] = (
    HF_HAM + VHF_UHF_HAM + UTILITY + SHORTWAVE + EXTRAS
)


def ranges_by_priority(limit: int = 50) -> List[ScanRange]:
    """The ``limit`` most useful ranges, best first.

    ``limit`` exists because programmable scan memory is a fixed, small
    resource: the FTX-1 has 50 pairs and no way to add more.
    """
    ordered = sorted(ALL_RANGES, key=lambda r: (r.priority, r.id))
    return ordered[:limit]
