"""TH-D75A - one scannable list for everything tunable within 75 miles.

``thd75-ames-lake`` is a 21-block loadout organised by service. Operators kept
asking the same thing of it: *which group do I scan?* This plan removes that
question. It resolves the same catalog into a single frequency-ordered memory
list so a plain memory scan sweeps every band, and it puts every continuous
carrier - broadcast, CB, HF data, WWV, satellite downlinks - into one trailing
block that is programmed but locked out of the sweep.

The radius is 75 miles from home, applied to each repeater's own WWARA
coordinates. Digital voice modes the TH-D75A cannot decode (DMR, P25, Fusion)
are dropped during resolution; D-STAR is kept and also written to the native
DR list.
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

#: 28523 NE 30th Ct, Redmond WA 98053. Shared with ``ftx1-scan`` so both
#: radios are built around the same point.
HOME = (47.6351, -121.9954)
RADIUS_MILES = 75.0
_WITHIN = (HOME[0], HOME[1], RADIUS_MILES)


def _near(*keys: str, dept: str = "", labels: str = "", ranges=()) -> ChannelSelector:
    return ChannelSelector(
        favorite_keys=tuple(keys),
        department_pattern=dept,
        label_pattern=labels,
        freq_ranges=tuple(ranges),
        within_miles=_WITHIN,
    )


def _sel(*keys: str, dept: str = "", labels: str = "", exclude: str = "", ranges=()) -> ChannelSelector:
    return ChannelSelector(
        favorite_keys=tuple(keys),
        department_pattern=dept,
        label_pattern=labels,
        exclude_label_pattern=exclude,
        freq_ranges=tuple(ranges),
    )


THD75_SCAN = ChannelPlan(
    id="thd75-scan",
    radio_id="th-d75",
    label="TH-D75A - One-List Scan (75 mi)",
    description=(
        "Everything the TH-D75A can tune within 75 miles of home, as a single "
        "frequency-ordered memory list: coordinated 2 m / 1.25 m / 70 cm and "
        "D-STAR repeaters, simplex calling, 6 m/10 m receive, and SAR, "
        "wildfire, interop, marine, air, rail and personal-radio listening. "
        "Broadcast, CB, HF data, time signals and satellites are programmed "
        "but locked out of the scan. Press memory scan and it sweeps every "
        "band."
    ),
    reserve_slots=50,
    blocks=(
        # -- one ascending run, scanned end to end --------------------------
        PlanBlock(
            label="Repeaters 2m 1.25m 70cm",
            selectors=(
                _near(
                    "PSHAM01",
                    dept=r"Analog 2 Meter|Analog 1.25 Meter|Analog 70 Centimeter|Linked Analog",
                    ranges=((144.0, 148.0), (222.0, 225.0), (430.0, 450.0)),
                ),
                _near(
                    "THD75WWARA",
                    dept=r"2 Meter|1.25 Meter|70 Centimeter",
                    ranges=((144.0, 148.0), (222.0, 225.0), (430.0, 450.0)),
                ),
                _sel("THD75USER"),
            ),
            tx_policy=TX_REPEATER,
            power="5.0W",
            sort=SORT_FREQ,
            limit=430,
            notes=(
                "Every current WWARA analog machine within 75 miles. Transmit "
                "uses the published access tone where the coordinator lists "
                "one. 33/23 cm machines are dropped: no receiver there."
            ),
        ),
        PlanBlock(
            label="D-STAR Repeaters",
            selectors=(
                _near("THD75LOCAL", dept=r"D-STAR", ranges=((144.0, 148.0), (430.0, 450.0))),
            ),
            tx_policy=TX_REPEATER,
            power="5.0W",
            sort=SORT_FREQ,
            limit=60,
            notes="Also loaded into the radio's native DR repeater list.",
        ),
        PlanBlock(
            label="Simplex Calling",
            selectors=(
                _sel("HAM01", dept=r"2 meters|70 centimeters", labels=r"FM simplex calling"),
                _sel("THD75LOCAL", dept=r"Calling"),
                _sel("PSHAM01", dept=r"Operator-Published", labels=r"Simplex"),
            ),
            tx_policy=TX_SIMPLEX,
            power="5.0W",
            sort=SORT_FREQ,
            limit=12,
        ),
        PlanBlock(
            label="6m and 10m Amateur",
            selectors=(
                _sel("HAM01", dept=r"6 meters|10 meters", labels=r"FM simplex"),
                _sel("PSHAM01", dept=r"Analog 6 Meter|Linked Analog", ranges=((28.0, 54.0),)),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=30,
            notes="Receive only: the TH-D75A does not transmit on 10 m or 6 m.",
        ),
        PlanBlock(
            label="SAR Wildfire and Interop",
            selectors=(
                _sel("FL01", "FL02", "FL03"),
                _sel("FL06", "FL07", "FL13", "FL16", "FL18", "FL19"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=140,
        ),
        PlanBlock(
            label="Marine Air and Rail",
            selectors=(
                _sel("FL52", "FL53", "FL54"),
                _sel("FL46", "FL48", "FL49"),
                _sel("FL14", "FL17", "FL29", "FL39", "FL43", "FL44", "FL47"),
                _sel("FL56", "FL58"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=220,
        ),
        PlanBlock(
            label="GMRS FRS MURS and Business",
            selectors=(
                _sel("FL65"),
                _sel("FL66", labels=r"MURS|Dot"),
                _sel("FL68"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_NATURAL,
            limit=50,
        ),
        # -- programmed, but locked out of the scan sweep ------------------
        PlanBlock(
            label="Broadcast Data CB and Reference",
            selectors=(
                _sel("FL75"),
                _sel("HAM01", dept=r"Time and Frequency"),
                _sel(
                    "HFNET01",
                    dept=r"Emergency and Weather|Centres of Activity|Utility and Aeronautical|Pacific Northwest|Propagation Beacons",
                ),
                _sel("FL51", labels=r"SSTV|APRS downlink|cross-band repeater|SO-50|AO-91|TEVEL"),
                _sel("FL66", labels=r"CB Ch"),
                _sel("THD75BC", dept=r"FM Broadcast|AM Broadcast"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=200,
            skip_scan=True,
            notes=(
                "NWR, WWV/WWVH, HF nets and beacons, satellite downlinks, the "
                "40 CB channels and FM/AM broadcast. Continuous carriers, so "
                "the scan skips them; tune by hand."
            ),
        ),
    ),
)
