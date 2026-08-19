"""TD-H9 channel plan for a trip based at Lake Ozette.

Ordering is the whole design.  The TD-H9 has no banks or zones, so a scan is
simply a walk down the memory list and the only structure available is which
slot a channel occupies.  Blocks are therefore arranged so that related
traffic sits together and the channels most likely to matter in an emergency
come early.

Transmit policy is set per block and is intentionally conservative:

* GMRS main and repeater channels transmit at the radio's full 10 W.
* GMRS channels 1-7 transmit at 5 W. They are the shared interstitials, and
  47 CFR 95.1767 caps them at 5 W, which is exactly the radio's mid step.
* MURS transmits at 1 W, because 47 CFR 95.2767 caps it at 2 W and the
  radio's steps are 1, 5 and 10 W.
* FRS-only channels 8-14 are **receive only**. A GMRS licence does not
  authorize transmitting there.
* Everything else - public safety, park and forest, marine, aviation,
  weather, tribal, ferry - is receive only, programmed with CHIRP's
  ``Duplex=off`` so the radio physically cannot key up on it.

Power on receive-only channels is set high for consistency; it has no effect,
because those channels cannot transmit at all.
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

_OZETTE = ("OZ01",)

#: Amateur repeaters elsewhere in western Washington, drawn from the WWARA
#: coordination extract.  Analog only: a D-STAR, Fusion or DMR machine would
#: be a silent carrier on this radio.
_PUGET_ANALOG = ChannelSelector(
    favorite_keys=("PSHAM01",),
    department_pattern=r"Analog (2 Meter|70 Centimeter|1\.25 Meter)|Linked Analog",
)


def _oz(pattern: str = "", *, exclude: str = "", labels: str = "") -> ChannelSelector:
    return ChannelSelector(
        favorite_keys=_OZETTE,
        department_pattern=pattern,
        label_pattern=labels,
        exclude_label_pattern=exclude,
    )


H9_OZETTE = ChannelPlan(
    id="h9-ozette",
    radio_id="td-h9",
    label="TD-H9 - Lake Ozette",
    description=(
        "Analog listening and licensed talk-out for a trip based at Lake Ozette "
        "on the north-west Olympic coast, with Puget Sound amateur repeaters "
        "filling the remaining slots for the drive out and back."
    ),
    reserve_slots=14,
    blocks=(
        # --- Talk-out first: these are the channels you would actually use.
        #
        # GMRS is split by channel group rather than swept by frequency. The
        # main channels and the interstitials alternate in the band, so a
        # frequency sweep interleaves them as 15, 1, 16, 2 ... which is
        # unreadable on a radio that shows one channel at a time. Split into
        # groups and sorted by number, the memory list reads 1 to 22 in order.
        PlanBlock(
            label="GMRS 1-7",
            selectors=(_oz(pattern="GMRS and FRS", labels=r"^GMRS [1-7]$"),),
            tx_policy=TX_SIMPLEX,
            power="5.0W",
            sort=SORT_NATURAL,
            notes=(
                "FRS/GMRS shared interstitial channels, capped at 5 W by "
                "47 CFR 95.1767. The radio's mid step is exactly 5 W."
            ),
        ),
        PlanBlock(
            label="FRS 8-14",
            selectors=(_oz(pattern="GMRS and FRS", labels=r"^FRS \d"),),
            tx_policy=TX_NONE,
            power="10W",
            sort=SORT_NATURAL,
            notes=(
                "FRS-only interstitials. A GMRS licence does not authorize "
                "transmitting here, so these are receive only; the power "
                "setting has no effect."
            ),
        ),
        PlanBlock(
            label="GMRS 15-22",
            selectors=(_oz(pattern="GMRS and FRS", labels=r"^GMRS (1[5-9]|2[0-2])$"),),
            tx_policy=TX_SIMPLEX,
            power="10W",
            sort=SORT_NATURAL,
        ),
        PlanBlock(
            label="GMRS Repeaters",
            selectors=(_oz(pattern="GMRS and FRS", labels=r"^GMRS RPT"),),
            tx_policy=TX_REPEATER,
            power="10W",
            sort=SORT_NATURAL,
            notes=(
                "Standard GMRS repeater pairs. No repeater is publicly published "
                "in Clallam County, so no access tone is programmed."
            ),
        ),
        PlanBlock(
            label="MURS",
            selectors=(_oz(pattern="MURS"),),
            tx_policy=TX_SIMPLEX,
            power="1.0W",
            sort=SORT_NATURAL,
            notes=(
                "Capped at 2 W by 47 CFR 95.2767. The radio's 1 W step is the "
                "only setting under that limit."
            ),
        ),
        PlanBlock(
            label="Ham Calling",
            selectors=(_oz(pattern="Amateur", labels=r"Calling"),),
            tx_policy=TX_SIMPLEX,
            power="10W",
            sort=SORT_FREQ,
            notes="National calling channels, kept together and early in the list.",
        ),
        PlanBlock(
            label="Ham Simplex",
            selectors=(_oz(pattern="Amateur", labels=r"Simplex"),),
            tx_policy=TX_SIMPLEX,
            power="10W",
            sort=SORT_FREQ,
        ),
        PlanBlock(
            label="Ham West Peninsula",
            selectors=(_oz(pattern="Amateur", exclude=r"Simplex|Calling"),),
            tx_policy=TX_REPEATER,
            power="10W",
            sort=SORT_FREQ,
            notes="Clallam and Jefferson analog repeaters, inputs and tones as published.",
        ),
        # --- Then listening, safety-first.
        PlanBlock(
            label="NOAA Weather",
            selectors=(_oz(pattern="NOAA Weather"),),
            tx_policy=TX_NONE,
            power="10W",
            sort=SORT_FREQ,
        ),
        PlanBlock(
            label="SAR and Interop",
            selectors=(_oz(pattern="SAR and Interop"),),
            tx_policy=TX_NONE,
            power="10W",
            sort=SORT_FREQ,
        ),
        PlanBlock(
            label="Park and Forest",
            selectors=(_oz(pattern="Olympic NP and Forest"),),
            tx_policy=TX_NONE,
            power="10W",
            sort=SORT_FREQ,
        ),
        PlanBlock(
            label="DNR Olympic",
            selectors=(_oz(pattern="WA DNR Olympic Region"),),
            tx_policy=TX_NONE,
            power="10W",
            sort=SORT_FREQ,
        ),
        PlanBlock(
            label="Clallam County",
            selectors=(_oz(pattern="Clallam County"),),
            tx_policy=TX_NONE,
            power="10W",
            sort=SORT_FREQ,
        ),
        PlanBlock(
            label="Tribal",
            selectors=(_oz(pattern="Tribal"),),
            tx_policy=TX_NONE,
            power="10W",
            sort=SORT_FREQ,
        ),
        PlanBlock(
            label="Marine",
            selectors=(_oz(pattern="Marine and Vessel Traffic"),),
            tx_policy=TX_NONE,
            power="10W",
            sort=SORT_NATURAL,
            notes="Channel-number order, then the named vessel traffic sectors.",
        ),
        PlanBlock(
            label="Aviation",
            selectors=(_oz(pattern="Aviation"),),
            tx_policy=TX_NONE,
            power="10W",
            sort=SORT_FREQ,
        ),
        PlanBlock(
            label="Ferry and Utility",
            selectors=(_oz(pattern="Ferry Transport Utility"),),
            tx_policy=TX_NONE,
            power="10W",
            sort=SORT_FREQ,
        ),
        # --- Whatever is left goes to repeaters for the drive.
        PlanBlock(
            label="Ham Puget Sound",
            selectors=(_PUGET_ANALOG,),
            tx_policy=TX_REPEATER,
            power="10W",
            sort=SORT_FREQ,
            notes="Fills the remaining slots from the WWARA coordination extract.",
        ),
    ),
)
