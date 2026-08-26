"""Complete TH-D75A loadout centered on Ames Lake, Washington.

Only site-specific repeaters use the hard 50-mile filter. Shared allocations
(NOAA, marine, aviation, rail, interoperability and personal radio) generally
have no single transmitter coordinate, so they are selected as regional
channel sets and remain receive-only. Unsupported P25/DMR/NXDN/AUTO records
are dropped by the verified TH-D75 profile rather than coerced to analog.
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

HOME = (47.633966, -121.960584)
RADIUS_MILES = 50.0
_WITHIN = (HOME[0], HOME[1], RADIUS_MILES)


def _near(*keys: str, dept: str = "", labels: str = "", ranges=()):
    return ChannelSelector(
        favorite_keys=tuple(keys),
        department_pattern=dept,
        label_pattern=labels,
        freq_ranges=tuple(ranges),
        within_miles=_WITHIN,
    )


def _sel(*keys: str, dept: str = "", labels: str = "", exclude: str = "", ranges=()):
    return ChannelSelector(
        favorite_keys=tuple(keys),
        department_pattern=dept,
        label_pattern=labels,
        exclude_label_pattern=exclude,
        freq_ranges=tuple(ranges),
    )


THD75_AMES_LAKE = ChannelPlan(
    id="thd75-ames-lake",
    radio_id="th-d75",
    label="TH-D75A - Ames Lake 50 Mile",
    description=(
        "Tri-band analog and D-STAR repeaters within 50 miles of Ames Lake, "
        "plus the TH-D75A's useful wideband receive services, broadcasts, "
        "satellites, HF utility channels and native operating channels."
    ),
    reserve_slots=50,
    blocks=(
        PlanBlock(
            label="2m Repeaters",
            selectors=(_near("PSHAM01", dept=r"Analog 2 Meter|Linked Analog", ranges=((144.0, 148.0),)),),
            tx_policy=TX_REPEATER,
            power="5.0W",
            sort=SORT_FREQ,
            limit=100,
        ),
        PlanBlock(
            label="1.25m Repeaters",
            selectors=(_near("PSHAM01", dept=r"Analog 1.25 Meter|Linked Analog", ranges=((222.0, 225.0),)),),
            tx_policy=TX_REPEATER,
            power="5.0W",
            sort=SORT_FREQ,
            limit=80,
        ),
        PlanBlock(
            label="70cm Repeaters",
            selectors=(_near("PSHAM01", dept=r"Analog 70 Centimeter|Linked Analog", ranges=((430.0, 450.0),)),),
            tx_policy=TX_REPEATER,
            power="5.0W",
            sort=SORT_FREQ,
            limit=180,
        ),
        PlanBlock(
            label="D-STAR Local",
            selectors=(_near("THD75LOCAL", dept=r"D-STAR", ranges=((144.0, 148.0), (430.0, 450.0))),),
            tx_policy=TX_REPEATER,
            power="5.0W",
            sort=SORT_FREQ,
            limit=40,
            notes="Also loaded into the radio's native DR repeater list.",
        ),
        PlanBlock(
            label="Amateur Calling",
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
            notes="Receive-only because the TH-D75A does not transmit on 10 m or 6 m.",
        ),
        PlanBlock(
            label="Satellites and ISS",
            selectors=(_sel("FL51", labels=r"SSTV|APRS downlink|cross-band repeater|SO-50|AO-91|TEVEL"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=12,
            skip_scan=True,
            notes="Use pass predictions; satellite status and Doppler shift change over time.",
        ),
        PlanBlock(
            label="NOAA Weather",
            selectors=(_sel("FL75"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=10,
        ),
        PlanBlock(
            label="SAR and Interop",
            selectors=(_sel("FL01", "FL02", "FL03"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=50,
        ),
        PlanBlock(
            label="Wildland Fire",
            selectors=(_sel("FL06", "FL07", "FL13", "FL16", "FL18", "FL19"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=80,
        ),
        PlanBlock(
            label="Marine and USCG",
            selectors=(_sel("FL52", "FL53", "FL54"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=70,
        ),
        PlanBlock(
            label="Civil Aviation",
            selectors=(_sel("FL46", "FL48", "FL49"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=80,
        ),
        PlanBlock(
            label="Military Aviation",
            selectors=(_sel("FL14", "FL17", "FL29", "FL39", "FL43", "FL44", "FL47"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=80,
        ),
        PlanBlock(
            label="Rail and Transit",
            selectors=(_sel("FL56", "FL58"),),
            tx_policy=TX_NONE,
            sort=SORT_NATURAL,
            limit=40,
        ),
        PlanBlock(
            label="GMRS and FRS",
            selectors=(_sel("FL65"),),
            tx_policy=TX_NONE,
            sort=SORT_NATURAL,
            limit=24,
        ),
        PlanBlock(
            label="MURS and Business",
            selectors=(
                _sel("FL66", labels=r"MURS|Dot"),
                _sel("FL68"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=30,
        ),
        PlanBlock(
            label="Citizens Band",
            selectors=(_sel("FL66", labels=r"CB Ch"),),
            tx_policy=TX_NONE,
            sort=SORT_NATURAL,
            limit=40,
            skip_scan=True,
        ),
        PlanBlock(
            label="FM Broadcast",
            selectors=(_sel("THD75BC", dept=r"FM Broadcast"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=40,
            skip_scan=True,
        ),
        PlanBlock(
            label="AM Broadcast",
            selectors=(_sel("THD75BC", dept=r"AM Broadcast"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=35,
            skip_scan=True,
        ),
        PlanBlock(
            label="HF Time Standards",
            selectors=(_sel("HAM01", dept=r"Time and Frequency"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=10,
            skip_scan=True,
        ),
        PlanBlock(
            label="HF Emergency and Utility",
            selectors=(
                _sel("HFNET01", dept=r"Emergency and Weather|Centres of Activity|Utility and Aeronautical|Pacific Northwest"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=40,
            skip_scan=True,
        ),
    ),
)
