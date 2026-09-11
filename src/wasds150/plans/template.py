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
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Tuple

from wasds150.models.plan import (
    GEO_DEPARTMENT,
    GEO_EITHER,
    SORT_FREQ,
    SORT_NATURAL,
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
FLEET_PLAN_RADIOS = ("td-h9", "ftx1", "th-d75", "at-d890uv")

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
#: Marine VHF from channel 5A up, plus the coast-station half of the duplex
#: channels. Starts above 156.2475 because 156.0-156.24 MHz is land-mobile
#: public safety in parts of Washington; AIS is excluded by label.
MARINE = ((156.2475, 157.4250), (161.7750, 161.9625))

GMRS_MAIN = (462.550, 462.575, 462.600, 462.625, 462.650, 462.675, 462.700, 462.725)
GMRS_INTERSTITIAL = (462.5625, 462.5875, 462.6125, 462.6375, 462.6625, 462.6875, 462.7125)
FRS_ONLY = (467.5625, 467.5875, 467.6125, 467.6375, 467.6625, 467.6875, 467.7125)
MURS = (151.820, 151.880, 151.940, 154.570, 154.600)
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

GROUP_HAM_ALL = "Ham All"
GROUP_HAM_ANALOG = "Ham Analog"
GROUP_HAM_DMR = "Ham DMR"
GROUP_PUB_SVC = "Pub Svc"
GROUP_MARINE_RAIL = "Marine Rail"
GROUP_PERSONAL = "Personal"
GROUP_EVERYTHING = "Everything"
SCAN_GROUP_ORDER = (
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
) -> ChannelSelector:
    """The statewide RadioReference list, minus the far side of the state."""
    return ChannelSelector(
        favorite_keys=("RRWA",),
        department_pattern=dept,
        exclude_department_pattern=FAR_AWAY,
        freq_ranges=tuple(ranges),
        service_types=tuple(service_types),
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
    )


SERVICE_BLOCKS: Tuple[ServiceBlockSpec, ...] = (
    # -- amateur, transmit where licensed ------------------------------------
    ServiceBlockSpec(
        "ham-6m", "Ham 6m Repeaters", "Ham 6m",
        lambda k: (_near(k, "PSHAM01", "PSHAM02", dept=r"Analog 6 Meter|Linked Analog", ranges=((50.0, 54.0),)),),
        tx=TXK_HAM_REPEATER, sort=SORT_TIER_DISTANCE, limit=40, radius=True, requires=_receives(52.0), tx_probe=(52.0,),
        groups=(GROUP_HAM_ALL, GROUP_HAM_ANALOG),
    ),
    ServiceBlockSpec(
        "ham-2m", "Ham 2m Repeaters", "Ham 2m",
        lambda k: (
            _near(k, "PSHAM01", dept=r"Analog 2 Meter|Linked Analog", ranges=((144.0, 148.0),)),
            _near(k, "THD75WWARA", dept=r"2 Meter", ranges=((144.0, 148.0),)),
        ),
        tx=TXK_HAM_REPEATER, sort=SORT_TIER_DISTANCE, limit=160, radius=True, requires=_receives(146.0),
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
        tx=TXK_HAM_REPEATER, sort=SORT_TIER_DISTANCE, limit=30, radius=True, requires=_receives(223.5),
        tx_probe=(223.5,), groups=(GROUP_HAM_ALL, GROUP_HAM_ANALOG),
    ),
    ServiceBlockSpec(
        "ham-70cm", "Ham 70cm Repeaters", "Ham 70cm",
        lambda k: (
            _near(k, "PSHAM01", dept=r"Analog 70 Centimeter|Linked Analog", ranges=((420.0, 450.0),)),
            _near(k, "THD75WWARA", dept=r"70 Centimeter", ranges=((420.0, 450.0),)),
            _keys("THD75USER"),
        ),
        tx=TXK_HAM_REPEATER, sort=SORT_TIER_DISTANCE, limit=160, radius=True, requires=_receives(440.0),
        tx_probe=(440.0,), groups=(GROUP_HAM_ALL, GROUP_HAM_ANALOG),
    ),
    ServiceBlockSpec(
        "dstar", "D-STAR Repeaters", "D-STAR",
        lambda k: (_near(k, "THD75LOCAL", dept=r"D-STAR", ranges=_VHF_UHF_HAM),),
        tx=TXK_HAM_REPEATER, limit=60, radius=True,
        requires=_all(_demodulates("DV"), _knob("include_dstar")), tx_probe=(146.0, 440.0),
        groups=(GROUP_HAM_ALL,),
        notes="Also loaded into the TH-D75's native DR repeater list.",
    ),
    ServiceBlockSpec(
        "dmr-core", "DMR Core", "DMR Core",
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
        "dmr-local", "DMR Local", "DMR Local",
        lambda k: _dmr(k, _DMR_CORE),
        tx=TXK_HAM_REPEATER, sort=SORT_TIER_DISTANCE, limit=600, radius=True,
        requires=_all(_demodulates("DMR"), _knob("include_dmr")), tx_probe=(146.0, 440.0),
        groups=(GROUP_HAM_DMR,),
        notes="The remaining tier 0-1 channels, beyond the first hundred.",
    ),
    ServiceBlockSpec(
        "dmr-wide", "DMR Wide Area", "DMR Wide",
        lambda k: _dmr(k, _DMR_WIDE) + (_near(k, "PSHAM01", dept=r"DMR", ranges=_VHF_UHF_HAM),),
        tx=TXK_HAM_REPEATER, sort=SORT_TIER_DISTANCE, limit=800, radius=True,
        requires=_all(_demodulates("DMR"), _knob("include_dmr")), tx_probe=(146.0, 440.0),
        groups=(GROUP_HAM_DMR,),
        notes="Wide-area and test talkgroups (tiers 2-3), and coordinated DMR machines with no published layout.",
    ),
    ServiceBlockSpec(
        "simplex", "Simplex Calling", "Simplex",
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
        "seattle-acs", "Seattle ACS", "Seattle ACS",
        lambda k: (_keys("SEAACS", dept=r"^ACS (VHF|UHF)$", exclude=r"^[UV]2\d|N ", ranges=_VHF_UHF_HAM),),
        tx=TXK_HAM_REPEATER, sort=SORT_NATURAL, limit=120, requires=_receives(146.0, 440.0),
        tx_probe=(146.0, 440.0), groups=(GROUP_HAM_ALL, GROUP_HAM_ANALOG),
        notes="Seattle Auxiliary Communications Service repeater plan with its access tones.",
    ),
    # -- HF -------------------------------------------------------------------
    ServiceBlockSpec(
        "hf-nets", "HF Voice Nets", "HF Nets",
        lambda k: (
            _keys("HFNET01", dept=r"Emergency and Weather|Centres of Activity|Traffic and Calling|Pacific Northwest"),
        ),
        limit=40, requires=_all(_knob("include_hf"), _receives(7.2)),
        notes="Receive only: nets run to a protocol.",
    ),
    ServiceBlockSpec(
        "hf-calling", "HF Calling", "HF Calling",
        lambda k: (_keys("HAM01", labels=r"QRP|CALLING|CLLNG", ranges=((1.8, 30.0),)),),
        tx=TXK_HAM_SIMPLEX, limit=40, requires=_all(_knob("include_hf"), _receives(14.2)),
        tx_probe=(7.2, 14.2, 21.3),
        notes="Band-plan calling and QRP centres; transmit only inside the licence class's privileges.",
    ),
    ServiceBlockSpec(
        "hf-digital", "HF Digital", "HF Digital",
        lambda k: (_keys("HAM01", labels=r"FT8|FT4|WSPR|PSK31|RTTY|SSTV"),),
        limit=40, skip_scan=True, requires=_all(_knob("include_hf"), _receives(14.2)),
    ),
    ServiceBlockSpec(
        "hf-reference", "Beacons and Time", "Beacons Time",
        lambda k: (
            _keys("HFNET01", dept=r"Propagation Beacons|Time and Frequency|Utility and Aeronautical|6 Meter Calling"),
            _keys("HAM01", dept=r"Time and Frequency"),
        ),
        limit=40, skip_scan=True, requires=_all(_knob("include_hf"), _receives(10.0)),
        notes="Continuous carriers: tune by hand.",
    ),
    # -- air --------------------------------------------------------------------
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
        limit=200, requires=_all(_knob("include_air"), _demodulates("AM"), _receives(121.5)),
        notes="AM; the AT-D890UV routes these rows to its separate air-band list.",
    ),
    ServiceBlockSpec(
        "air-mil", "Airband Military SAR", "Air Mil SAR",
        lambda k: (
            _keys("FL49", "FL44", "FL55", ranges=MIL_AIR),
            _rr_state(dept=r"JBLM|Joint Base|Fairchild|Civil Air Patrol", ranges=MIL_AIR),
        ),
        limit=60, requires=_all(_knob("include_air"), _demodulates("AM"), _receives(121.5)),
    ),
    # -- public service -------------------------------------------------------
    ServiceBlockSpec(
        "sar", "SAR and Interop", "SAR Interop",
        lambda k: (
            _keys("FL01", "FL02", "FL03"),
            _rr_state(dept=r"Search and Rescue|Mutual Aid|Interoperability|CEMNET"),
            _rr_county(k, service_types=INTEROP),
        ),
        limit=100, groups=(GROUP_PUB_SVC,),
    ),
    ServiceBlockSpec(
        "wildfire", "Wildfire", "Wildfire",
        lambda k: (
            # FL34/FL35/FL37: Mountain Loop, Snoqualmie Pass and Mount Rainier,
            # the three backcountry lists inside the home radius.
            _keys("FL06", "FL07", "FL34", "FL35", "FL37"),
            _rr_state(
                dept=r"Natural Resources (Tactical|Aircraft|South Puget|Northwest|Olympic|Pacific Cascade)|"
                r"Forest Service|Mt Baker|Olympic National|National Park",
            ),
        ),
        limit=100, groups=(GROUP_PUB_SVC,),
    ),
    ServiceBlockSpec(
        "marine", "Marine", "Marine",
        lambda k: (ChannelSelector(favorite_key_pattern=r".*", freq_ranges=MARINE, exclude_label_pattern=r"\bAIS\b"),),
        limit=60, groups=(GROUP_MARINE_RAIL,),
        notes="Selected by band: every marine working channel any list carries.",
    ),
    ServiceBlockSpec(
        "rail", "Rail", "Rail",
        lambda k: (
            _keys("FL56", "FL58"),
            _rr_state(
                dept=r"Washington Railroads (Operations|Seattle|Scenic|Stampede|Bellingham|Sumas|"
                r"Cherry Point|Capital|Tidelands|Other)",
            ),
            _rr_county(k, service_types=RAILROAD),
        ),
        limit=40, groups=(GROUP_MARINE_RAIL,),
    ),
    # -- personal radio -------------------------------------------------------
    # GMRS and FRS transmit at the radio's highest power by the operator's
    # choice. 47 CFR 95.1767 limits a GMRS station to 5 W ERP on channels 1-7
    # and 0.5 W ERP on 8-14; see docs/fleet-updates.md.
    ServiceBlockSpec(
        "gmrs-interstitial", "GMRS 1-7", "GMRS FRS MURS",
        lambda k: (_keys("FL65", ranges=_exact(GMRS_INTERSTITIAL)),),
        tx=TXK_GMRS, sort=SORT_NATURAL, limit=7, tx_probe=_GMRS_PROBE,
        groups=(GROUP_PERSONAL,),
        notes="Full power by the operator's choice; 47 CFR 95.1767 sets 5 W ERP here.",
    ),
    ServiceBlockSpec(
        "frs", "FRS 8-14", "GMRS FRS MURS",
        lambda k: (_keys("FL65", ranges=_exact(FRS_ONLY)),),
        tx=TXK_GMRS, sort=SORT_NATURAL, limit=7, tx_probe=_FRS_PROBE,
        groups=(GROUP_PERSONAL,),
        notes="Full power by the operator's choice; 47 CFR 95.1767 sets 0.5 W ERP here.",
    ),
    ServiceBlockSpec(
        "gmrs-main", "GMRS 15-22", "GMRS FRS MURS",
        lambda k: (_keys("FL65", ranges=_exact(GMRS_MAIN)),),
        tx=TXK_GMRS, sort=SORT_NATURAL, limit=8, tx_probe=_GMRS_PROBE,
        groups=(GROUP_PERSONAL,),
        notes="Simplex on the eight main channels; repeaters are the next block.",
    ),
    ServiceBlockSpec(
        "gmrs-repeaters", "GMRS Repeaters", "GMRS FRS MURS",
        lambda k: (
            _near(k, "GMRS01", ranges=((462.54, 462.74),)),
            _rr_county(k, dept=r"GMRS", ranges=((462.54, 462.74),)),
        ),
        tx=TXK_GMRS, sort=SORT_TIER_DISTANCE, limit=20, radius=True, tx_probe=_GMRS_PROBE,
        groups=(GROUP_PERSONAL,),
        notes="Nearest listed open repeaters first, each on its published input and access tone.",
    ),
    ServiceBlockSpec(
        "murs", "MURS", "GMRS FRS MURS",
        lambda k: (_keys("FL66", ranges=_exact(MURS)),),
        tx=TXK_MURS, limit=5, power=POWER_LOW, tx_probe=_MURS_PROBE,
        groups=(GROUP_PERSONAL,),
        notes="47 CFR 95.2767 caps MURS at 2 W.",
    ),
    ServiceBlockSpec(
        "business", "Business and Events", "Business",
        lambda k: (
            _keys("FL68", "FL72", "FL73", "FL74a", "FL69"),
            _rr_county(k, service_types=BUSINESS),
            _rr_state(service_types=BUSINESS),
        ),
        limit=400,
    ),
    ServiceBlockSpec(
        "public-safety", "Public Safety Conventional", "Pub Safety",
        lambda k: (
            _keys("FL13", "FL14", "FL16", "FL71"),
            _rr_county(k, service_types=PUBLIC_SAFETY),
            _rr_state(service_types=PUBLIC_SAFETY),
        ),
        limit=400, groups=(GROUP_PUB_SVC,),
        notes="Conventional only; trunked P25 dispatch is the SDS150's job.",
    ),
    ServiceBlockSpec(
        "commercial-digital", "Commercial Digital", "Comm Digital",
        lambda k: (
            _keys("FL70a", "FL70b"),
            _rr_county(k, modes=("DMR", "NXDN"), exclude=r"DSTAR"),
            # FCC-licensed digital voice, each at its licence location.
            _near(k, "FCCDIG"),
        ),
        limit=100, requires=_demodulates("DMR", "NXDN"), groups=(GROUP_PUB_SVC,),
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
        "noaa", "NOAA Weather", "NOAA WX",
        lambda k: (_keys("FL75", ranges=_exact(NOAA)),),
        limit=7, skip_scan=True,
        notes="Continuous carriers; select by hand.",
    ),
    ServiceBlockSpec(
        "broadcast-fm", "FM Broadcast", "FM Bcast",
        lambda k: (_keys("THD75BC", dept=r"FM Broadcast"),),
        limit=100, skip_scan=True,
        requires=_all(_knob("include_broadcast"), _demodulates("WFM", "FMB"), _receives(98.0)),
    ),
    ServiceBlockSpec(
        "broadcast-am", "AM Broadcast", "AM Bcast",
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
        limit=100, radius=True, requires=_knob("include_trip_packs"),
        notes="Area packs whose coverage reaches home; channels other blocks already hold are skipped.",
    ),
    ServiceBlockSpec(
        "other-nearby", "Other Nearby", "Other Nearby",
        lambda k: (ChannelSelector(favorite_key_pattern=r".*", within_miles=k.within, geo_fallback=GEO_EITHER),),
        limit=60, radius=True, requires=_knob("catch_all"),
        notes="Anything located within range that no other block claimed.",
    ),
)

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
    for name in SCAN_GROUP_ORDER:
        members = tuple(s.label for s in specs if name in s.groups and not s.skip_scan)
        if members:
            groups.append(ScanGroup(name, members))
    # Air rows live in a separate list on the Anytone and HF is a different
    # radio mode everywhere, so "Everything" is every other scannable block.
    everything = tuple(
        s.label for s in specs if not s.skip_scan and not s.id.startswith(("air-", "hf-"))
    )
    if everything:
        groups.append(ScanGroup(GROUP_EVERYTHING, everything))
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
            notes=spec.notes,
            bank=spec.bank if knobs.bank_names else "",
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
        "ham-2m": 38, "ham-125": 4, "ham-70cm": 36, "simplex": 6, "seattle-acs": 0,
        "air-civil": 8, "air-mil": 0, "sar": 10, "wildfire": 6, "marine": 12, "rail": 4,
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
        "ham-6m": 40, "ham-2m": 150, "ham-70cm": 150, "simplex": 20, "seattle-acs": 40,
        "hf-nets": 40, "hf-calling": 40, "hf-digital": 40, "hf-reference": 40,
        "air-civil": 50, "air-mil": 20, "sar": 40, "wildfire": 40, "marine": 30, "rail": 15,
        "business": 30, "public-safety": 50, "data": 10, "broadcast-am": 20, "packs": 20,
        "gmrs-repeaters": 10, "other-nearby": 20,
    },
)

#: TH-D75: 1,000 memories in 30 groups; transmit on 2 m, 1.25 m and 70 cm.
_TH_D75 = RadioKnobs(
    reserve_slots=50,
    power=("5.0W", "5.0W", "0.5W"),
    limits={
        "ham-6m": 20, "ham-2m": 150, "ham-125": 30, "ham-70cm": 150, "dstar": 40,
        "simplex": 20, "seattle-acs": 50, "hf-nets": 20, "hf-calling": 20, "hf-digital": 10,
        "hf-reference": 20, "air-civil": 40, "air-mil": 20, "sar": 40, "wildfire": 40,
        "marine": 30, "rail": 15, "business": 30, "public-safety": 50, "data": 10,
        "broadcast-fm": 40, "broadcast-am": 20, "packs": 20, "gmrs-repeaters": 10, "other-nearby": 20,
    },
)

#: AT-D890UV: 4,000 channels in zones of up to 160; the template defaults fit.
_AT_D890UV = RadioKnobs(
    reserve_slots=200,
    power=("High", "Mid", "Low"),
    limits={"packs": 60},
)

_DEFAULT_KNOBS: Dict[str, RadioKnobs] = {
    "td-h9": _TD_H9,
    "ftx1": _FTX1,
    "th-d75": _TH_D75,
    "at-d890uv": _AT_D890UV,
}


def default_knobs(radio_id: str) -> RadioKnobs:
    return _DEFAULT_KNOBS.get(str(radio_id).strip().lower(), RadioKnobs())


def fleet_plans() -> Dict[str, ChannelPlan]:
    return {fleet_plan_id(radio_id): build_fleet_plan(radio_id) for radio_id in FLEET_PLAN_RADIOS}
