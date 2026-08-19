"""United States amateur band plan, as structured data.

Three different things get called a "band plan", and they are kept separate
here because they have different force:

* :class:`Band` and :class:`LicenseSegment` are **regulation** - 47 CFR 97.301
  says which frequencies each licence class may transmit on. Getting these
  wrong is a legal problem.
* :class:`ModeSegment` is **convention** - the ARRL band plan says where CW,
  digital and phone operators agree to congregate. Getting these wrong is a
  courtesy problem.
* :class:`ScanRange` is **operational** - a span worth sweeping to find
  activity, which is what a radio's programmable scan actually consumes.

Sources are recorded per entry.  Where the ARRL band plan web page and the
Considerate Operator's Frequency Guide disagree - they do, on parts of 10 m
and 40 m - the Considerate Operator's Guide is used, because it is the
document with a date on it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

CFR_97_301 = "https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-97/subpart-D/section-97.301"
CFR_97_305 = "https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-97/subpart-D/section-97.305"
ARRL_BAND_PLAN = "http://www.arrl.org/band-plan"
ARRL_CONOP = "http://www.arrl.org/files/file/conop.pdf"

#: Licence classes in increasing order of privilege.
CLASS_NOVICE = "novice"
CLASS_TECHNICIAN = "technician"
CLASS_GENERAL = "general"
CLASS_ADVANCED = "advanced"
CLASS_EXTRA = "extra"

CLASS_ORDER = (
    CLASS_NOVICE,
    CLASS_TECHNICIAN,
    CLASS_GENERAL,
    CLASS_ADVANCED,
    CLASS_EXTRA,
)


@dataclass(frozen=True)
class LicenseSegment:
    """A span one licence class may transmit on, per 47 CFR 97.301."""

    low_mhz: float
    high_mhz: float
    classes: Tuple[str, ...]
    note: str = ""

    def allows(self, license_class: str) -> bool:
        return license_class in self.classes


@dataclass(frozen=True)
class ModeSegment:
    """A span the ARRL band plan associates with a mode or activity."""

    low_mhz: float
    high_mhz: float
    label: str
    note: str = ""


@dataclass(frozen=True)
class CallingFrequency:
    """A single frequency with an agreed purpose."""

    mhz: float
    label: str
    mode: str
    note: str = ""
    #: False for widely observed conventions that no standards body publishes.
    #: These are still worth programming; they are just not citable as rules.
    official: bool = True


@dataclass(frozen=True)
class Band:
    """One amateur band."""

    id: str
    label: str
    low_mhz: float
    high_mhz: float
    license_segments: Tuple[LicenseSegment, ...] = ()
    mode_segments: Tuple[ModeSegment, ...] = ()
    calling: Tuple[CallingFrequency, ...] = ()
    #: Modes 47 CFR 97.305 forbids anywhere in the band.
    prohibited: str = ""
    note: str = ""

    def segments_for(self, license_class: str) -> List[LicenseSegment]:
        return [s for s in self.license_segments if s.allows(license_class)]

    def may_transmit(self, mhz: float, license_class: str) -> bool:
        return any(
            s.low_mhz <= mhz <= s.high_mhz
            for s in self.license_segments
            if s.allows(license_class)
        )


@dataclass(frozen=True)
class ScanRange:
    """A span worth sweeping, and the reason it is worth sweeping.

    ``band_id`` matters because some radios - the FTX-1 among them - require
    both limits of a programmed scan pair to sit in the same band register.
    """

    id: str
    label: str
    low_mhz: float
    high_mhz: float
    mode: str
    band_id: str
    note: str = ""
    priority: int = 50

    def __post_init__(self) -> None:
        if self.high_mhz <= self.low_mhz:
            raise ValueError(f"{self.id}: high must be above low")

    @property
    def span_khz(self) -> float:
        return (self.high_mhz - self.low_mhz) * 1000


# ---------------------------------------------------------------------------
# Licence segments, 47 CFR 97.301.
# ---------------------------------------------------------------------------

_ALL = (CLASS_GENERAL, CLASS_ADVANCED, CLASS_EXTRA)
_ALL_PLUS_TECH = (CLASS_NOVICE, CLASS_TECHNICIAN) + _ALL
_EXTRA_ONLY = (CLASS_EXTRA,)
_EXTRA_ADV = (CLASS_ADVANCED, CLASS_EXTRA)


BANDS: Tuple[Band, ...] = (
    Band(
        id="160m",
        label="160 meters",
        low_mhz=1.800,
        high_mhz=2.000,
        license_segments=(LicenseSegment(1.800, 2.000, _ALL),),
        mode_segments=(
            ModeSegment(1.800, 1.810, "Digital"),
            ModeSegment(1.810, 1.843, "CW"),
            ModeSegment(1.843, 2.000, "SSB, SSTV and other wideband"),
            ModeSegment(1.995, 2.000, "Experimental"),
            ModeSegment(1.999, 2.000, "Beacons"),
        ),
        calling=(
            CallingFrequency(1.810, "160m QRP CW", "CW", ARRL_CONOP),
            CallingFrequency(1.836600, "160m WSPR", "USB", "WSJT-X default"),
            CallingFrequency(1.840, "160m FT8", "USB", "WSJT-X default"),
            CallingFrequency(1.910, "160m QRP SSB", "LSB", ARRL_CONOP),
        ),
    ),
    Band(
        id="80m",
        label="80 meters",
        low_mhz=3.500,
        high_mhz=3.600,
        license_segments=(
            LicenseSegment(3.500, 3.525, _EXTRA_ONLY),
            LicenseSegment(3.525, 3.600, _ALL_PLUS_TECH),
        ),
        mode_segments=(
            ModeSegment(3.500, 3.510, "CW DX window"),
            ModeSegment(3.510, 3.570, "CW"),
            ModeSegment(3.570, 3.600, "RTTY and data"),
            ModeSegment(3.585, 3.600, "Automatically controlled data stations"),
        ),
        prohibited="No phone or image below 3.600 MHz (47 CFR 97.305)",
        calling=(
            CallingFrequency(3.560, "80m QRP CW", "CW", ARRL_CONOP),
            CallingFrequency(3.568600, "80m WSPR", "USB", "WSJT-X default"),
            CallingFrequency(3.573, "80m FT8", "USB", "WSJT-X default"),
            CallingFrequency(3.575, "80m FT4", "USB", "WSJT-X default"),
            CallingFrequency(3.580, "80m PSK31", "USB", "IARU R2 band plan"),
            CallingFrequency(3.590, "80m RTTY DX", "USB", ARRL_CONOP),
        ),
    ),
    Band(
        id="75m",
        label="75 meters",
        low_mhz=3.600,
        high_mhz=4.000,
        license_segments=(
            LicenseSegment(3.600, 3.700, _EXTRA_ONLY),
            LicenseSegment(3.700, 3.800, _EXTRA_ADV),
            LicenseSegment(3.800, 4.000, _ALL),
        ),
        mode_segments=(
            ModeSegment(3.790, 3.800, "DX window"),
            ModeSegment(3.800, 4.000, "SSB phone"),
        ),
        calling=(
            CallingFrequency(3.845, "75m SSTV", "USB", ARRL_CONOP),
            CallingFrequency(3.885, "75m AM calling", "AM", ARRL_CONOP),
            CallingFrequency(3.985, "75m QRP SSB", "LSB", ARRL_CONOP),
        ),
        note="A General may transmit only above 3.800 MHz.",
    ),
    Band(
        id="60m",
        label="60 meters",
        low_mhz=5.3515,
        high_mhz=5.3665,
        license_segments=(LicenseSegment(5.3515, 5.3665, _ALL),),
        prohibited="USB only, 2.8 kHz maximum bandwidth, 9.15 W ERP in the band",
        calling=(
            CallingFrequency(5.3305, "60m Ch 1", "USB", "47 CFR 97.303(h)(3) discrete channel"),
            CallingFrequency(5.3465, "60m Ch 2", "USB", "47 CFR 97.303(h)(3) discrete channel"),
            CallingFrequency(5.357, "60m FT8", "USB", "WSJT-X default, inside the band"),
            CallingFrequency(5.3715, "60m Ch 3", "USB", "47 CFR 97.303(h)(3) discrete channel"),
            CallingFrequency(5.4035, "60m Ch 4", "USB", "47 CFR 97.303(h)(3) discrete channel"),
        ),
        note=(
            "Four discrete channels sit outside the 5.3515-5.3665 band. Values "
            "here are USB dial frequencies, 1.5 kHz below the channel centre. "
            "The radio's factory 5-01..5-15 memories store centre frequencies "
            "from the older five-channel plan."
        ),
    ),
    Band(
        id="40m",
        label="40 meters",
        low_mhz=7.000,
        high_mhz=7.300,
        license_segments=(
            LicenseSegment(7.000, 7.025, _EXTRA_ONLY),
            LicenseSegment(7.025, 7.125, _ALL_PLUS_TECH),
            LicenseSegment(7.125, 7.175, _EXTRA_ADV),
            LicenseSegment(7.175, 7.300, _ALL),
        ),
        mode_segments=(
            ModeSegment(7.000, 7.070, "CW"),
            ModeSegment(7.070, 7.125, "RTTY and data"),
            ModeSegment(7.100, 7.105, "Automatically controlled data stations"),
            ModeSegment(7.125, 7.300, "SSB phone"),
        ),
        prohibited="No phone below 7.125 MHz except 7.075-7.100 in limited areas",
        calling=(
            CallingFrequency(7.030, "40m QRP CW", "CW", ARRL_CONOP),
            CallingFrequency(7.038600, "40m WSPR", "USB", "WSJT-X default"),
            CallingFrequency(7.040, "40m RTTY DX", "USB", ARRL_CONOP),
            CallingFrequency(7.0475, "40m FT4", "USB", "WSJT-X default"),
            CallingFrequency(7.070, "40m PSK31", "USB", "IARU R2 band plan"),
            CallingFrequency(7.074, "40m FT8", "USB", "WSJT-X default"),
            CallingFrequency(7.171, "40m SSTV", "USB", ARRL_CONOP),
            CallingFrequency(7.285, "40m QRP SSB", "LSB", ARRL_CONOP),
            CallingFrequency(7.290, "40m AM calling", "AM", ARRL_CONOP),
        ),
        note="A General has two segments here: 7.025-7.125 and 7.175-7.300.",
    ),
    Band(
        id="30m",
        label="30 meters",
        low_mhz=10.100,
        high_mhz=10.150,
        license_segments=(LicenseSegment(10.100, 10.150, _ALL),),
        mode_segments=(
            ModeSegment(10.100, 10.130, "CW"),
            ModeSegment(10.130, 10.140, "RTTY and data"),
            ModeSegment(10.140, 10.150, "Automatically controlled data stations"),
        ),
        prohibited="No phone and no image anywhere on 30 m. CW and data only.",
        calling=(
            CallingFrequency(10.136, "30m FT8", "USB", "WSJT-X default"),
            CallingFrequency(10.138700, "30m WSPR", "USB", "WSJT-X default"),
            CallingFrequency(10.140, "30m FT4", "USB", "WSJT-X default"),
            CallingFrequency(10.142, "30m PSK31", "USB", "IARU R2 band plan"),
        ),
    ),
    Band(
        id="20m",
        label="20 meters",
        low_mhz=14.000,
        high_mhz=14.350,
        license_segments=(
            LicenseSegment(14.000, 14.025, _EXTRA_ONLY),
            LicenseSegment(14.025, 14.150, _ALL),
            LicenseSegment(14.150, 14.225, _EXTRA_ADV),
            LicenseSegment(14.225, 14.350, _ALL),
        ),
        mode_segments=(
            ModeSegment(14.000, 14.070, "CW"),
            ModeSegment(14.070, 14.095, "RTTY and data"),
            ModeSegment(14.095, 14.112, "Automatically controlled data stations"),
            ModeSegment(14.112, 14.150, "CW and data"),
            ModeSegment(14.150, 14.350, "SSB phone"),
        ),
        prohibited="No phone below 14.150 MHz",
        calling=(
            CallingFrequency(14.060, "20m QRP CW", "CW", ARRL_CONOP),
            CallingFrequency(14.070, "20m PSK31", "USB", "IARU R2 band plan"),
            CallingFrequency(14.074, "20m FT8", "USB", "WSJT-X default"),
            CallingFrequency(14.080, "20m FT4", "USB", "WSJT-X default"),
            CallingFrequency(14.095600, "20m WSPR", "USB", "WSJT-X default"),
            CallingFrequency(14.100, "20m NCDXF beacon", "CW", ARRL_CONOP),
            CallingFrequency(14.230, "20m SSTV", "USB", ARRL_CONOP),
            CallingFrequency(14.285, "20m QRP SSB", "USB", ARRL_CONOP),
            CallingFrequency(
                14.300, "20m MMSN net", "USB",
                "Maritime Mobile Service Net; a net convention, not an ARRL designation",
                official=False,
            ),
        ),
        note="A General may not use 14.150-14.225.",
    ),
    Band(
        id="17m",
        label="17 meters",
        low_mhz=18.068,
        high_mhz=18.168,
        license_segments=(LicenseSegment(18.068, 18.168, _ALL),),
        mode_segments=(
            ModeSegment(18.068, 18.100, "CW"),
            ModeSegment(18.100, 18.110, "RTTY and data"),
            ModeSegment(18.110, 18.168, "SSB phone"),
        ),
        prohibited="No phone below 18.110 MHz",
        calling=(
            CallingFrequency(18.100, "17m FT8", "USB", "WSJT-X default"),
            CallingFrequency(18.104, "17m FT4", "USB", "WSJT-X default"),
            CallingFrequency(18.104600, "17m WSPR", "USB", "WSJT-X default"),
            CallingFrequency(18.110, "17m NCDXF beacon", "CW", ARRL_CONOP),
        ),
    ),
    Band(
        id="15m",
        label="15 meters",
        low_mhz=21.000,
        high_mhz=21.450,
        license_segments=(
            LicenseSegment(21.000, 21.025, _EXTRA_ONLY),
            LicenseSegment(21.025, 21.200, _ALL_PLUS_TECH),
            LicenseSegment(21.200, 21.275, _EXTRA_ADV),
            LicenseSegment(21.275, 21.450, _ALL),
        ),
        mode_segments=(
            ModeSegment(21.000, 21.070, "CW"),
            ModeSegment(21.070, 21.110, "RTTY and data"),
            ModeSegment(21.090, 21.100, "Automatically controlled data stations"),
            ModeSegment(21.200, 21.450, "SSB phone"),
        ),
        prohibited="No phone below 21.200 MHz",
        calling=(
            CallingFrequency(21.060, "15m QRP CW", "CW", ARRL_CONOP),
            CallingFrequency(21.074, "15m FT8", "USB", "WSJT-X default"),
            CallingFrequency(21.094600, "15m WSPR", "USB", "WSJT-X default"),
            CallingFrequency(21.140, "15m FT4", "USB", "WSJT-X default"),
            CallingFrequency(21.150, "15m NCDXF beacon", "CW", ARRL_CONOP),
            CallingFrequency(21.340, "15m SSTV", "USB", ARRL_CONOP),
            CallingFrequency(21.385, "15m QRP SSB", "USB", ARRL_CONOP),
        ),
        note="A General may not use 21.200-21.275.",
    ),
    Band(
        id="12m",
        label="12 meters",
        low_mhz=24.890,
        high_mhz=24.990,
        license_segments=(LicenseSegment(24.890, 24.990, _ALL),),
        mode_segments=(
            ModeSegment(24.890, 24.920, "CW"),
            ModeSegment(24.920, 24.930, "RTTY and data"),
            ModeSegment(24.930, 24.990, "SSB phone"),
        ),
        prohibited="No phone below 24.930 MHz",
        calling=(
            CallingFrequency(24.915, "12m FT8", "USB", "WSJT-X default"),
            CallingFrequency(24.919, "12m FT4", "USB", "WSJT-X default"),
            CallingFrequency(24.924600, "12m WSPR", "USB", "WSJT-X default"),
            CallingFrequency(24.930, "12m NCDXF beacon", "CW", ARRL_CONOP),
        ),
    ),
    Band(
        id="10m",
        label="10 meters",
        low_mhz=28.000,
        high_mhz=29.700,
        license_segments=(
            LicenseSegment(28.000, 28.500, _ALL_PLUS_TECH),
            LicenseSegment(28.500, 29.700, _ALL),
        ),
        mode_segments=(
            ModeSegment(28.000, 28.070, "CW"),
            ModeSegment(28.070, 28.120, "RTTY and data"),
            ModeSegment(28.120, 28.189, "Automatically controlled data stations"),
            ModeSegment(28.190, 28.225, "Beacons"),
            ModeSegment(28.300, 29.300, "SSB phone"),
            ModeSegment(29.000, 29.200, "AM"),
            ModeSegment(29.300, 29.510, "Satellite"),
            ModeSegment(29.520, 29.580, "FM repeater inputs"),
            ModeSegment(29.620, 29.680, "FM repeater outputs"),
        ),
        prohibited="No phone below 28.300 MHz",
        calling=(
            CallingFrequency(28.060, "10m QRP CW", "CW", ARRL_CONOP),
            CallingFrequency(28.074, "10m FT8", "USB", "WSJT-X default"),
            CallingFrequency(28.124600, "10m WSPR", "USB", "WSJT-X default"),
            CallingFrequency(28.180, "10m FT4", "USB", "WSJT-X default"),
            CallingFrequency(28.200, "10m NCDXF beacon", "CW", ARRL_CONOP),
            CallingFrequency(28.385, "10m QRP SSB", "USB", ARRL_CONOP),
            CallingFrequency(
                28.400, "10m SSB calling", "USB",
                "Widely used but not an ARRL designation", official=False,
            ),
            CallingFrequency(28.680, "10m SSTV", "USB", ARRL_CONOP),
            CallingFrequency(29.600, "10m FM simplex", "FM", ARRL_CONOP),
        ),
    ),
    Band(
        id="6m",
        label="6 meters",
        low_mhz=50.000,
        high_mhz=54.000,
        license_segments=(LicenseSegment(50.000, 54.000, _ALL_PLUS_TECH),),
        mode_segments=(
            ModeSegment(50.000, 50.100, "CW and beacons"),
            ModeSegment(50.060, 50.080, "Beacon sub-band"),
            ModeSegment(50.100, 50.300, "SSB and CW"),
            ModeSegment(50.100, 50.125, "DX window"),
            ModeSegment(50.300, 50.600, "All modes"),
            ModeSegment(50.600, 50.800, "Non-voice"),
            ModeSegment(51.120, 51.480, "FM repeater inputs"),
            ModeSegment(51.620, 51.980, "FM repeater outputs"),
            ModeSegment(52.500, 52.980, "FM repeater outputs"),
        ),
        prohibited="50.000-50.100 is CW only",
        calling=(
            CallingFrequency(50.125, "6m SSB calling", "USB", ARRL_BAND_PLAN),
            CallingFrequency(50.260, "6m MSK144", "USB", "WSJT-X default, Region 2"),
            CallingFrequency(50.293, "6m WSPR", "USB", "WSJT-X default, Region 2"),
            CallingFrequency(50.313, "6m FT8", "USB", "WSJT-X default"),
            CallingFrequency(50.323, "6m FT8 alternate", "USB", "WSJT-X default"),
            CallingFrequency(50.620, "6m digital calling", "USB", ARRL_BAND_PLAN),
            CallingFrequency(52.525, "6m FM simplex", "FM", ARRL_BAND_PLAN),
        ),
    ),
    Band(
        id="2m",
        label="2 meters",
        low_mhz=144.000,
        high_mhz=148.000,
        license_segments=(LicenseSegment(144.000, 148.000, _ALL_PLUS_TECH),),
        mode_segments=(
            ModeSegment(144.000, 144.050, "EME CW"),
            ModeSegment(144.050, 144.100, "General CW and weak signal"),
            ModeSegment(144.100, 144.200, "EME and weak-signal SSB"),
            ModeSegment(144.200, 144.275, "General SSB"),
            ModeSegment(144.275, 144.300, "Propagation beacons"),
            ModeSegment(144.300, 144.500, "Satellite"),
            ModeSegment(144.500, 144.600, "Linear translator inputs"),
            ModeSegment(144.600, 144.900, "FM repeater inputs"),
            ModeSegment(144.900, 145.100, "Weak signal, FM simplex and packet"),
            ModeSegment(145.100, 145.200, "Linear translator outputs"),
            ModeSegment(145.200, 145.500, "FM repeater outputs"),
            ModeSegment(145.500, 145.800, "Miscellaneous and experimental"),
            ModeSegment(145.800, 146.000, "Satellite only"),
            ModeSegment(146.010, 146.370, "FM repeater inputs"),
            ModeSegment(146.400, 146.580, "FM simplex"),
            ModeSegment(146.610, 147.390, "FM repeater outputs"),
            ModeSegment(147.420, 147.570, "FM simplex"),
            ModeSegment(147.600, 147.990, "FM repeater inputs"),
        ),
        prohibited="144.000-144.100 is CW only",
        calling=(
            CallingFrequency(144.174, "2m FT8", "USB", "WSJT-X default"),
            CallingFrequency(144.200, "2m SSB calling", "USB", ARRL_BAND_PLAN),
            CallingFrequency(
                144.390, "2m APRS", "FM",
                "National APRS channel by convention; not an ARRL designation",
                official=False,
            ),
            CallingFrequency(144.489, "2m WSPR", "USB", "WSJT-X default"),
            CallingFrequency(146.520, "2m FM simplex calling", "FM", ARRL_BAND_PLAN),
        ),
    ),
    Band(
        id="70cm",
        label="70 centimeters",
        low_mhz=420.000,
        high_mhz=450.000,
        license_segments=(LicenseSegment(420.000, 450.000, _ALL_PLUS_TECH),),
        mode_segments=(
            ModeSegment(420.000, 426.000, "ATV repeater and simplex"),
            ModeSegment(426.000, 432.000, "ATV simplex"),
            ModeSegment(432.000, 432.070, "EME"),
            ModeSegment(432.070, 432.100, "Weak-signal CW"),
            ModeSegment(432.100, 432.300, "Mixed mode and weak signal"),
            ModeSegment(432.300, 432.400, "Propagation beacons"),
            ModeSegment(433.000, 435.000, "Auxiliary and repeater links"),
            ModeSegment(435.000, 438.000, "Satellite only"),
            ModeSegment(442.000, 445.000, "Repeater inputs and outputs"),
            ModeSegment(445.000, 447.000, "Auxiliary, repeaters and simplex"),
            ModeSegment(447.000, 450.000, "Repeater inputs and outputs"),
        ),
        prohibited="No transmitting on 420-430 MHz north of Line A",
        calling=(
            CallingFrequency(432.065, "70cm Q65 and JT65", "USB", "WSJT-X default"),
            CallingFrequency(432.100, "70cm SSB and CW calling", "USB", ARRL_BAND_PLAN),
            CallingFrequency(432.300, "70cm WSPR", "USB", "WSJT-X default"),
            CallingFrequency(446.000, "70cm FM simplex calling", "FM", ARRL_BAND_PLAN),
        ),
    ),
)

BANDS_BY_ID: Dict[str, Band] = {band.id: band for band in BANDS}

#: 222-225 MHz is a US amateur band, but no radio in this project can reach
#: it: the SDS150 has no transmitter and the FTX-1's receiver has a hard
#: 174-400 MHz gap. It is recorded here so its absence is a stated fact
#: rather than an oversight.
UNREACHABLE_BANDS = {
    "1.25m": (
        "222-225 MHz. The FTX-1 cannot receive 174-400 MHz and the TD-H9 "
        "covers only 220-230 MHz for receive, not transmit."
    ),
}


def band_for(mhz: float) -> Optional[Band]:
    for band in BANDS:
        if band.low_mhz <= mhz <= band.high_mhz:
            return band
    return None


def may_transmit(mhz: float, license_class: str = CLASS_GENERAL) -> bool:
    """True when ``license_class`` may transmit on ``mhz``."""
    band = band_for(mhz)
    return band.may_transmit(mhz, license_class) if band else False


def all_calling_frequencies() -> List[Tuple[Band, CallingFrequency]]:
    return [(band, calling) for band in BANDS for calling in band.calling]


def general_class_summary(band: Band) -> str:
    """One line describing what a General may do in ``band``.

    Adjacent segments are merged: 47 CFR splits 10 m at 28.5 MHz because the
    Technician privileges stop there, but for a General it is one span and
    printing it as two is just noise.
    """
    segments = sorted(band.segments_for(CLASS_GENERAL), key=lambda s: s.low_mhz)
    if not segments:
        return "no General privileges"

    merged: List[Tuple[float, float]] = []
    for segment in segments:
        if merged and abs(segment.low_mhz - merged[-1][1]) < 1e-9:
            merged[-1] = (merged[-1][0], segment.high_mhz)
        else:
            merged.append((segment.low_mhz, segment.high_mhz))

    spans = ", ".join(f"{low:g}-{high:g}" for low, high in merged)
    return f"General: {spans} MHz"
