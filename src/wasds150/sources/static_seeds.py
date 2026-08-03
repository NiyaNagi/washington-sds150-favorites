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
* ``FL02`` (NPSPAC interoperability): ICALL/ITAC1-4 are the FCC's own
  nationwide 800 MHz NPSPAC interoperability calling/tactical channels
  (0.5 MHz spacing), not specific to Washington. The row's own text
  already gives the exact endpoints (866.5125 and 868.0125) for
  "ITAC1-4"; this table supplies the two literal intermediate channels.

**What is deliberately NOT seeded**: this module never seeds a
system-specific or state-specific plan that is not independently,
nationally standardized -- e.g. WA's own STATEOPS1-5 channels (also
mentioned only as a range on FL02) are state-specific interoperability
assignments, not an FCC-mandated nationwide table, so they are left for a
local Sentinel HPDB/RadioReference Premium match or manual entry instead
of being interpolated here. The same discipline applies to the CB Class D
40-channel plan (FL66): only the two channels already spelled out
verbatim in the baseline text (Ch9/Ch19) are populated, because the full
plan has a well-known non-linear channel/frequency mapping (channels
22-23 historically interleave for RC-control legacy reasons) that this
project has no independently verified source to reproduce correctly.
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

#: FCC 800 MHz NPSPAC nationwide interoperability calling/tactical
#: channels (0.5 MHz spacing starting at ICALL). ``ICALL`` matches the
#: label the free-text parser already derives from this same row's own
#: "ICALL 866.0125" text, so the two sources dedupe cleanly (see
#: :mod:`wasds150.recipes.systems`).
_NPSPAC_INTEROP_CHANNELS: List[ParsedChannel] = [
    ParsedChannel(label="ICALL", freq_mhz=866.0125, note="NPSPAC nationwide interoperability calling channel"),
    ParsedChannel(label="ITAC1", freq_mhz=866.5125, note="NPSPAC nationwide interoperability tactical channel"),
    ParsedChannel(label="ITAC2", freq_mhz=867.0125, note="NPSPAC nationwide interoperability tactical channel"),
    ParsedChannel(label="ITAC3", freq_mhz=867.5125, note="NPSPAC nationwide interoperability tactical channel"),
    ParsedChannel(label="ITAC4", freq_mhz=868.0125, note="NPSPAC nationwide interoperability tactical channel"),
]


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
    "FL02": SeedTable(required_anchors=("866.0125", "866.5125", "868.0125"), channels=_NPSPAC_INTEROP_CHANNELS),
}


def seed_channels_for(favorite_key: str, departments_or_channels: str) -> List[ParsedChannel]:
    """The hand-curated channels (if any) for ``favorite_key`` -- but only
    if ``departments_or_channels`` (that row's own checked-in free text)
    actually contains every one of the matching table's
    :attr:`SeedTable.required_anchors`, so a coincidental
    ``favorite_key`` collision in an unrelated/local/test catalog can
    never pull in this seed's channels (see module docstring). Always
    returns a fresh list (never a shared mutable reference)."""
    table = SEED_TABLES_BY_FAVORITE_KEY.get(favorite_key)
    if table is None:
        return []
    text = departments_or_channels or ""
    if not all(anchor in text for anchor in table.required_anchors):
        return []
    return list(table.channels)
