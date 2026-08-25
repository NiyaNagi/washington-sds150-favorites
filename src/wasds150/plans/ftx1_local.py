"""FTX-1 - a compact list built around one location.

Where ``ftx1-wa`` fills the radio with everything the catalog offers for the
whole state, this plan answers a narrower question: *what can I actually work
or hear from home, and where should I tune on HF when the bands are open?*

Two consequences follow from that.

**Repeaters are filtered by real distance, not by region.** Every WWARA
repeater carries its own coordinates, so the selector keeps only machines
whose transmitter is within :data:`RADIUS_MILES` of :data:`HOME`. A regional
department fence would answer "is this list relevant near Seattle", which is
not the same question - it would include a repeater 90 miles south that is
nominally in the same region and unusable from here.

**The radius is deliberately generous.** WWARA lets a repeater owner obscure
their site by up to about 50 miles, and marks every coordinate ``unknown``
precision as a result. A hard 50-mile cut would silently drop nearby machines
whose published position has been moved. 60 miles absorbs most of that at the
cost of a few distant entries, which is the better failure direction: an extra
channel is a nuisance, a missing local repeater is a gap you do not discover
until you need it.

Repeaters whose coordination has lapsed are excluded, because the catalog
marks them avoided and selectors skip avoided channels by default. That is the
closest thing WWARA publishes to an "is it still on the air" signal.
"""
from __future__ import annotations

from wasds150.models.plan import (
    SORT_FREQ,
    SORT_NATURAL,
    TX_NONE,
    TX_REPEATER,
    TX_SIMPLEX,
    ChannelPlan,
    ChannelSelector,
    PlanBlock,
)

#: Centre of the radius filter: 98053, Redmond / Union Hill-Novelty Hill, WA.
#: Changing these two numbers and re-exporting produces the same plan built
#: around somewhere else, which is the point of filtering on coordinates
#: rather than on hand-drawn regions.
HOME = (47.6740, -122.0290)

#: See the module docstring: sized to absorb WWARA location fuzzing rather
#: than to describe usable radio range.
RADIUS_MILES = 60.0

_WITHIN = (HOME[0], HOME[1], RADIUS_MILES)


def _near(*keys: str, dept: str = "", labels: str = "", exclude: str = "") -> ChannelSelector:
    """A selector that also requires the channel to be within the radius.

    Channels with no coordinates are dropped by this, which is intended: a
    radius filter that silently kept unlocated channels would not be a filter.
    """
    return ChannelSelector(
        favorite_keys=tuple(keys),
        department_pattern=dept,
        label_pattern=labels,
        exclude_label_pattern=exclude,
        within_miles=_WITHIN,
    )


def _sel(*keys: str, dept: str = "", labels: str = "", exclude: str = "") -> ChannelSelector:
    """An ordinary selector, for content that has no location - HF and the
    band plan are propagation-dependent and belong to no particular place."""
    return ChannelSelector(
        favorite_keys=tuple(keys),
        department_pattern=dept,
        label_pattern=labels,
        exclude_label_pattern=exclude,
    )


FTX1_LOCAL = ChannelPlan(
    id="ftx1-local",
    radio_id="ftx1",
    label="FTX-1 - Local and HF",
    description=(
        "Coordinated amateur repeaters within 60 miles of 98053, plus the HF "
        "nets, utility stations and beacons worth tuning across 160 m to 6 m. "
        "A working list for home rather than a statewide inventory."
    ),
    reserve_slots=40,
    blocks=(
        # Curated first. These carry published net schedules in their notes,
        # and the resolver keeps the first copy of a duplicated frequency - so
        # putting them ahead of the bulk WWARA blocks means the entry with the
        # schedule wins rather than the bare coordination record.
        PlanBlock(
            label="Published Nets and Repeaters",
            selectors=(_sel("PSHAM01", dept=r"Operator-Published"),),
            tx_policy=TX_REPEATER,
            sort=SORT_FREQ,
            limit=12,
            notes=(
                "Operator-published machines with known net schedules. No "
                "radius filter: these are curated by hand and a couple sit "
                "outside the circle but are worth carrying anyway."
            ),
        ),
        # ------------------------------------------------ local repeaters --
        PlanBlock(
            label="Local 2m Repeaters",
            selectors=(_near("PSHAM01", dept=r"Analog 2 Meter|Linked Analog"),),
            tx_policy=TX_REPEATER,
            sort=SORT_FREQ,
            limit=70,
            notes=(
                "Coordinated 2 m machines within 60 miles whose coordination "
                "is current. Transmit needs the access tone, which the catalog "
                "carries where the coordinator publishes one."
            ),
        ),
        PlanBlock(
            label="Local 70cm Repeaters",
            selectors=(_near("PSHAM01", dept=r"Analog 70 Centimeter"),),
            tx_policy=TX_REPEATER,
            sort=SORT_FREQ,
            limit=130,
            notes="Coordinated 70 cm machines within 60 miles.",
        ),
        PlanBlock(
            label="Local 6m Repeaters",
            selectors=(_near("PSHAM01", dept=r"Analog 6 Meter"),),
            tx_policy=TX_REPEATER,
            sort=SORT_FREQ,
            limit=20,
            notes=(
                "6 m repeaters are sparse and worth having: when the band "
                "opens they are the first thing to come alive."
            ),
        ),
        # ------------------------------------------------------ VHF/UHF ----
        PlanBlock(
            label="VHF UHF Calling",
            selectors=(_sel("HAM01", labels=r"simplex calling|SSB calling|SSB and CW calling"),),
            tx_policy=TX_SIMPLEX,
            sort=SORT_FREQ,
            limit=8,
            notes="National calling frequencies on 6 m, 2 m and 70 cm.",
        ),
        # ----------------------------------------------------------- HF ----
        PlanBlock(
            label="HF Emergency Nets",
            selectors=(_sel("HFNET01", dept=r"Emergency and Weather|Centres of Activity"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=14,
            notes=(
                "Receive only. These nets run to a protocol and check-ins are "
                "by invitation during an activation."
            ),
        ),
        PlanBlock(
            label="HF Traffic and Nets",
            selectors=(_sel("HFNET01", dept=r"Traffic and Calling|Pacific Northwest"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=14,
            notes=(
                "Receive only by default. Schedules in the notes are context, "
                "not fact - confirm before relying on one."
            ),
        ),
        PlanBlock(
            label="HF Calling and QRP",
            selectors=(_sel("HAM01", labels=r"QRP|CALLING|CLLNG"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=30,
            notes=(
                "Band-plan calling and QRP centres, 160 m through 10 m. "
                "Receive only: transmit privileges vary by band and licence "
                "class, so enabling them is a deliberate per-channel choice."
            ),
        ),
        PlanBlock(
            label="HF Digital Watering Holes",
            selectors=(_sel("HAM01", labels=r"FT8|FT4|WSPR|PSK31|RTTY|SSTV"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=40,
            skip_scan=True,
            notes=(
                "Programmed but skipped on scan: these carry continuous data "
                "bursts that would stop a sweep on every pass."
            ),
        ),
        PlanBlock(
            label="HF Beacons",
            selectors=(_sel("HFNET01", dept=r"Propagation Beacons"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=6,
            notes=(
                "NCDXF/IARU network. The fastest way to find out where a band "
                "is open right now."
            ),
        ),
        PlanBlock(
            label="Time Standards",
            selectors=(_sel("HFNET01", dept=r"Time and Frequency"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=8,
            notes=(
                "WWV/WWVH. Known power from a known place, so also a receiver "
                "calibration check."
            ),
        ),
        PlanBlock(
            label="HF Utility and Aero",
            selectors=(_sel("HFNET01", dept=r"Utility and Aeronautical"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=16,
            notes=(
                "Oceanic ATC, HFGCS and Coast Guard high seas. Always on, "
                "which makes them dependable propagation references. "
                "Transmitting here is not permitted."
            ),
        ),
        PlanBlock(
            label="6 Meter",
            selectors=(_sel("HFNET01", dept=r"6 Meter Calling"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=8,
            notes="Calling frequencies and the beacon sub-band on the magic band.",
        ),
        # --------------------------------------------------- listening -----
        PlanBlock(
            label="NOAA Weather",
            selectors=(_sel("OZ01", dept="NOAA Weather"), _sel("FL75")),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=10,
            notes="The seven NWR channels.",
        ),
        PlanBlock(
            label="GMRS and FRS",
            selectors=(_sel("OZ01", dept=r"GMRS and FRS"),),
            tx_policy=TX_NONE,
            sort=SORT_NATURAL,
            limit=24,
            notes=(
                "Receive only. The FTX-1 is not certified for Part 95, so "
                "these are for listening even with a GMRS licence."
            ),
        ),
        PlanBlock(
            label="MURS",
            selectors=(_sel("OZ01", dept=r"MURS"),),
            tx_policy=TX_NONE,
            sort=SORT_NATURAL,
            limit=6,
            notes="Receive only, same reasoning as GMRS.",
        ),
        PlanBlock(
            label="Marine VHF",
            selectors=(_sel("OZ01", dept=r"Marine and Vessel Traffic"),),
            tx_policy=TX_NONE,
            sort=SORT_NATURAL,
            limit=20,
            notes="Puget Sound vessel traffic and bridge-to-bridge.",
        ),
        PlanBlock(
            label="Aviation",
            selectors=(_sel("OZ01", dept=r"Aviation"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=20,
            notes="Airband. AM, which the plan sets per channel.",
        ),
    ),
)
