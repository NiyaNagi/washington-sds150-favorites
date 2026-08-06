"""Hand-curated seed tables for fixed, nationally-standardized public
channel plans that this catalog's own free text only describes as a
*range* (see :mod:`wasds150.sources.static_channels`'s module docstring:
a hyphen-joined range is deliberately never expanded there, since
interpolating "the channels in between" would be fabrication).

**Why a seed table is safe here and a generic range-expansion would not
be**: every table below is a fixed, publicly regulated channel plan --
not a system-specific fact that could vary by jurisdiction or change
without notice:

* ``FL65`` (FRS/GMRS): the shared/GMRS-only/FRS-only channel frequencies
  are set nationwide by 47 CFR Part 95 Subparts B (GMRS) and E (FRS); this
  project ships no other input for that band. The endpoints of the three
  ranges already checked into ``washington-sds150-favorites.csv`` for
  FL65 (462.5625, 467.5625/467.7125, 462.5500/462.7250) match this table's
  channel 1, 8, 14, 15 and 22 values exactly -- the table below only
  supplies the (also fixed, 12.5 kHz-spaced) values in between.
* ``FL02`` (nationwide interoperability): current NIFOG 2.02 VCALL/VTAC,
    UCALL/UTAC, 7CALL/7TAC and post-rebanding 8CALL/8TAC receive/output
    channels, plus current WAFOG STATEOPS1-5 assignments.

* ``FL52``-``FL54`` use the fixed U.S. marine VHF channel plan.
* ``FL66`` uses the fixed FCC 40-channel Class D CB plan, including its
  historical non-linear channel 23/24/25 ordering.

**What is deliberately NOT seeded**: this module never seeds a
system-specific or state-specific plan that is not independently verified. WA's STATEOPS
channels are therefore included only when their literal frequencies are
checked into the catalog, never interpolated from a range.
**Safety gate, not just a key lookup**: ``favorite_key`` strings like
``"FL02"``/``"FL65"`` are only unique *within* a given catalog -- a
different/local/test catalog could coincidentally reuse one for something
unrelated. :func:`seed_channels_for` therefore also requires the row's
own ``departments_or_channels`` text to literally contain each of a
table's :attr:`SeedTable.required_anchors` before applying it, so a seed
can only ever fire for the specific row it was written for.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from wasds150.sources.static_channels import ParsedChannel

#: 47 CFR §95.1763 channel plan: channels 1-7 (shared FRS/GMRS, 462 MHz,
#: 12.5 kHz spacing from the row's own cited 462.5625-462.7125 range),
#: channels 8-14 (FRS-only, 467 MHz, 0.5 W, from the row's own cited
#: 467.5625-467.7125 range), channels 15-22 (GMRS/FRS, 462 MHz,
#: repeater-capable on GMRS, from the row's own cited 462.5500-462.7250
#: range).
_FRS_GMRS_CHANNELS: List[ParsedChannel] = [
    ParsedChannel(label=f"FRS/GMRS Ch{n}", freq_mhz=freq, note="FRS/GMRS shared (462 MHz)")
    for n, freq in enumerate(
        [462.5625, 462.5875, 462.6125, 462.6375, 462.6625, 462.6875, 462.7125], start=1
    )
] + [
    ParsedChannel(label=f"FRS Ch{n}", freq_mhz=freq, note="FRS-only, 0.5W max (467 MHz)")
    for n, freq in enumerate(
        [467.5625, 467.5875, 467.6125, 467.6375, 467.6625, 467.6875, 467.7125], start=8
    )
] + [
    ParsedChannel(label=f"GMRS/FRS Ch{n}", freq_mhz=freq, note="GMRS repeater-capable output (462 MHz)")
    for n, freq in enumerate(
        [462.5500, 462.5750, 462.6000, 462.6250, 462.6500, 462.6750, 462.7000, 462.7250], start=15
    )
]

_NIFOG_INTEROP_CHANNELS: List[ParsedChannel] = [
    *[
        ParsedChannel(
            label, frequency, tone="CTCSS 156.7",
            note=("FMN NIFOG 2.02 nationwide analog interoperability" if frequency < 500
                  else "FM NIFOG 2.02 / WAFOG analog interoperability"),
        )
        for label, frequency in (
            ("VCALL10", 155.7525), ("VTAC11", 151.1375), ("VTAC12", 154.4525),
            ("VTAC13", 158.7375), ("VTAC14", 159.4725),
            ("UCALL40", 453.2125), ("UTAC41", 453.4625), ("UTAC42", 453.7125),
            ("UTAC43", 453.8625), ("8CALL90", 851.0125), ("8TAC91", 851.5125),
            ("8TAC92", 852.0125), ("8TAC93", 852.5125), ("8TAC94", 853.0125),
            ("STATEOPS1", 852.5375), ("STATEOPS2", 852.5625), ("STATEOPS3", 852.5875),
            ("STATEOPS4", 852.6125), ("STATEOPS5", 852.6375),
        )
    ],
    *[
        ParsedChannel(label, frequency, note="P25 NIFOG 2.02 nationwide 700 MHz interoperability")
        for label, frequency in (
            ("7CALL50", 769.24375), ("7TAC51", 769.14375), ("7TAC52", 769.64375),
            ("7TAC53", 770.14375), ("7TAC54", 770.64375),
        )
    ],
]

_CB_CHANNELS: List[ParsedChannel] = [
    ParsedChannel(label=f"CB Ch{number}", freq_mhz=frequency, note="FCC Class D CB channel")
    for number, frequency in enumerate(
        [
            26.965, 26.975, 26.985, 27.005, 27.015, 27.025, 27.035, 27.055,
            27.065, 27.075, 27.085, 27.105, 27.115, 27.125, 27.135, 27.155,
            27.165, 27.175, 27.185, 27.205, 27.215, 27.225, 27.255, 27.235,
            27.245, 27.265, 27.275, 27.285, 27.295, 27.305, 27.315, 27.325,
            27.335, 27.345, 27.355, 27.365, 27.375, 27.385, 27.395, 27.405,
        ],
        start=1,
    )
]

_MARINE_CHANNELS = {
    "FL52": [
        ParsedChannel("Ch5A VTS", 156.250, note="U.S. marine VHF"),
        ParsedChannel("Ch6 Intership", 156.300, note="U.S. marine VHF"),
        ParsedChannel("Ch14 VTS", 156.700, note="U.S. marine VHF"),
        ParsedChannel("Ch67 Intership", 156.375, note="U.S. marine VHF"),
    ],
    "FL53": [
        ParsedChannel("Ch14 VTS", 156.700, note="U.S. marine VHF"),
        ParsedChannel("Ch16 Distress", 156.800, note="U.S. marine VHF"),
        ParsedChannel("Ch78A", 156.925, note="U.S. marine VHF"),
        ParsedChannel("Ch79A", 156.975, note="U.S. marine VHF"),
    ],
    "FL54": [
        ParsedChannel("Ch01A", 156.050, note="U.S. marine VHF"),
        ParsedChannel("Ch13 Bridge", 156.650, note="U.S. marine VHF"),
        ParsedChannel("Ch16 Distress", 156.800, note="U.S. marine VHF"),
    ],
}
_MARINE_ANCHORS = {
    "FL52": ("Ch16", "Ch22A"),
    "FL53": ("Ch14", "Ch79A"),
    "FL54": ("Ch07A", "Port of Seattle"),
}

_SEATTLE_CENTER_CHANNELS = [
    ParsedChannel(label=f"ZSE {frequency:g}", freq_mhz=frequency, note="Seattle Center/FSS published channel")
    for frequency in [119.1, 120.3, 124.85, 125.8, 126.1, 126.3, 128.3, 128.5, 132.6, 133.65, 269.35]
] + [
    ParsedChannel("Seattle Radio FSS", 122.2, note="Flight Service"),
    ParsedChannel("Civil Guard", 121.5, note="AM"),
    ParsedChannel("Military Guard", 243.0, note="AM"),
]

_MOUNTAIN_COMMON_CHANNELS = [
    ParsedChannel("USFS Air Guard", 168.625, note="National wildfire aviation guard"),
    ParsedChannel("WA SAR", 155.160, note="Washington statewide SAR"),
    ParsedChannel("WA DNR Main", 159.420, note="Washington DNR statewide"),
    ParsedChannel("NIFC ICP", 168.550, note="National incident command"),
]

_MOUNTAIN_ANCHORS = {
    "FL32": "168.525",
    "FL33": "169.925",
    "FL34": "169.575",
    "FL35": "169.900",
    "FL36": "171.500",
    "FL37": "169.7250",
    "FL38": "171.425",
    "FL39": "172.225",
    "FL40": "172.350",
    "FL41": "171.475",
    "FL42": "164.825",
    "FL43": "172.325",
}


@dataclass(frozen=True)
class SeedTable:
    """A curated channel table, gated behind a content check so it can
    only ever apply to the specific baseline row it was written for --
    never to an unrelated row that happens to reuse the same
    ``favorite_key`` string (a real risk: ``favorite_key`` is only unique
    *within* a given catalog, e.g. a local/custom catalog or a test
    fixture could coincidentally reuse ``"FL02"`` for something else
    entirely)."""

    #: Every one of these must appear verbatim in the row's own
    #: ``departments_or_channels`` text for this table to apply -- see
    #: :func:`seed_channels_for`. Chosen to be the exact endpoints this
    #: table's own module docstring cites as already being in that text.
    required_anchors: Tuple[str, ...]
    channels: List[ParsedChannel]


#: ``favorite_key`` -> the hand-curated channels to add for that baseline
#: row, on top of whatever :func:`wasds150.sources.static_channels.parse_department_text`
#: already finds in its own free text. Deliberately a small, explicit,
#: auditable table -- see module docstring for why each entry is safe.
SEED_TABLES_BY_FAVORITE_KEY: Dict[str, SeedTable] = {
    "FL65": SeedTable(required_anchors=("462.5625", "467.5625", "462.5500"), channels=_FRS_GMRS_CHANNELS),
    "FL02": SeedTable(required_anchors=("155.7525", "769.24375", "851.0125", "852.5375"), channels=_NIFOG_INTEROP_CHANNELS),
    "FL48": SeedTable(required_anchors=("119.1", "133.65", "269.35"), channels=_SEATTLE_CENTER_CHANNELS),
    "FL66": SeedTable(required_anchors=("27.065", "27.185"), channels=_CB_CHANNELS),
}


def seed_channels_for(favorite_key: str, departments_or_channels: str) -> List[ParsedChannel]:
    """The hand-curated channels (if any) for ``favorite_key`` -- but only
    if ``departments_or_channels`` (that row's own checked-in free text)
    actually contains every one of the matching table's
    :attr:`SeedTable.required_anchors`, so a coincidental
    ``favorite_key`` collision in an unrelated/local/test catalog can
    never pull in this seed's channels (see module docstring). Always
    returns a fresh list (never a shared mutable reference)."""
    text = departments_or_channels or ""
    channels: List[ParsedChannel] = []
    table = SEED_TABLES_BY_FAVORITE_KEY.get(favorite_key)
    if table is not None and all(anchor in text for anchor in table.required_anchors):
        channels.extend(table.channels)
    marine_channels = _MARINE_CHANNELS.get(favorite_key)
    marine_anchors = _MARINE_ANCHORS.get(favorite_key, ())
    if marine_channels and all(anchor in text for anchor in marine_anchors):
        channels.extend(marine_channels)
    mountain_anchor = _MOUNTAIN_ANCHORS.get(favorite_key)
    if mountain_anchor and mountain_anchor in text:
        channels.extend(_MOUNTAIN_COMMON_CHANNELS)
    return list(channels)
