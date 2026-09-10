"""Anytone AT-D890UV - everything within 60 miles of home, as a scanner
that can also transmit where the operator is licensed.

The radio organises memories into zones and scans explicit lists of at most
100 members, so this plan is written as banks (one zone each) in the order
the operator wants to scan them, plus composite scan groups. Amateur blocks
transmit (2 m and 70 cm only; the radio's US band mode has no 220 MHz);
every other block is receive-only and gets ``PTT Prohibit`` in the codeplug.

AM air-band rows resolve as ordinary channels here and the export routes
them into the radio's separate AM air list and zones; the FM broadcast block
likewise lands in the FM list. Both are locked out of every scan list, as is
NOAA weather, so the sweep only stops on traffic.

Data comes from the coordinator (WWARA, via the enriched catalog), the
regional DMR network layout (:mod:`wasds150.catalog.atd890_dmr`), the Seattle
ACS channel plan, the project's statewide public lists, and - when the user
has imported their own RadioReference export - the per-county ``RRC-*``
lists, selected by service type.
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
    ScanGroup,
)

#: 28523 NE 30th Ct, Redmond WA 98053 - the same point ``thd75-scan`` and
#: ``ftx1-scan`` are built around.
HOME = (47.6351, -121.9954)
RADIUS_MILES = 60.0
_WITHIN = (HOME[0], HOME[1], RADIUS_MILES)

#: RadioReference county lists inside the radius (built by
#: ``wasds150 sources update`` from the user's own export; absent lists
#: simply match nothing).
RR_NEARBY = ("RRC-KING", "RRC-SNOHOMISH", "RRC-PIERCE", "RRC-KITSAP", "RRC-ISLAND",
             "RRC-SKAGIT", "RRC-THURSTON", "RRC-MASON", "RRC-JEFFERSON", "RRC-KITTITAS")
RR_STATEWIDE = ("RRWA",)
#: Statewide RadioReference categories that are really somewhere else.
_FAR_AWAY = (
    r"^(?!.*(Spokane|Tri-Cit|Yakima|Wenatchee|Walla|Vancouver|Bellingham|Fairchild|Deer Park|"
    r"Felts|Hanford|Kalama|Longview|Gorge|Hoopfest|Davenport|Northtown|Lilac|Kettle|Colville|"
    r"Umatilla|Okanogan|Grant County|Whitman|Pullman|Moses|Ephrata|Pasco|Kennewick|Richland|"
    r"Eastern State|Inland|Snake Ri|Southeast Region|Northeast Region|Mid Columbia|Avista|"
    r"Chelan|Benton|Yakima|Spokesman|KXLY|KREM|Olympia Capital|Sacred Heart|Holy Family|"
    r"Deaconess|River Park|Spokane Valley|Clark |CRESA|Cowlitz|Klickitat|Skamania|Pacific|"
    r"Grays Harbor|Lewis|Wahkiakum|Asotin|Garfield|Columbia|Franklin|Adams|Lincoln|Douglas|"
    r"Ferry|Stevens|Pend Oreille|San Juan|Whatcom)).*"
)

# Uniden service types (see wasds150.hpe.schema.SERVICE_TYPES).
_PUBLIC_SAFETY = (1, 2, 3, 4, 6, 7, 8, 9, 11, 12, 14, 16, 22, 23, 24, 25, 29, 30)
_BUSINESS = (17, 21, 26, 31)
_AIRCRAFT = (15,)
_HAM = (13,)
_RAILROAD = (20,)


def _near(*keys: str, dept: str = "", labels: str = "", ranges=()) -> ChannelSelector:
    return ChannelSelector(
        favorite_keys=tuple(keys), department_pattern=dept, label_pattern=labels,
        freq_ranges=tuple(ranges), within_miles=_WITHIN,
    )


def _sel(*keys: str, dept: str = "", labels: str = "", exclude: str = "", ranges=(),
         modes=(), service_types=()) -> ChannelSelector:
    return ChannelSelector(
        favorite_keys=tuple(keys), department_pattern=dept, label_pattern=labels,
        exclude_label_pattern=exclude, freq_ranges=tuple(ranges), modes=tuple(modes),
        service_types=tuple(service_types),
    )


_VHF_UHF = ((136.0, 174.0), (400.0, 480.0))
_AIR = ((108.0, 137.0),)

ATD890_SCAN = ChannelPlan(
    id="atd890-scan",
    radio_id="at-d890uv",
    label="AT-D890UV - Scanner with Ham TX (60 mi)",
    description=(
        "Every conventional channel the AT-D890UV can hear within 60 miles of "
        "home, one zone per service in scan-priority order: coordinated 2 m / "
        "70 cm repeaters and the PNWDigital / SeattleDMR talkgroup layout "
        "(transmit enabled), simplex, Seattle ACS, air band (routed to the "
        "radio's AM list), SAR, wildfire, marine, rail, personal radio, "
        "business, conventional public safety and commercial DMR/NXDN "
        "(receive only). NOAA and FM broadcast are programmed but never scanned."
    ),
    reserve_slots=200,
    blocks=(
        PlanBlock(
            label="Ham 2m Repeaters",
            bank="Ham 2m",
            selectors=(
                _near("PSHAM01", dept=r"Analog 2 Meter|Linked Analog", ranges=((144.0, 148.0),)),
                _near("THD75WWARA", dept=r"2 Meter", ranges=((144.0, 148.0),)),
            ),
            tx_policy=TX_REPEATER, power="High", sort=SORT_FREQ, limit=160,
            notes="Every current WWARA analog 2 m machine within 60 miles; TX uses the published access tone.",
        ),
        PlanBlock(
            label="Ham 70cm Repeaters",
            bank="Ham 70cm",
            selectors=(
                _near("PSHAM01", dept=r"Analog 70 Centimeter|Linked Analog", ranges=((430.0, 450.0),)),
                _near("THD75WWARA", dept=r"70 Centimeter", ranges=((430.0, 450.0),)),
            ),
            tx_policy=TX_REPEATER, power="High", sort=SORT_FREQ, limit=160,
        ),
        PlanBlock(
            label="DMR Puget Sound Repeaters",
            bank="DMR Puget Sound",
            selectors=(_sel("DMRNET", dept=r"^Puget Sound$", ranges=_VHF_UHF),),
            tx_policy=TX_REPEATER, power="High", sort=SORT_FREQ, limit=480,
            notes=(
                "One channel per repeater and talkgroup as PNWDigital / SeattleDMR carry them. "
                "Colour code and timeslot come from the network's Config Builder file."
            ),
        ),
        PlanBlock(
            label="DMR Other Repeaters",
            bank="DMR Other",
            selectors=(
                _sel("DMRNET", dept=r"Western Washington", ranges=_VHF_UHF),
                _near("PSHAM01", dept=r"DMR", ranges=_VHF_UHF),
            ),
            tx_policy=TX_NONE, sort=SORT_FREQ, limit=400,
            notes="Machines outside the core area or without a published talkgroup layout: monitor only.",
        ),
        PlanBlock(
            label="Simplex",
            bank="Simplex",
            selectors=(
                _sel("HAM01", dept=r"2 meters|70 centimeters", labels=r"FM simplex calling"),
                _sel("PSHAM01", dept=r"Operator-Published", labels=r"Simplex"),
                _sel("ATD890LOCAL", dept=r"DMR Simplex"),
                _sel("SEAACS", dept=r"^ACS (VHF|UHF)$", labels=r"^[UV]2\d"),
            ),
            tx_policy=TX_SIMPLEX, power="High", sort=SORT_FREQ, limit=40,
        ),
        PlanBlock(
            label="Seattle ACS",
            bank="Seattle ACS",
            selectors=(_sel("SEAACS", dept=r"^ACS (VHF|UHF)$", exclude=r"^[UV]2\d|N ", ranges=_VHF_UHF),),
            tx_policy=TX_REPEATER, power="High", sort=SORT_NATURAL, limit=120,
            notes="Seattle Auxiliary Communications Service repeater plan with its access tones; duplicates of coordinated machines are dropped.",
        ),
        PlanBlock(
            label="Airband Civil",
            bank="Air Civil",
            selectors=(
                _sel("FL46", "FL48", ranges=_AIR),
                _sel(*RR_NEARBY, dept=r"Airport|Seaplane|Air to Air|Choppers|Airlines|Aircraft", ranges=_AIR),
                _sel(*RR_STATEWIDE, dept=r"Airports Air Traffic Control|Airports Boeing|Airports Airlines|Seaplanes|Air to Air|Paine Field|Airports Aircraft|Airports Airline Operations|Medevac", ranges=_AIR),
            ),
            tx_policy=TX_NONE, sort=SORT_FREQ, limit=200,
            notes="Written to the radio's AM air list and zone, scanned from the B receiver.",
        ),
        PlanBlock(
            label="Airband Military SAR",
            bank="Air Mil SAR",
            selectors=(
                _sel("FL49", "FL44", "FL55", ranges=_AIR),
                _sel(*RR_STATEWIDE, dept=r"JBLM|Joint Base|Fairchild|Civil Air Patrol", ranges=_AIR),
            ),
            tx_policy=TX_NONE, sort=SORT_FREQ, limit=56,
        ),
        PlanBlock(
            label="SAR and Interop",
            bank="SAR Interop",
            selectors=(
                _sel("FL01", "FL02", "FL03", ranges=_VHF_UHF),
                _sel(*RR_STATEWIDE, dept=r"Search and Rescue|Mutual Aid|Interoperability|CEMNET", ranges=_VHF_UHF),
            ),
            tx_policy=TX_NONE, sort=SORT_FREQ, limit=100,
        ),
        PlanBlock(
            label="Wildfire",
            bank="Wildfire",
            selectors=(
                _sel("FL06", "FL07", ranges=_VHF_UHF),
                _sel(*RR_STATEWIDE, dept=r"Natural Resources (Tactical|Aircraft|South Puget|Northwest|Olympic|Pacific Cascade)|Forest Service|Mt Baker|Olympic National|National Park", ranges=_VHF_UHF),
            ),
            tx_policy=TX_NONE, sort=SORT_FREQ, limit=100,
        ),
        PlanBlock(
            label="Marine",
            bank="Marine",
            selectors=(_sel("FL52", "FL53", "FL54", ranges=_VHF_UHF),),
            tx_policy=TX_NONE, sort=SORT_NATURAL, limit=100,
        ),
        PlanBlock(
            label="Rail",
            bank="Rail",
            selectors=(
                _sel("FL56", "FL58", ranges=_VHF_UHF),
                _sel(*RR_STATEWIDE, dept=r"Washington Railroads (Operations|Seattle|Scenic|Stampede|Bellingham|Sumas|Cherry Point|Capital|Tidelands|Other)", ranges=_VHF_UHF),
                _sel(*RR_NEARBY, service_types=_RAILROAD, ranges=_VHF_UHF),
            ),
            tx_policy=TX_NONE, sort=SORT_FREQ, limit=100,
        ),
        PlanBlock(
            label="GMRS FRS MURS",
            bank="GMRS FRS MURS",
            selectors=(
                _sel("FL65", ranges=_VHF_UHF),
                _sel("FL66", labels=r"MURS", ranges=_VHF_UHF),
                _sel("RRC-KING", dept=r"GMRS", ranges=_VHF_UHF),
            ),
            tx_policy=TX_NONE, sort=SORT_NATURAL, limit=60,
            notes="Receive only: GMRS needs its own licence and the radio is not certified for it.",
        ),
        PlanBlock(
            label="Business and Events",
            bank="Business",
            selectors=(
                _sel("FL68", "FL72", "FL73", "FL74a", "FL69", ranges=_VHF_UHF),
                _sel(*RR_NEARBY, service_types=_BUSINESS, ranges=_VHF_UHF),
                _sel(*RR_STATEWIDE, dept=_FAR_AWAY, service_types=_BUSINESS, ranges=_VHF_UHF),
            ),
            tx_policy=TX_NONE, sort=SORT_FREQ, limit=400,
        ),
        PlanBlock(
            label="Public Safety Conventional",
            bank="Pub Safety",
            selectors=(
                _sel("FL13", "FL14", "FL16", "FL71", ranges=_VHF_UHF),
                _sel(*RR_NEARBY, service_types=_PUBLIC_SAFETY, ranges=_VHF_UHF),
                _sel(*RR_STATEWIDE, dept=_FAR_AWAY, service_types=_PUBLIC_SAFETY, ranges=_VHF_UHF),
            ),
            tx_policy=TX_NONE, sort=SORT_FREQ, limit=400,
            notes="Everything conventional; the trunked P25 systems the county actually dispatches on are dropped (the radio cannot decode P25).",
        ),
        PlanBlock(
            label="Commercial Digital",
            bank="Comm Digital",
            selectors=(
                _sel("FL70a", "FL70b", ranges=_VHF_UHF),
                _sel(*RR_NEARBY, modes=("DMR", "NXDN"), exclude=r"DSTAR", ranges=_VHF_UHF),
            ),
            tx_policy=TX_NONE, sort=SORT_FREQ, limit=100,
            notes="Conventional DMR and NXDN users; NXDN rows are silent until the radio is switched to the NXDN protocol.",
        ),
        PlanBlock(
            label="ACS Packet and Data",
            bank="ACS Data",
            selectors=(_sel("SEAACS", dept=r"Data", ranges=_VHF_UHF),),
            tx_policy=TX_NONE, sort=SORT_FREQ, limit=60, skip_scan=True,
            notes="APRS, Winlink and packet frequencies: programmed for reference, never scanned.",
        ),
        PlanBlock(
            label="NOAA Weather",
            bank="NOAA WX",
            selectors=(_sel("FL75", ranges=_VHF_UHF),),
            tx_policy=TX_NONE, sort=SORT_FREQ, limit=10, skip_scan=True,
            notes="Continuous carriers; select the zone by hand.",
        ),
        PlanBlock(
            label="FM Broadcast",
            bank="FM Bcast",
            selectors=(_sel("THD75BC", dept=r"FM Broadcast"),),
            tx_policy=TX_NONE, sort=SORT_FREQ, limit=100, skip_scan=True,
            notes="Written to the radio's FM broadcast list, not the channel table.",
        ),
    ),
    scan_groups=(
        ScanGroup("Ham All", ("Ham 2m Repeaters", "Ham 70cm Repeaters", "DMR Puget Sound Repeaters", "Simplex", "Seattle ACS")),
        ScanGroup("Ham Analog", ("Ham 2m Repeaters", "Ham 70cm Repeaters", "Simplex", "Seattle ACS")),
        ScanGroup("Ham DMR", ("DMR Puget Sound Repeaters", "DMR Other Repeaters")),
        ScanGroup("Pub Svc", ("SAR and Interop", "Wildfire", "Public Safety Conventional", "Commercial Digital")),
        ScanGroup("Marine Rail", ("Marine", "Rail")),
        ScanGroup("Personal Biz", ("GMRS FRS MURS", "Business and Events")),
        ScanGroup("Everything", (
            "Ham 2m Repeaters", "Ham 70cm Repeaters", "DMR Puget Sound Repeaters", "DMR Other Repeaters",
            "Simplex", "Seattle ACS", "SAR and Interop", "Wildfire", "Marine", "Rail", "GMRS FRS MURS",
            "Business and Events", "Public Safety Conventional", "Commercial Digital",
        )),
    ),
)
