"""Yaesu FTX-1 channel plan for Washington state.

The FTX-1 holds 999 memories, roughly seven times what fits in a handheld, so
this plan is inclusive where the TD-H9 plan has to be ruthless.  The ordering
goal is different too: the radio has a keypad and an alpha tag display, so
blocks are grouped by service in the order an operator reaches for them
rather than by emergency priority.

Every block carries an explicit ``limit``.  That is not tidiness - the
catalog holds far more than 999 receivable channels once local enrichment is
applied, and blocks are filled in declaration order, so without ceilings the
amateur repeater blocks alone would consume the whole radio and every block
after them would silently resolve to nothing.  The limits are a budget: they
sum to less than the available capacity, so each service is guaranteed its
share and the tail of the plan still gets programmed.

Transmit policy follows the radio's licence class rather than the plan's
convenience.  The FTX-1 transmits **only** on amateur allocations - 160 m
through 10 m, 6 m, 2 m and 70 cm - so amateur blocks are transmit-enabled and
everything else is receive only.  That is not a stylistic choice: the
resolver checks each channel against the profile's transmit bands and refuses
to mark a memory transmit-capable outside them.  GMRS, FRS, MURS, marine,
aviation and public safety are all ``TX_NONE`` here even though some are
transmit services for other radios, because this radio cannot work them.

Receive coverage has one hard gap worth knowing: the FTX-1 receives
30 kHz-174 MHz and 400-470 MHz, with nothing in between.  The 1.25 m band
(222-225 MHz) is therefore impossible on this radio, and any 220 MHz channel
in the catalog is dropped during resolution with that reason stated.
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

#: Analog amateur departments in the WWARA-derived Puget Sound list.  D-STAR,
#: Fusion and DMR machines are excluded: a DMR or D-STAR repeater would be an
#: unreadable carrier on this radio.
_PUGET_ANALOG = ChannelSelector(
    favorite_keys=("PSHAM01",),
    department_pattern=r"Analog (2 Meter|6 Meter|70 Centimeter)|Operator-Published",
)


def _sel(
    *keys: str,
    dept: str = "",
    labels: str = "",
    exclude: str = "",
) -> ChannelSelector:
    return ChannelSelector(
        favorite_keys=tuple(keys),
        department_pattern=dept,
        label_pattern=labels,
        exclude_label_pattern=exclude,
    )


FTX1_WA = ChannelPlan(
    id="ftx1-wa",
    radio_id="ftx1",
    label="FTX-1 - Washington",
    description=(
        "Statewide Washington loadout for the Yaesu FTX-1: amateur HF calling "
        "frequencies and VHF/UHF repeaters with transmit enabled, plus marine, "
        "aviation, weather, wildfire and public-safety listening."
    ),
    reserve_slots=20,
    blocks=(
        # --- Immediate-use listening ------------------------------------
        PlanBlock(
            label="NOAA Weather",
            selectors=(
                _sel("OZ01", dept="NOAA Weather"),
                _sel("FL75"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=18,
            notes="The seven NWR channels plus the statewide transmitter list.",
        ),
        PlanBlock(
            label="GMRS and FRS",
            selectors=(
                _sel("OZ01", dept="GMRS and FRS"),
                _sel("FL65"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_NATURAL,
            limit=30,
            notes=(
                "Receive only. The FTX-1 does not transmit in the 462/467 MHz "
                "GMRS allocation, so these are monitor channels on this radio "
                "regardless of what licence the operator holds."
            ),
        ),
        PlanBlock(
            label="MURS and CB",
            selectors=(
                _sel("OZ01", dept="MURS"),
                _sel("FL66"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_NATURAL,
            limit=45,
            notes="Receive only; outside this radio's transmit allocations.",
        ),
        # --- Amateur: the part this radio is actually for ---------------
        PlanBlock(
            label="HF Calling and Activity",
            selectors=(_sel("HAM01", dept=r"calling and activity"),),
            tx_policy=TX_SIMPLEX,
            sort=SORT_FREQ,
            limit=88,
            notes=(
                "Calling and activity frequencies from the ARRL band plan, "
                "160 m through 70 cm. Each carries its General-class privilege "
                "summary in the comment. Verify your own privileges before "
                "transmitting; the band plan is convention, not authorization."
            ),
        ),
        PlanBlock(
            label="Time Standards",
            selectors=(_sel("HAM01", dept="Time and Frequency Standards"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=8,
            notes="WWV, WWVH and CHU, for checking calibration and propagation.",
        ),
        PlanBlock(
            label="Amateur 6 Meter",
            selectors=(_sel("FTX01", dept="Amateur 6 Meter"),),
            tx_policy=TX_REPEATER,
            sort=SORT_FREQ,
            limit=20,
        ),
        PlanBlock(
            label="Amateur 2m Repeaters",
            selectors=(_sel("FTX01", dept="Amateur 2 Meter Repeaters"),),
            tx_policy=TX_REPEATER,
            sort=SORT_FREQ,
            limit=135,
            notes=(
                "Statewide 2 m coordination, including eastern Washington "
                "machines the WWARA extract does not cover."
            ),
        ),
        PlanBlock(
            label="Amateur 70cm Repeaters",
            selectors=(_sel("FTX01", dept="Amateur 70 Centimeter Repeaters"),),
            tx_policy=TX_REPEATER,
            sort=SORT_FREQ,
            limit=225,
            notes="The largest block in the plan; statewide 70 cm coordination.",
        ),
        PlanBlock(
            label="Amateur West Peninsula",
            selectors=(_sel("OZ01", dept="Amateur West Peninsula"),),
            tx_policy=TX_REPEATER,
            sort=SORT_FREQ,
            limit=20,
        ),
        PlanBlock(
            label="Amateur Puget Sound",
            selectors=(_PUGET_ANALOG,),
            tx_policy=TX_REPEATER,
            sort=SORT_FREQ,
            limit=110,
            notes=(
                "WWARA-coordinated analog machines around Puget Sound. Digital "
                "departments are excluded: a DMR or D-STAR repeater would be "
                "an unreadable carrier on this radio."
            ),
        ),
        PlanBlock(
            label="ARES RACES and Winlink",
            selectors=(
                _sel(
                    "FL62",
                    labels=r"Winlink|ARES/RACES|Eastside/King|national calling|UHF calling",
                ),
            ),
            tx_policy=TX_REPEATER,
            sort=SORT_FREQ,
            limit=14,
            notes=(
                "Emergency-service amateur nets and Winlink gateways, matched "
                "by label. A bare favourite-key selector would instead pull "
                "the enriched WWARA dump this list also carries, which sorts "
                "lower by frequency and would crowd out every curated entry."
            ),
        ),
        PlanBlock(
            label="Data and Packet",
            selectors=(
                ChannelSelector(
                    favorite_keys=("FL62", "FL51"),
                    label_pattern=r"Winlink|APRS|packet|SSTV",
                    include_avoided=True,
                ),
            ),
            tx_policy=TX_REPEATER,
            sort=SORT_FREQ,
            limit=8,
            skip_scan=True,
            notes=(
                "Winlink gateways, APRS and SSTV. These are flagged 'avoid' in "
                "the catalog because a scanner should not stop on a continuous "
                "data burst, but a transceiver still wants them as memories - "
                "so they are programmed here with include_avoided and marked "
                "skip_scan so the radio tunes them on demand without the scan "
                "sweep parking on them."
            ),
        ),
        PlanBlock(
            label="Linked and Intertie",
            selectors=(
                _sel("FL60", labels=r"Seattle|Olympia|Chelan|Chinook"),
                _sel("FL61", labels=r"WIN|Chinook|Evergreen"),
            ),
            tx_policy=TX_REPEATER,
            sort=SORT_FREQ,
            limit=12,
            notes="Evergreen Intertie and WIN linked-system entry points.",
        ),
        PlanBlock(
            label="Amateur Satellites",
            selectors=(
                _sel(
                    "FL51",
                    labels=r"SSTV|APRS|cross-band|SO-\d|AO-\d|TEVEL|ISS|ARISS",
                ),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=12,
            notes=(
                "Satellite and ISS downlinks, plus the APRS downlink. Receive "
                "only here: working a satellite needs full duplex and Doppler "
                "correction that a fixed memory pair cannot express."
            ),
        ),
        # --- Marine and aviation ----------------------------------------
        PlanBlock(
            label="Marine VHF",
            selectors=(
                _sel("FTX01", dept="Marine VHF"),
                _sel("OZ01", dept="Marine and Vessel Traffic"),
                _sel("FL52"),
                _sel("FL54"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_NATURAL,
            limit=70,
        ),
        PlanBlock(
            label="Ferries and VTS",
            selectors=(
                _sel("FL53"),
                _sel("OZ01", dept="Ferry Transport Utility"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=12,
        ),
        PlanBlock(
            label="Aviation",
            selectors=(
                _sel("OZ01", dept="Aviation"),
                _sel("FL46"),
                _sel("FL47"),
                _sel("FL48"),
                _sel("FL49"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=45,
            notes="AM airband. The FTX-1 receives it; it cannot transmit there.",
        ),
        PlanBlock(
            label="Medevac and Rescue Air",
            selectors=(
                _sel("FL44"),
                _sel("FL55"),
                _sel("FL71"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=18,
        ),
        # --- Public safety and land management --------------------------
        PlanBlock(
            label="SAR and Interop",
            selectors=(
                _sel("OZ01", dept="SAR and Interop"),
                _sel("FL01"),
                _sel("FL02"),
                _sel("FL03"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=28,
        ),
        PlanBlock(
            label="Wildfire and DNR",
            selectors=(
                _sel("OZ01", dept="WA DNR Olympic Region"),
                _sel("FL06"),
                _sel("FL07"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=36,
        ),
        PlanBlock(
            label="Parks and Forests",
            selectors=(
                _sel("OZ01", dept="Olympic NP and Forest"),
                _sel("FL32"),
                _sel("FL33"),
                _sel("FL34"),
                _sel("FL35"),
                _sel("FL36"),
                _sel("FL37"),
                _sel("FL38"),
                _sel("FL39"),
                _sel("FL40"),
                _sel("FL41"),
                _sel("FL42"),
                _sel("FL43"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=45,
        ),
        PlanBlock(
            label="Clallam and Tribal",
            selectors=(
                _sel("OZ01", dept="Clallam County"),
                _sel("OZ01", dept="Tribal Neah Bay and La Push"),
                _sel("FL18"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=18,
        ),
        PlanBlock(
            label="Military Ground and Range",
            selectors=(_sel("FL59"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=8,
            notes="Range operations and flight following, receive only.",
        ),
        PlanBlock(
            label="Rail",
            selectors=(_sel("FL56"), _sel("FL57")),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=13,
        ),
        PlanBlock(
            label="Business and Itinerant",
            selectors=(
                _sel("FTX01", dept="Business and Itinerant UHF"),
                _sel("FL68"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=15,
        ),
        PlanBlock(
            label="Events and Media",
            selectors=(
                _sel("FL73"),
                _sel("FL74a"),
                _sel("FL74b"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=10,
        ),
        PlanBlock(
            label="Upper Lena Essentials",
            selectors=(_sel("UL00"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=12,
        ),
        PlanBlock(
            label="Regional Public Safety",
            selectors=(
                _sel("FL13"),
                _sel("FL14"),
                _sel("FL16"),
                _sel("FL17"),
                _sel("FL19"),
                _sel("FL22"),
                _sel("FL23"),
                _sel("FL24"),
                _sel("FL26"),
                _sel("FL27"),
                _sel("FL28"),
                _sel("FL29"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=45,
        ),
    ),
)
