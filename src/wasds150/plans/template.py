"""One channel-plan template for every memory-list radio in the fleet.

The hand-written plans each chose their own home point, radius, block names
and favorite keys, so a database refresh reached some radios and not others,
and a new list (a RadioReference county, the DMR network layout) reached none
until someone edited several files. This template writes the service
taxonomy once. :func:`build_fleet_plan` asks a radio's capability profile
which blocks it can use at all, and :class:`RadioKnobs` carries the few
choices that really are per radio: slot ceilings, whether HF or DMR is
wanted, which power labels its exporter understands.

How blocks select, and why:

* **Repeaters, DMR and the catch-all are distance-filtered** on each
  station's own position, around one home point shared by every radio.
* **Band-driven blocks** (marine, NOAA, GMRS/FRS/MURS, broadcast) select by
  frequency, because there the frequency *is* the service and the catalog's
  service types are heuristic (marine and weather are "Other").
* **List-driven blocks** name the statewide lists that carry a service, plus
  the user's RadioReference lists: county lists (``RRC-*``) by service type,
  passing the radius through their county geo-fence because RadioReference
  publishes no per-channel positions, and the statewide ``RRWA`` list minus
  the departments that are really somewhere else.
* **Transmit** is offered only where the operator is licensed - amateur
  blocks within ``license_class`` privileges, GMRS under the operator's GMRS
  licence, MURS licence-free - and only where the radio's hardware
  transmits. Every other block is receive only.

Capacity is budgeted, not discovered: each radio's knobs cap every block so
the ceilings add up to no more than the radio holds, and a later block (NOAA,
the catch-all) can never be starved by a refresh that grows an earlier one.
Every block keeps its nearest stations first. Once each block has its budget,
the slots nobody used go to the next-nearest stations of the ``fill`` blocks,
statewide if need be; those beyond the radius are programmed but locked out
of the scan (``ChannelPlan.fill_to_capacity``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Tuple

from wasds150.models.plan import (
    GEO_DEPARTMENT,
    GEO_EITHER,
    SORT_FREQ,
    SORT_NATURAL,
    SORT_NEAREST,
    SORT_TIER_DISTANCE,
    TX_AUTO,
    TX_NONE,
    TX_REPEATER,
    TX_SIMPLEX,
    ChannelPlan,
    ChannelSelector,
    PlanBlock,
    ScanGroup,
)
from wasds150 import station
from wasds150.radios.profile import RadioProfile
from wasds150.radios.registry import get_profile

#: 28523 NE 30th Ct, Redmond WA 98053 - the point ``thd75-scan``,
#: ``ftx1-scan`` and ``atd890-scan`` are already built around.
HOME = (47.6351, -121.9954)
RADIUS_MILES = 60.0

#: Radios the template builds a ``<radio>-fleet`` plan for. The SDS150 is not
#: here: it installs Favorites Lists, not a flat memory plan.
FLEET_PLAN_RADIOS = ("td-h9", "ftx1", "th-d75", "at-d890uv", "id-52a")

TXK_NONE = "none"
TXK_HAM_REPEATER = "ham-repeater"
TXK_HAM_SIMPLEX = "ham-simplex"
TXK_GMRS = "gmrs"
TXK_MURS = "murs"
TX_KINDS = (TXK_NONE, TXK_HAM_REPEATER, TXK_HAM_SIMPLEX, TXK_GMRS, TXK_MURS)

POWER_HIGH = "high"
POWER_MID = "mid"
POWER_LOW = "low"

#: Representative frequencies for "can this radio transmit on GMRS / MURS".
_GMRS_PROBE = (462.600,)
_FRS_PROBE = (467.6375,)
_MURS_PROBE = (151.880,)

# Uniden service types (see wasds150.hpe.schema.SERVICE_TYPES).
PUBLIC_SAFETY = (1, 2, 3, 4, 6, 7, 8, 9, 11, 12, 14, 16, 22, 23, 24, 25, 29, 30)
BUSINESS = (17, 21, 26, 31)
AIRCRAFT = (15,)
RAILROAD = (20,)
INTEROP = (11, 29)

AIR = ((108.0, 137.0),)
MIL_AIR = ((108.0, 137.0), (225.0, 400.0))
#: Military VHF operations channels the FAA lists at towers (Gray AAF OPS
#: 138.6), received AM.
MIL_VHF = ((137.0, 144.0),)
#: Everything outside the amateur bands (6 m, 2 m, 1.25 m, 70 cm, 33 cm,
#: 23 cm): a repeater a curated list happens to carry belongs to the ham
#: groups, not to wildfire or business.
NON_HAM = ((25.0, 50.0), (54.0, 144.0), (148.0, 222.0), (225.0, 420.0), (450.0, 902.0), (928.0, 1240.0), (1300.0, 3000.0))
#: Broadcasts that never stop (ATIS, ASOS/AWOS weather, PMSV METRO): worth
#: programming, but a scan that lands on one would stay there.
CONTINUOUS = r"\b(ATIS|D-ATIS|ASOS|AWOS|METRO|VOLMET)\b"
#: Marine VHF from channel 5A up, plus the coast-station half of the duplex
#: channels. Starts above 156.2475 because 156.0-156.24 MHz is land-mobile
#: public safety in parts of Washington; AIS is excluded by label.
MARINE = ((156.2475, 157.4250), (161.7750, 161.9625))

# The personal-radio channel plans live with the service rules that use them.
from wasds150.radios.services import FRS_ONLY, GMRS_INTERSTITIAL, GMRS_MAIN, MURS  # noqa: E402
NOAA = (162.400, 162.425, 162.450, 162.475, 162.500, 162.525, 162.550)

#: Statewide RadioReference departments that are really somewhere else.
FAR_AWAY = (
    r"Spokane|Tri-Cit|Yakima|Wenatchee|Walla|Vancouver|Bellingham|Fairchild|Deer Park|"
    r"Felts|Hanford|Kalama|Longview|Gorge|Hoopfest|Davenport|Northtown|Lilac|Kettle|Colville|"
    r"Umatilla|Okanogan|Grant County|Whitman|Pullman|Moses|Ephrata|Pasco|Kennewick|Richland|"
    r"Eastern State|Inland|Snake Ri|Southeast Region|Northeast Region|Mid Columbia|Avista|"
    r"Chelan|Benton|Spokesman|KXLY|KREM|Olympia Capital|Sacred Heart|Holy Family|"
    r"Deaconess|River Park|Spokane Valley|Clark |CRESA|Cowlitz|Klickitat|Skamania|Pacific|"
    r"Grays Harbor|Lewis|Wahkiakum|Asotin|Garfield|Columbia|Franklin|Adams|Lincoln|Douglas|"
    r"Ferry|Stevens|Pend Oreille|San Juan|Whatcom"
)

GROUP_NEAR_ME = "Near Me"
GROUP_HAM_ALL = "Ham All"
GROUP_HAM_ANALOG = "Ham Analog"
GROUP_HAM_DMR = "Ham DMR"
GROUP_PUB_SVC = "Public Svc"
GROUP_MARINE_RAIL = "Rail & Marine"
GROUP_PERSONAL = "Personal"
GROUP_EVERYTHING = "Everything"
#: The one list worth leaving running: every local amateur service, inside a
#: single scan list so it never splits into chunks the radio cannot scan
#: together. Quotas are nearest-first, because every block is.
#:
#: Amateur only, by choice: the repeaters carrying nets, the nearest analog
#: machines on every band the radio has, its digital voice mode, simplex
#: calling and the ACS plan. Public safety, marine, rail and the personal
#: radio services have their own groups; a list meant to be left running all
#: day is more useful when everything on it is a conversation you could join.
#: Never included anywhere: NOAA and the broadcast bands (continuous
#: carriers), packet and data, HF (a different radio mode) and the air blocks
#: (a separate AM receiver on the Anytone, which cannot share a VHF/UHF list).
#:
#: A radio contributes nothing for a block it does not have, so these do not
#: total the same everywhere and are not meant to: 100 on the AT-D890UV,
#: which is its scan list's ceiling, and less on radios that lack a band or a
#: digital mode. Whichever digital voice a radio speaks is in here - DMR,
#: D-STAR or none - because on the radio that has it, it is where the local
#: amateur traffic is.
#:
#: The quotas are deliberately modest against what each block holds - 14 of
#: 96 70 cm repeaters, say. Blocks are nearest-first, so raising a quota adds
#: machines that are progressively farther off and quieter, while every
#: addition lengthens the sweep for the channels already on it. The ceiling
#: that matters is not the radio's, it is how long a pass can take and still
#: catch a call.
NEAR_ME_QUOTAS = (
    ("Nets", 24),
    ("Ham 6m Repeaters", 4),
    ("Ham 2m Repeaters", 14),
    ("Ham 1.25m Repeaters", 4),
    ("Ham 70cm Repeaters", 14),
    ("D-STAR Repeaters", 10),
    ("DMR Core", 20),
    ("DMR Local", 10),
    ("Simplex Calling", 6),
    ("Seattle ACS", 8),
)

#: Repeaters Near Me always holds, ahead of the quotas' own choice:
#: (output MHz, call in the memory's name). The operator's daily machines.
NEAR_ME_PINNED = (
    (443.050, "KC7BAE"),  # East Tiger Mountain
    (146.960, "WW7PSR"),  # Puget Sound Repeater Group, Seattle: the PSRG nets
)
#: How far from home a handheld reaches a repeater. A quota takes stations
#: within it, nearest first, then those whose distance is unknown (simplex
#: frequencies), and never one known to be farther unless it is pinned.
NEAR_ME_REACH_MILES = 35.0

SCAN_GROUP_ORDER = (
    GROUP_NEAR_ME,
    GROUP_HAM_ALL,
    GROUP_HAM_ANALOG,
    GROUP_HAM_DMR,
    GROUP_PUB_SVC,
    GROUP_MARINE_RAIL,
    GROUP_PERSONAL,
)


# ------------------------------------------------------------------ knobs --
@dataclass(frozen=True)
class RadioKnobs:
    home: Tuple[float, float] = HOME
    radius_miles: float = RADIUS_MILES
    reserve_slots: int = 0
    #: Amateur licence class (see :mod:`wasds150.radios.bandplan`); empty
    #: means no amateur licence and no amateur transmit.
    license_class: str = station.LICENSE_CLASS
    callsign: str = station.CALLSIGN
    gmrs_licensed: bool = True
    gmrs_call: str = station.GMRS_CALL
    murs_tx: bool = True
    include_hf: bool = True
    include_dmr: bool = True
    include_dstar: bool = True
    include_air: bool = True
    include_broadcast: bool = True
    include_trip_packs: bool = True
    catch_all: bool = True
    bank_names: bool = True
    #: Per-block slot ceilings overriding the template's defaults, by block
    #: id; ``0`` leaves the block out.
    limits: Mapping[str, int] = field(default_factory=dict, hash=False)
    #: Power labels the radio's exporter understands, as (high, mid, low).
    power: Tuple[str, str, str] = ("High", "Mid", "Low")
    #: Give slots the budget leaves empty to the next-nearest stations,
    #: statewide if need be (programmed, but not scanned beyond the radius).
    fill_to_capacity: bool = True
    #: Ceilings the fill pass may not push a block past, by block id.
    fill_limits: Mapping[str, int] = field(default_factory=dict, hash=False)
    #: The radio can program AM outside the civil air band (138.6 MHz).
    am_outside_airband: bool = True

    @property
    def within(self) -> Tuple[float, float, float]:
        return (self.home[0], self.home[1], self.radius_miles)

    def limit_for(self, spec: "ServiceBlockSpec") -> int:
        return int(self.limits.get(spec.id, spec.limit))


Requirement = Callable[[RadioProfile, RadioKnobs], bool]


def _always(profile: RadioProfile, knobs: RadioKnobs) -> bool:
    return True


def _receives(*freqs: float) -> Requirement:
    return lambda profile, knobs: any(profile.can_receive(f) for f in freqs)


def _demodulates(*modes: str) -> Requirement:
    return lambda profile, knobs: any(m.upper() in profile.modes for m in modes)


def _knob(name: str) -> Requirement:
    return lambda profile, knobs: bool(getattr(knobs, name))


def _all(*requirements: Requirement) -> Requirement:
    return lambda profile, knobs: all(r(profile, knobs) for r in requirements)


@dataclass(frozen=True)
class ServiceBlockSpec:
    id: str
    label: str
    #: Zone/bank/group name on radios that have them; 16 characters at most.
    bank: str
    selectors: Callable[[RadioKnobs], Tuple[ChannelSelector, ...]]
    tx: str = TXK_NONE
    sort: str = SORT_FREQ
    #: Default slot ceiling; a radio's :class:`RadioKnobs` may override it.
    limit: int = 100
    skip_scan: bool = False
    power: str = POWER_HIGH
    #: The block filters stations by their own distance from home.
    radius: bool = False
    requires: Requirement = _always
    #: Transmit is offered only when the radio can transmit on one of these.
    tx_probe: Tuple[float, ...] = ()
    groups: Tuple[str, ...] = ()
    notes: str = ""
    #: The block may take spare slots, nearest first, beyond its limit.
    fill: bool = False
    #: Channel labels programmed but locked out of the scan.
    skip_labels: str = ""

    def __post_init__(self) -> None:
        if self.tx not in TX_KINDS:
            raise ValueError(f"block {self.id!r}: tx must be one of {TX_KINDS}")
        if self.power not in (POWER_HIGH, POWER_MID, POWER_LOW):
            raise ValueError(f"block {self.id!r}: unknown power {self.power!r}")


# -------------------------------------------------------------- selectors --
def _keys(
    *keys: str,
    dept: str = "",
    labels: str = "",
    exclude: str = "",
    ranges: Iterable[Tuple[float, float]] = (),
    modes: Iterable[str] = (),
    service_types: Iterable[int] = (),
    dmr_tiers: Iterable[int] = (),
    include_avoided: bool = False,
    anywhere: bool = False,
) -> ChannelSelector:
    return ChannelSelector(
        favorite_keys=tuple(keys),
        department_pattern=dept,
        label_pattern=labels,
        exclude_label_pattern=exclude,
        freq_ranges=tuple(ranges),
        modes=tuple(modes),
        service_types=tuple(service_types),
        dmr_tiers=tuple(dmr_tiers),
        include_avoided=include_avoided,
        anywhere=anywhere,
    )


def _near(
    knobs: RadioKnobs,
    *keys: str,
    dept: str = "",
    ranges: Iterable[Tuple[float, float]] = (),
    dmr_tiers: Iterable[int] = (),
) -> ChannelSelector:
    return ChannelSelector(
        favorite_keys=tuple(keys),
        department_pattern=dept,
        freq_ranges=tuple(ranges),
        dmr_tiers=tuple(dmr_tiers),
        within_miles=knobs.within,
    )


def _rr_county(
    knobs: RadioKnobs,
    *,
    service_types: Iterable[int] = (),
    dept: str = "",
    modes: Iterable[str] = (),
    ranges: Iterable[Tuple[float, float]] = (),
    exclude: str = "",
) -> ChannelSelector:
    """Every RadioReference county list whose county fence reaches the radius."""
    return ChannelSelector(
        favorite_key_pattern=r"^RRC-",
        department_pattern=dept,
        exclude_label_pattern=exclude,
        freq_ranges=tuple(ranges),
        modes=tuple(modes),
        service_types=tuple(service_types),
        within_miles=knobs.within,
        geo_fallback=GEO_DEPARTMENT,
    )


def _rr_state(
    *,
    dept: str = "",
    service_types: Iterable[int] = (),
    ranges: Iterable[Tuple[float, float]] = (),
    anywhere: bool = False,
) -> ChannelSelector:
    """The statewide RadioReference list, minus the far side of the state."""
    return ChannelSelector(
        favorite_keys=("RRWA",),
        department_pattern=dept,
        exclude_department_pattern=FAR_AWAY,
        freq_ranges=tuple(ranges),
        service_types=tuple(service_types),
        anywhere=anywhere,
    )


def _exact(freqs: Iterable[float], tolerance: float = 0.0006) -> Tuple[Tuple[float, float], ...]:
    """Frequency windows narrow enough to separate 12.5 kHz neighbours."""
    return tuple((f - tolerance, f + tolerance) for f in freqs)


_VHF_UHF_HAM = ((144.0, 148.0), (420.0, 450.0))
_DMR_CORE = (0, 1)
_DMR_WIDE = (2, 3)


def _dmr(knobs: RadioKnobs, tiers: Tuple[int, ...]) -> Tuple[ChannelSelector, ...]:
    return (
        # The core network rows, located or not: SeattleDMR publishes no
        # positions, and these are the machines the operator works daily.
        _keys("DMRNET", dept=r"^Puget Sound$", dmr_tiers=tiers),
        _near(knobs, "DMRNET", dmr_tiers=tiers),
        # BrandMeister machines publish their owners' positions.
        _near(knobs, "BMNET", dmr_tiers=tiers),
    )


_BLOCKS: Tuple[ServiceBlockSpec, ...] = (
    # -- amateur, transmit where licensed ------------------------------------
    ServiceBlockSpec(
        "ham-6m", "Ham 6m Repeaters", "Ham 6m",
        lambda k: (_near(k, "PSHAM01", "PSHAM02", dept=r"Analog 6 Meter|Linked Analog", ranges=((50.0, 54.0),)),),
        tx=TXK_HAM_REPEATER, sort=SORT_NEAREST, limit=40, radius=True, fill=True, requires=_receives(52.0), tx_probe=(52.0,),
        groups=(GROUP_HAM_ALL, GROUP_HAM_ANALOG),
    ),
    ServiceBlockSpec(
        "ham-2m", "Ham 2m Repeaters", "Ham 2m",
        lambda k: (
            _near(k, "PSHAM01", dept=r"Analog 2 Meter|Linked Analog", ranges=((144.0, 148.0),)),
            _near(k, "THD75WWARA", dept=r"2 Meter", ranges=((144.0, 148.0),)),
        ),
        tx=TXK_HAM_REPEATER, sort=SORT_NEAREST, limit=160, radius=True, fill=True, requires=_receives(146.0),
        tx_probe=(146.0,), groups=(GROUP_HAM_ALL, GROUP_HAM_ANALOG),
        notes=(
            "Every current WWARA analog 2 m machine in range, nearest first so a small radio keeps "
            "the closest; transmit uses the published access tone."
        ),
    ),
    ServiceBlockSpec(
        "ham-125", "Ham 1.25m Repeaters", "Ham 1.25m",
        lambda k: (
            _near(k, "PSHAM01", "PSHAM02", dept=r"Analog 1\.25 Meter|Linked Analog", ranges=((222.0, 225.0),)),
            _near(k, "THD75WWARA", dept=r"1\.25 Meter", ranges=((222.0, 225.0),)),
        ),
        tx=TXK_HAM_REPEATER, sort=SORT_NEAREST, limit=30, radius=True, fill=True, requires=_receives(223.5),
        tx_probe=(223.5,), groups=(GROUP_HAM_ALL, GROUP_HAM_ANALOG),
    ),
    ServiceBlockSpec(
        "ham-70cm", "Ham 70cm Repeaters", "Ham 70cm",
        lambda k: (
            _near(k, "PSHAM01", dept=r"Analog 70 Centimeter|Linked Analog", ranges=((420.0, 450.0),)),
            _near(k, "THD75WWARA", dept=r"70 Centimeter", ranges=((420.0, 450.0),)),
            _keys("THD75USER"),
        ),
        tx=TXK_HAM_REPEATER, sort=SORT_NEAREST, limit=160, radius=True, fill=True, requires=_receives(440.0),
        tx_probe=(440.0,), groups=(GROUP_HAM_ALL, GROUP_HAM_ANALOG),
    ),
    ServiceBlockSpec(
        "dstar", "D-STAR Repeaters", "Ham D-STAR",
        lambda k: (_near(k, "THD75LOCAL", dept=r"D-STAR", ranges=_VHF_UHF_HAM),),
        tx=TXK_HAM_REPEATER, sort=SORT_NEAREST, limit=60, radius=True, fill=True,
        requires=_all(_demodulates("DV"), _knob("include_dstar")), tx_probe=(146.0, 440.0),
        groups=(GROUP_HAM_ALL,),
        notes="Also loaded into the TH-D75's native DR repeater list.",
    ),
    ServiceBlockSpec(
        "dmr-core", "DMR Core", "Ham DMR Core",
        lambda k: _dmr(k, _DMR_CORE),
        tx=TXK_HAM_REPEATER, sort=SORT_TIER_DISTANCE, limit=100, radius=True,
        requires=_all(_demodulates("DMR"), _knob("include_dmr")), tx_probe=(146.0, 440.0),
        groups=(GROUP_HAM_ALL, GROUP_HAM_DMR),
        notes=(
            "Calling and local talkgroups (tiers 0-1) on the nearest machines: sorted by "
            "talkgroup tier, then distance, so the first scan list is the one worth starting."
        ),
    ),
    ServiceBlockSpec(
        "dmr-local", "DMR Local", "Ham DMR Local",
        lambda k: _dmr(k, _DMR_CORE),
        tx=TXK_HAM_REPEATER, sort=SORT_TIER_DISTANCE, limit=600, radius=True, fill=True,
        requires=_all(_demodulates("DMR"), _knob("include_dmr")), tx_probe=(146.0, 440.0),
        groups=(GROUP_HAM_DMR,),
        notes="The remaining tier 0-1 channels, beyond the first hundred.",
    ),
    ServiceBlockSpec(
        "dmr-wide", "DMR Wide Area", "Ham DMR Wide",
        lambda k: _dmr(k, _DMR_WIDE) + (_near(k, "PSHAM01", dept=r"DMR", ranges=_VHF_UHF_HAM),),
        tx=TXK_HAM_REPEATER, sort=SORT_TIER_DISTANCE, limit=800, radius=True, fill=True,
        requires=_all(_demodulates("DMR"), _knob("include_dmr")), tx_probe=(146.0, 440.0),
        groups=(GROUP_HAM_DMR,),
        notes="Wide-area and test talkgroups (tiers 2-3).",
    ),
    ServiceBlockSpec(
        "ham-nxdn", "Ham NXDN", "Ham NXDN",
        lambda k: (_near(k, "PSHAM01", dept=r"NXDN", ranges=_VHF_UHF_HAM),),
        tx=TXK_HAM_REPEATER, sort=SORT_NEAREST, limit=6, radius=True,
        requires=_demodulates("NXDN"), tx_probe=(146.0, 440.0),
        groups=(GROUP_HAM_ALL,),
        notes=(
            "Coordinated NXDN machines on their published RAN (KC7BAE on 443.050, RAN 5). "
            "Receive only: WWARA publishes no NXDN group ID to key up with."
        ),
    ),
    ServiceBlockSpec(
        "simplex", "Simplex Calling", "Ham Simplex",
        lambda k: (
            _keys("HAM01", labels=r"FM simplex|SSB calling|SSB and CW calling"),
            _keys("PSHAM01", dept=r"Operator-Published", labels=r"Simplex"),
            _keys("THD75LOCAL", dept=r"Calling"),
            _keys("ATD890LOCAL", dept=r"DMR Simplex"),
            _keys("SEAACS", dept=r"^ACS (VHF|UHF)$", labels=r"^[UV]2\d"),
        ),
        tx=TXK_HAM_SIMPLEX, limit=40, tx_probe=(29.6, 52.525, 146.52, 446.0),
        groups=(GROUP_HAM_ALL, GROUP_HAM_ANALOG),
    ),
    ServiceBlockSpec(
        "seattle-acs", "Seattle ACS", "Ham Seattle ACS",
        lambda k: (_keys("SEAACS", dept=r"^ACS (VHF|UHF)$", exclude=r"^[UV]2\d|N ", ranges=_VHF_UHF_HAM),),
        tx=TXK_HAM_REPEATER, sort=SORT_NATURAL, limit=120, requires=_receives(146.0, 440.0),
        tx_probe=(146.0, 440.0), groups=(GROUP_HAM_ALL, GROUP_HAM_ANALOG),
        notes="Seattle Auxiliary Communications Service repeater plan with its access tones.",
    ),
    ServiceBlockSpec(
        "nets", "Nets", "Ham Nets",
        lambda k: (_keys("PSHAM01", dept=r"Operator-Published"),),
        # No radius: these rows carry no coordinates of their own, only the
        # department's fence, so a per-station distance filter drops them all.
        tx=TXK_HAM_REPEATER, sort=SORT_NATURAL, limit=50,
        requires=_receives(146.0), tx_probe=(146.0,),
        groups=(GROUP_HAM_ALL, GROUP_HAM_ANALOG),
        notes=(
            "Repeaters and simplex channels that carry a scheduled net, each with its "
            "day and time in the channel note. One zone and one scan list, so a net "
            "night is a single list to sit on."
        ),
    ),
    # -- HF -------------------------------------------------------------------
    ServiceBlockSpec(
        "hf-nets", "HF Voice Nets", "Ham HF Nets",
        lambda k: (
            _keys("HFNET01", dept=r"Emergency and Weather|Centres of Activity|Traffic and Calling|Pacific Northwest"),
        ),
        limit=40, requires=_all(_knob("include_hf"), _receives(7.2)),
        notes="Receive only: nets run to a protocol.",
    ),
    ServiceBlockSpec(
        "hf-calling", "HF Calling", "Ham HF Calling",
        lambda k: (_keys("HAM01", labels=r"QRP|CALLING|CLLNG", ranges=((1.8, 30.0),)),),
        tx=TXK_HAM_SIMPLEX, limit=40, requires=_all(_knob("include_hf"), _receives(14.2)),
        tx_probe=(7.2, 14.2, 21.3),
        notes="Band-plan calling and QRP centres; transmit only inside the licence class's privileges.",
    ),
    ServiceBlockSpec(
        "hf-digital", "HF Digital", "Ham HF Digital",
        lambda k: (_keys("HAM01", labels=r"FT8|FT4|WSPR|PSK31|RTTY|SSTV"),),
        limit=40, skip_scan=True, requires=_all(_knob("include_hf"), _receives(14.2)),
    ),
    ServiceBlockSpec(
        "hf-reference", "Beacons and Time", "Beacons & Time",
        lambda k: (
            _keys("HFNET01", dept=r"Propagation Beacons|Time and Frequency|Utility and Aeronautical|6 Meter Calling"),
            _keys("HAM01", dept=r"Time and Frequency"),
        ),
        limit=40, skip_scan=True, requires=_all(_knob("include_hf"), _receives(10.0)),
        notes="Continuous carriers: tune by hand.",
    ),
    # -- air --------------------------------------------------------------------
    # FAAAIR (the FAA's own frequency file) comes first: every tower, approach,
    # Seattle Center outlet, CTAF and weather broadcast within the radius,
    # nearest first. The blocks after it add only what it does not hold.
    ServiceBlockSpec(
        "air-towers", "Airport Towers", "Air Towers",
        lambda k: (
            ChannelSelector(
                favorite_keys=("FAAAIR",),
                label_pattern=r"\b(TWR|ATIS)\b",
                freq_ranges=AIR,
                within_miles=k.within,
            ),
        ),
        sort=SORT_NEAREST, limit=0, radius=True, skip_labels=CONTINUOUS,
        requires=_all(_knob("include_air"), _demodulates("AM"), _receives(121.5)),
        notes="The nearest towers and ATIS (programmed, not scanned), for radios too small for the full airport block.",
    ),
    ServiceBlockSpec(
        "air-local", "Airports Near Home", "Air Local",
        lambda k: (_near(k, "FAAAIR", ranges=MIL_AIR + (MIL_VHF if k.am_outside_airband else ())),),
        sort=SORT_NEAREST, limit=130, radius=True, fill=True, skip_labels=CONTINUOUS,
        requires=_all(_knob("include_air"), _demodulates("AM"), _receives(121.5)),
        notes="FAA NASR: towers, ground, ATIS, approach, Seattle Center, CTAF/UNICOM and ASOS/AWOS; AM, nearest first.",
    ),
    ServiceBlockSpec(
        "air-civil", "Airband Civil", "Air Civil",
        lambda k: (
            _keys("FL46", "FL48", ranges=AIR),
            _rr_county(k, service_types=AIRCRAFT, ranges=AIR),
            _rr_state(
                dept=r"Airports Air Traffic Control|Airports Boeing|Airports Airlines|Seaplanes|Air to Air|"
                r"Paine Field|Airports Aircraft|Airports Airline Operations|Medevac",
                ranges=AIR,
            ),
        ),
        sort=SORT_NEAREST, limit=200, fill=True, skip_labels=CONTINUOUS,
        requires=_all(_knob("include_air"), _demodulates("AM"), _receives(121.5)),
        notes="AM; the AT-D890UV routes these rows to its separate air-band list.",
    ),
    ServiceBlockSpec(
        "air-mil", "Airband Military SAR", "Air Military",
        lambda k: (
            # The national SAR aviation channels are heard anywhere; the
            # military and medevac lists are regional.
            _keys("FL44", ranges=MIL_AIR, anywhere=True),
            _keys("FL49", "FL55", ranges=MIL_AIR),
            _rr_state(dept=r"JBLM|Joint Base|Fairchild|Civil Air Patrol", ranges=MIL_AIR),
        ),
        sort=SORT_NEAREST, limit=60, fill=True, skip_labels=CONTINUOUS,
        requires=_all(_knob("include_air"), _demodulates("AM"), _receives(121.5)),
    ),
    # -- weather: ahead of the service blocks, so a NOAA frequency another list
    # also carries (an events list's "NOAA Weather Radio") is claimed here,
    # unscanned, and never lands in a scanned block.
    ServiceBlockSpec(
        "noaa", "NOAA Weather", "Weather",
        lambda k: (
            _keys("FL75", ranges=_exact(NOAA), anywhere=True),
            # Any other list's copy of a NOAA channel the statewide list lacks
            # (a trip pack's 162.500) is claimed here too, unscanned.
            ChannelSelector(favorite_key_pattern=r".*", freq_ranges=_exact(NOAA), anywhere=True),
        ),
        sort=SORT_NEAREST, limit=7, skip_scan=True,
        notes="Continuous carriers; select by hand.",
    ),
    # -- public service -------------------------------------------------------
    ServiceBlockSpec(
        "sar", "SAR and Interop", "SAR & Interop",
        lambda k: (
            _keys("FL01", "FL02", "FL03", ranges=NON_HAM, anywhere=True),
            _rr_state(dept=r"Search and Rescue|Mutual Aid|Interoperability|CEMNET", anywhere=True),
            _rr_county(k, service_types=INTEROP),
        ),
        sort=SORT_NEAREST, limit=100, fill=True, groups=(GROUP_PUB_SVC,),
    ),
    ServiceBlockSpec(
        "wildfire", "Wildfire", "Wildfire",
        lambda k: (
            # None of these rows carries a position, so the order of the
            # selectors is the ranking: the three backcountry lists inside the
            # home radius (Mountain Loop, Snoqualmie Pass, Mount Rainier), the
            # DNR regions that cover home, the statewide plans, then the rest.
            # Ham repeaters these lists carry belong to the ham groups.
            _keys("FL34", "FL35", "FL37", ranges=NON_HAM),
            _rr_state(dept=r"Natural Resources (Tactical|Aircraft|South Puget|Northwest)"),
            _keys("FL06", "FL07", ranges=NON_HAM),
            _rr_state(
                dept=r"Natural Resources (Olympic|Pacific Cascade)|Forest Service|Mt Baker|Olympic National|National Park",
            ),
        ),
        sort=SORT_NEAREST, limit=100, fill=True, groups=(GROUP_PUB_SVC,),
    ),
    ServiceBlockSpec(
        "marine", "Marine", "Marine",
        lambda k: (
            # The marine channel plans first (USCG, ferries and VTS, ports),
            # then any other list's marine working channels, nearest first.
            _keys("FL52", ranges=MARINE, exclude=r"\bAIS\b", anywhere=True),
            _keys("FL53", "FL54", ranges=MARINE, exclude=r"\bAIS\b"),
            ChannelSelector(favorite_key_pattern=r".*", freq_ranges=MARINE, exclude_label_pattern=r"\bAIS\b"),
        ),
        sort=SORT_NEAREST, limit=60, fill=True, groups=(GROUP_MARINE_RAIL,),
        notes="Selected by band: every marine working channel any list carries, the channel plans first.",
    ),
    ServiceBlockSpec(
        "rail", "Rail", "Rail",
        lambda k: (
            _keys("FL56", "FL58", ranges=NON_HAM),
            _rr_state(
                dept=r"Washington Railroads (Operations|Seattle|Scenic|Stampede|Bellingham|Sumas|"
                r"Cherry Point|Capital|Tidelands|Other)",
            ),
            _rr_county(k, service_types=RAILROAD),
        ),
        sort=SORT_NEAREST, limit=40, fill=True, groups=(GROUP_MARINE_RAIL,),
    ),
    # -- personal radio -------------------------------------------------------
    # GMRS and FRS transmit at the radio's highest power by the operator's
    # choice. 47 CFR 95.1767 limits a GMRS station to 5 W ERP on channels 1-7
    # and 0.5 W ERP on 8-14; see docs/fleet-updates.md.
    ServiceBlockSpec(
        "gmrs-interstitial", "GMRS 1-7", "GMRS/FRS/MURS",
        lambda k: (_keys("FL65", ranges=_exact(GMRS_INTERSTITIAL)),),
        tx=TXK_GMRS, sort=SORT_NATURAL, limit=7, tx_probe=_GMRS_PROBE,
        groups=(GROUP_PERSONAL,),
        notes="Full power by the operator's choice; 47 CFR 95.1767 sets 5 W ERP here.",
    ),
    ServiceBlockSpec(
        "frs", "FRS 8-14", "GMRS/FRS/MURS",
        lambda k: (_keys("FL65", ranges=_exact(FRS_ONLY)),),
        tx=TXK_GMRS, sort=SORT_NATURAL, limit=7, tx_probe=_FRS_PROBE,
        groups=(GROUP_PERSONAL,),
        notes="Full power by the operator's choice; 47 CFR 95.1767 sets 0.5 W ERP here.",
    ),
    ServiceBlockSpec(
        "gmrs-main", "GMRS 15-22", "GMRS/FRS/MURS",
        lambda k: (_keys("FL65", ranges=_exact(GMRS_MAIN)),),
        tx=TXK_GMRS, sort=SORT_NATURAL, limit=8, tx_probe=_GMRS_PROBE,
        groups=(GROUP_PERSONAL,),
        notes="Simplex on the eight main channels; repeaters are the next block.",
    ),
    ServiceBlockSpec(
        "gmrs-repeaters", "GMRS Repeaters", "GMRS/FRS/MURS",
        lambda k: (
            _near(k, "GMRS01", ranges=((462.54, 462.74),)),
            _rr_county(k, dept=r"GMRS", ranges=((462.54, 462.74),)),
        ),
        tx=TXK_GMRS, sort=SORT_NEAREST, limit=20, radius=True, fill=True, tx_probe=_GMRS_PROBE,
        groups=(GROUP_PERSONAL,),
        notes="Nearest open repeaters first, each on its input and access tone.",
    ),
    ServiceBlockSpec(
        "murs", "MURS", "GMRS/FRS/MURS",
        lambda k: (_keys("FL66", ranges=_exact(MURS)),),
        tx=TXK_MURS, limit=5, power=POWER_HIGH, tx_probe=_MURS_PROBE,
        groups=(GROUP_PERSONAL,),
        notes="47 CFR 95.2767 caps MURS at 2 W ERP; the operator's explicit "
              "choice is the radio's highest step, as on GMRS and FRS.",
    ),
    ServiceBlockSpec(
        "business", "Business and Events", "Business",
        lambda k: (
            # The itinerant (color dot) channels are used anywhere; events,
            # media and utility lists are regional; county rows rank by distance.
            _keys("FL68", ranges=NON_HAM, anywhere=True),
            _keys("FL72", "FL73", "FL74a", "FL69", ranges=NON_HAM),
            _rr_county(k, service_types=BUSINESS),
            _rr_state(service_types=BUSINESS),
        ),
        sort=SORT_NEAREST, limit=400, fill=True,
    ),
    ServiceBlockSpec(
        "public-safety", "Public Safety Conventional", "Public Safety",
        lambda k: (
            _keys("FL13", "FL14", "FL16", "FL71", ranges=NON_HAM),
            _rr_county(k, service_types=PUBLIC_SAFETY),
            _rr_state(service_types=PUBLIC_SAFETY),
        ),
        sort=SORT_NEAREST, limit=400, fill=True, groups=(GROUP_PUB_SVC,),
        notes="Conventional only, nearest county first and dispatch before tactical; trunked P25 is the SDS150's job.",
    ),
    ServiceBlockSpec(
        "commercial-digital", "Commercial Digital", "Business Digital",
        lambda k: (
            _keys("FL70a", "FL70b"),
            _rr_county(k, modes=("DMR", "NXDN"), exclude=r"DSTAR"),
            # FCC-licensed digital voice, each at its licence location.
            _near(k, "FCCDIG"),
        ),
        sort=SORT_NEAREST, limit=100, fill=True, requires=_demodulates("DMR", "NXDN"), groups=(GROUP_PUB_SVC,),
    ),
    # -- programmed, never scanned ----------------------------------------------
    ServiceBlockSpec(
        "data", "Packet and Data", "Data",
        lambda k: (
            _keys("SEAACS", dept=r"Data"),
            _keys("FL62", "FL51", labels=r"Winlink|APRS|packet", include_avoided=True),
        ),
        limit=60, skip_scan=True,
    ),
    ServiceBlockSpec(
        "broadcast-fm", "FM Broadcast", "FM Broadcast",
        lambda k: (_keys("THD75BC", dept=r"FM Broadcast"),),
        limit=100, skip_scan=True,
        requires=_all(_knob("include_broadcast"), _demodulates("WFM", "FMB"), _receives(98.0)),
    ),
    ServiceBlockSpec(
        "broadcast-am", "AM Broadcast", "AM Broadcast",
        lambda k: (_keys("THD75BC", dept=r"AM Broadcast"),),
        limit=60, skip_scan=True,
        requires=_all(_knob("include_broadcast"), _demodulates("AM"), _receives(1.0)),
    ),
    # -- whatever else is near home -----------------------------------------------
    ServiceBlockSpec(
        "packs", "Local and Trip Packs", "Local Packs",
        lambda k: (
            ChannelSelector(
                favorite_key_pattern=r"^(LA|OUT|UL|OZ|KC)\d",
                within_miles=k.within,
                geo_fallback=GEO_DEPARTMENT,
            ),
        ),
        sort=SORT_NEAREST, limit=100, radius=True, fill=True, requires=_knob("include_trip_packs"),
        notes="Area packs whose coverage reaches home; channels other blocks already hold are skipped.",
    ),
    ServiceBlockSpec(
        "other-nearby", "Other Nearby", "Other Nearby",
        # Not FAAAIR: airband has its own budgeted blocks, and on the Anytone
        # every air row lands in the 256-entry AM air list.
        lambda k: (ChannelSelector(favorite_key_pattern=r"^(?!FAAAIR$).*", within_miles=k.within, geo_fallback=GEO_EITHER),),
        sort=SORT_NEAREST, limit=60, radius=True, fill=True, requires=_knob("catch_all"),
        notes="Anything located within range that no other block claimed, airband aside.",
    ),
)

#: Plan order - the order of the groups on every radio and of the memories on
#: the TD-H9 - follows the SDS150's Near Me lists: public service, air, ham,
#: rail & marine, business, with each handheld-only group (SAR & interop,
#: wildfire, GMRS/FRS/MURS...) beside its kin. Weather leads, unscanned,
#: because it must claim the NOAA channels before any scanned group can; SAR
#: and wildfire come before the broad public-safety group so their channels
#: land in their own group on every radio, whatever its size.
BLOCK_ORDER: Tuple[str, ...] = (
    "noaa",
    "sar", "wildfire", "public-safety",
    "air-towers", "air-local", "air-civil", "air-mil",
    # Nets comes before the general repeater blocks on purpose. A frequency is
    # programmed once, by the first block that claims it, and a repeater that
    # carries a scheduled net is more useful filed under Nets with its day and
    # time than buried among sixty others in Ham 2m.
    "nets",
    "ham-6m", "ham-2m", "ham-125", "ham-70cm", "dstar", "dmr-core", "dmr-local", "dmr-wide", "ham-nxdn",
    "simplex", "seattle-acs", "hf-nets", "hf-calling", "hf-digital", "hf-reference",
    "rail", "marine",
    "gmrs-interstitial", "frs", "gmrs-main", "gmrs-repeaters", "murs",
    "business", "commercial-digital",
    "data", "broadcast-fm", "broadcast-am", "packs", "other-nearby",
)
SERVICE_BLOCKS: Tuple[ServiceBlockSpec, ...] = tuple(sorted(_BLOCKS, key=lambda spec: BLOCK_ORDER.index(spec.id)))
SERVICE_BLOCKS_BY_ID: Dict[str, ServiceBlockSpec] = {spec.id: spec for spec in SERVICE_BLOCKS}


# --------------------------------------------------------------- policies --
def tx_policy_for(spec: ServiceBlockSpec, profile: RadioProfile, knobs: RadioKnobs) -> str:
    """Transmit policy for one block on one radio.

    The hardware is the only gate besides the licence: a block whose band
    the radio cannot transmit on is receive only outright, rather than a
    block of channels that each warn.
    """
    if profile.receive_only or spec.tx == TXK_NONE:
        return TX_NONE
    if spec.tx_probe and not any(profile.can_transmit(f) for f in spec.tx_probe):
        return TX_NONE
    if spec.tx == TXK_HAM_REPEATER:
        return TX_REPEATER if knobs.license_class else TX_NONE
    if spec.tx == TXK_HAM_SIMPLEX:
        return TX_SIMPLEX if knobs.license_class else TX_NONE
    if spec.tx == TXK_GMRS:
        # Repeater when a published input exists, simplex otherwise: the main
        # GMRS channels double as repeater outputs.
        return TX_AUTO if knobs.gmrs_licensed else TX_NONE
    if spec.tx == TXK_MURS:
        return TX_SIMPLEX if knobs.murs_tx else TX_NONE
    return TX_NONE


def _power_label(spec: ServiceBlockSpec, knobs: RadioKnobs) -> str:
    high, mid, low = knobs.power
    return {POWER_HIGH: high, POWER_MID: mid, POWER_LOW: low}[spec.power]


def included_blocks(profile: RadioProfile, knobs: RadioKnobs) -> List[ServiceBlockSpec]:
    return [
        spec
        for spec in SERVICE_BLOCKS
        if knobs.limit_for(spec) > 0 and spec.requires(profile, knobs)
    ]


def _scan_groups(specs: List[ServiceBlockSpec]) -> Tuple[ScanGroup, ...]:
    groups: List[ScanGroup] = []
    # Near Me is quota-driven rather than block-driven, so it is built from
    # NEAR_ME_QUOTAS directly and skips any block this radio did not get.
    scannable = {s.label for s in specs if not s.skip_scan}
    near = tuple((label, n) for label, n in NEAR_ME_QUOTAS if label in scannable)
    if near:
        groups.append(
            ScanGroup(
                GROUP_NEAR_ME,
                tuple(label for label, _ in near),
                take=near,
                notes=(
                    "The pinned repeaters, then the nearest reachable few of every amateur service, "
                    "in one list in frequency order."
                ),
                pinned=NEAR_ME_PINNED,
                reach_miles=NEAR_ME_REACH_MILES,
                frequency_order=True,
            )
        )
    for name in SCAN_GROUP_ORDER:
        if name == GROUP_NEAR_ME:
            continue
        members = tuple(s.label for s in specs if name in s.groups and not s.skip_scan)
        if members:
            groups.append(ScanGroup(name, members, frequency_order=True))
    # Air rows live in a separate list on the Anytone and HF is a different
    # radio mode everywhere, so "Everything" is every other scannable block.
    everything = tuple(
        s.label for s in specs if not s.skip_scan and not s.id.startswith(("air-", "hf-"))
    )
    if everything:
        groups.append(ScanGroup(GROUP_EVERYTHING, everything, frequency_order=True))
    return tuple(groups)


def _description(profile: RadioProfile, knobs: RadioKnobs, specs: List[ServiceBlockSpec]) -> str:
    tx = [s.label for s in specs if tx_policy_for(s, profile, knobs) != TX_NONE]
    return (
        f"Generated from the fleet template: everything the {profile.label} can use within "
        f"{knobs.radius_miles:g} miles of home, one block per service. Transmit: "
        + (", ".join(tx) if tx else "none")
        + "."
    )


def fleet_plan_id(radio_id: str) -> str:
    return f"{radio_id}-fleet"


def build_fleet_plan(radio_id: str, knobs: Optional[RadioKnobs] = None) -> ChannelPlan:
    profile = get_profile(radio_id)
    if profile.max_channels is None:
        raise ValueError(
            f"{radio_id}: the fleet template builds memory-list plans; the "
            f"{profile.label} installs Favorites Lists instead"
        )
    knobs = knobs or default_knobs(radio_id)
    specs = included_blocks(profile, knobs)
    blocks = tuple(
        PlanBlock(
            label=spec.label,
            selectors=tuple(spec.selectors(knobs)),
            tx_policy=tx_policy_for(spec, profile, knobs),
            power=_power_label(spec, knobs),
            sort=spec.sort,
            limit=knobs.limit_for(spec),
            skip_scan=spec.skip_scan,
            skip_label_pattern=spec.skip_labels,
            notes=spec.notes,
            bank=spec.bank if knobs.bank_names else "",
            fill=spec.fill and knobs.fill_to_capacity,
            fill_limit=knobs.fill_limits.get(spec.id),
        )
        for spec in specs
    )
    return ChannelPlan(
        id=fleet_plan_id(radio_id),
        radio_id=radio_id,
        label=f"{profile.model} - Fleet ({knobs.radius_miles:g} mi)",
        description=_description(profile, knobs, specs),
        blocks=blocks,
        reserve_slots=knobs.reserve_slots,
        scan_groups=_scan_groups(specs) if profile.supports_banks else (),
        license_class=knobs.license_class,
        gmrs_call=knobs.gmrs_call if knobs.gmrs_licensed else "",
        # The catch-all overlaps every block; without this it would add a
        # receive-only copy of channels already programmed with transmit.
        skip_receive_duplicates=True,
        home=knobs.home,
        radius_miles=knobs.radius_miles,
        fill_to_capacity=knobs.fill_to_capacity,
        canonical_labels=True,
        # Transmit follows the service, not the block: a ham repeater the
        # catch-all block picks up is keyable like any other (see
        # wasds150.radios.services and docs/fleet-updates.md).
        transmit_by_service=True,
        gmrs_licensed=knobs.gmrs_licensed,
        murs_transmit=knobs.murs_tx,
        # Stations are chosen nearest first; every list then reads low to high.
        frequency_order=True,
    )


def slot_budget(radio_id: str, knobs: Optional[RadioKnobs] = None) -> int:
    """Sum of the block ceilings; never more than the radio's capacity."""
    profile = get_profile(radio_id)
    knobs = knobs or default_knobs(radio_id)
    return sum(knobs.limit_for(spec) for spec in included_blocks(profile, knobs))


# ---------------------------------------------------------------- defaults --
#: TD-H9: 199 memories and no banks, so every block is small and the list
#: reads as one scan in service order.
_TD_H9 = RadioKnobs(
    reserve_slots=4,
    include_hf=False,
    include_broadcast=False,
    include_trip_packs=False,
    power=("10W", "5.0W", "1.0W"),
    limits={
        # Nets takes its twelve from the two repeater blocks, which is where
        # those repeaters would otherwise have sat: a frequency is programmed
        # once, and Nets claims it first.
        "nets": 12,
        "ham-2m": 32, "ham-125": 4, "ham-70cm": 30, "simplex": 6, "seattle-acs": 0,
        "air-towers": 8, "air-local": 0, "air-civil": 0, "air-mil": 0, "sar": 10, "wildfire": 6, "marine": 12, "rail": 4,
        "gmrs-interstitial": 7, "frs": 7, "gmrs-main": 8, "gmrs-repeaters": 9, "murs": 5, "business": 6,
        "public-safety": 12, "data": 0, "noaa": 7, "other-nearby": 10,
    },
)

#: FTX-1: 999 memories, HF included; digital voice is C4FM, so no D-STAR.
_FTX1 = RadioKnobs(
    reserve_slots=40,
    include_dmr=False,
    include_dstar=False,
    power=("High", "Mid", "Low"),
    limits={
        "nets": 50,
        "ham-6m": 20, "ham-2m": 85, "ham-70cm": 125, "simplex": 20, "seattle-acs": 40,
        "hf-nets": 40, "hf-calling": 40, "hf-digital": 40, "hf-reference": 40,
        # VHF airband only: the FTX-1 does not receive 225-400 MHz.
        "air-local": 90, "air-civil": 40, "air-mil": 10, "sar": 40, "wildfire": 40, "marine": 30, "rail": 15,
        "business": 30, "public-safety": 50, "data": 10, "broadcast-am": 20, "packs": 20,
        "gmrs-repeaters": 10, "other-nearby": 20,
    },
)

#: TH-D75: 1,000 memories in 30 groups; transmit on 2 m, 1.25 m and 70 cm.
#: The reserve is the operator's fifty free slots plus a hundred for the Near
#: Me group of copies (see docs/scan-groups.md): Group Link reaches whole
#: groups, so the curated list has to be a group of its own.
_TH_D75 = RadioKnobs(
    reserve_slots=150,
    power=("5.0W", "5.0W", "0.5W"),
    limits={
        "nets": 50,
        # A hundred fewer than before, for the Near Me group of copies: off
        # the least-scanned blocks (distant airports, broadcast, beacons).
        "ham-6m": 20, "ham-2m": 50, "ham-125": 20, "ham-70cm": 96, "dstar": 25,
        "simplex": 20, "seattle-acs": 30, "hf-nets": 20, "hf-calling": 20, "hf-digital": 10,
        # Band B hears civil VHF and military UHF airband alike.
        "hf-reference": 10, "air-local": 90, "air-civil": 40, "air-mil": 10, "sar": 40, "wildfire": 40,
        "marine": 30, "rail": 15, "business": 30, "public-safety": 50, "data": 10,
        "broadcast-fm": 20, "broadcast-am": 20, "packs": 20, "gmrs-repeaters": 10, "other-nearby": 20,
    },
)

#: AT-D890UV: 4,000 channels in zones of up to 160. Air rows go to the
#: separate AM air list, which holds 256 (``AM_AIR_MAX``), so the three air
#: blocks together stay under it.
_AT_D890UV = RadioKnobs(
    reserve_slots=200,
    power=("High", "Mid", "Low"),
    # Nets takes its fifty from the two repeater blocks, which is where those
    # repeaters would otherwise have sat.
    limits={
        "nets": 50, "ham-2m": 135, "ham-70cm": 135,
        "packs": 60, "air-local": 90, "air-civil": 140, "air-mil": 20,
    },
    # Filling spare slots must not push the air rows past the AM list either.
    fill_limits={"air-local": 200, "air-civil": 36, "air-mil": 20},
    # Its main channel table is analog FM or digital only: AM exists solely
    # in the air-band list, so 138.6 MHz AM cannot be programmed.
    am_outside_airband=False,
)

#: ID-52A: 1,000 memories in groups of 100, so no block may exceed a group.
#: No HF and no broadcast receiver; D-STAR, and no DMR.
#:
#: The reserve carries the operator's own fifty slots and, on top of them,
#: the ``Near Me`` group: the radio scans one memory group at a time and a
#: memory belongs to one group, so that list exists only as a second copy of
#: its seventy-six channels. They come off the far end of the fill blocks,
#: which is the most distant thing the radio was holding. This is the only
#: radio where widening Near Me costs memories - the Anytone spends a scan
#: list, the FTX-1 a flag on channels already there.
_ID52A = RadioKnobs(
    reserve_slots=126,
    include_hf=False,
    include_broadcast=False,
    include_dmr=False,
    power=("High", "Mid", "Low1"),
    limits={
        "noaa": 7, "sar": 40, "wildfire": 60, "public-safety": 100,
        "air-local": 100, "air-civil": 30, "air-mil": 10,
        "nets": 44, "ham-2m": 78, "ham-70cm": 78, "dstar": 25, "simplex": 20, "seattle-acs": 50,
        "rail": 15, "marine": 40,
        "gmrs-interstitial": 7, "frs": 7, "gmrs-main": 8, "gmrs-repeaters": 10, "murs": 5,
        # Seventy off the three widest-reaching blocks, which is what the
        # Near Me copy costs; these are the most distant rows on the radio.
        "business": 65, "data": 10, "packs": 35, "other-nearby": 30,
    },
)

_DEFAULT_KNOBS: Dict[str, RadioKnobs] = {
    "td-h9": _TD_H9,
    "ftx1": _FTX1,
    "th-d75": _TH_D75,
    "at-d890uv": _AT_D890UV,
    "id-52a": _ID52A,
}


def default_knobs(radio_id: str) -> RadioKnobs:
    return _DEFAULT_KNOBS.get(str(radio_id).strip().lower(), RadioKnobs())


def fleet_plans() -> Dict[str, ChannelPlan]:
    return {fleet_plan_id(radio_id): build_fleet_plan(radio_id) for radio_id in FLEET_PLAN_RADIOS}
