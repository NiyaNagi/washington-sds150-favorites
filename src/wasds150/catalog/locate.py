"""Give every department a geo-fence, so position can decide what is scanned.

A department with no position is everywhere. The SDS150's location control
cannot exclude it, whatever range the operator sets (SDS150 manual, *Set
Location Information*), and the plan's distance filter has to guess: a channel
with no site and no fence counts as here when its list is "relevant anywhere"
and infinitely far otherwise (:func:`wasds150.plan.resolve._select_for_block`).
Neither is true of a Snohomish County fire department, and between them they
left 4,062 of the scanner's 16,529 channels ungated.

Nothing here invents a position. Each rule reads something the catalog already
knows, and they run in order of how specific that knowledge is:

1. **The department's own channels.** A DMR network's "Puget Sound" department
   carries a repeater position on every row; the fence is their centre and
   their spread.
2. **A county named in the department's or system's label.** "Okanogan
   County", "Yakima Valley Yakima/Kittitas" - the county's Census internal
   point and land-area radius, from :mod:`wasds150.catalog.wa_counties`.
3. **Located sisters in the same system.** Sno911's "Radio Techs" has no
   position of its own, but the system it belongs to does.
4. **The favorites list's county.** ``PS-SNO`` says Snohomish, and every
   department in it is somewhere in Snohomish.
5. **A statewide fence**, for the sets that really are everywhere: nationwide
   interop, SAR mutual aid, CEMNET, the marine and wildfire nets. A circle
   round Washington is not "no position": it still says the channel is
   irrelevant in Arizona, and it keeps the plan treating these as here rather
   than as infinitely far.

A department nothing matches keeps ``None`` and behaves as it always has.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from wasds150.catalog.wa_counties import WA_COUNTIES, county_point
from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.util.geo import haversine_miles

#: Smallest fence a derived position gets. A department whose rows all sit on
#: one hilltop still covers the ground that repeater reaches.
MIN_FENCE_MILES = 5.0
#: Added to the spread of a department's own channels, for the coverage around
#: the outermost one.
SPREAD_MARGIN_MILES = 5.0

#: Labels that mark a set as genuinely everywhere rather than merely unplaced.
#: Kept deliberately narrow: a wrong statewide fence is invisible, and the
#: cost of missing one is only that the department stays as it is today.
_STATEWIDE = re.compile(
    r"\b(state ?wide|nation ?wide|anywhere|interop(erability)?|mutual aid|CEMNET|"
    r"NIFC|NOAA|USCG|marine|maritime|itinerant|national)\b",
    re.IGNORECASE,
)
#: "King County", "Yakima Valley Yakima/Kittitas" - a county name as a word.
_COUNTY_WORD = {
    name: re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE) for name in WA_COUNTIES
}
#: A list's own ``counties``/``region`` saying it covers the whole state. This
#: is the catalog's own metadata rather than a guess from a department name,
#: which is why it outranks :data:`_STATEWIDE`.
_STATEWIDE_METADATA = re.compile(
    r"\b(state ?wide|all 39 counties|wherever the scanner is)\b", re.IGNORECASE
)


@dataclass(frozen=True)
class Fence:
    lat: float
    lon: float
    radius_miles: float
    #: Which rule produced it, for the report and the audit.
    source: str


def _centre(points: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    """Mean of the points, good enough at the scale of a state."""
    return (
        sum(p[0] for p in points) / len(points),
        sum(p[1] for p in points) / len(points),
    )


def _fence_over(points: Sequence[Tuple[float, float]], source: str, margin: float) -> Optional[Fence]:
    if not points:
        return None
    lat, lon = _centre(points)
    spread = max((haversine_miles(lat, lon, p[0], p[1]) for p in points), default=0.0)
    return Fence(lat, lon, max(round(spread + margin, 1), MIN_FENCE_MILES), source)


def washington_fence() -> Fence:
    """A circle round the state, derived from the county table rather than
    written down, so it follows the Census data if that is ever refreshed."""
    points = [(c.lat, c.lon) for c in WA_COUNTIES.values()]
    lat, lon = _centre(points)
    radius = max(haversine_miles(lat, lon, c.lat, c.lon) + c.radius_miles for c in WA_COUNTIES.values())
    return Fence(lat, lon, round(radius, 1), "statewide")


def _county_in(text: str) -> Optional[Fence]:
    """The one Washington county this text names, or ``None``.

    Exactly one: "King, Snohomish, Pierce, Kitsap, Mason, ..." describes a
    region, and fencing it to whichever county sorted first would put a Puget
    Sound list inside King County.
    """
    found = [name for name, pattern in _COUNTY_WORD.items() if pattern.search(text)]
    if len(found) != 1:
        return None
    point = county_point(found[0])
    return Fence(point.lat, point.lon, point.radius_miles, f"county:{found[0]}") if point else None


def _counties_fence(text: str) -> Optional[Fence]:
    """A fence over every Washington county this text names.

    A list that covers "King, Snohomish, Pierce, Kitsap" is a region, and the
    circle over those four counties describes it. Used only for a list's own
    ``counties`` metadata, where a several-county string is a statement of
    coverage rather than an accident of wording.
    """
    points = [county_point(name) for name, pattern in _COUNTY_WORD.items() if pattern.search(text)]
    points = [p for p in points if p is not None]
    if not points:
        return None
    lat, lon = _centre([(p.lat, p.lon) for p in points])
    radius = max(haversine_miles(lat, lon, p.lat, p.lon) + p.radius_miles for p in points)
    names = ",".join(p.name for p in points[:3]) + ("..." if len(points) > 3 else "")
    return Fence(lat, lon, round(radius, 1), f"counties:{names}")


def _placed(channels: Iterable[Channel]) -> List[Tuple[float, float]]:
    return [(c.lat, c.lon) for c in channels if c.lat is not None and c.lon is not None]


#: Above this, a signal is line-of-sight and a fence describes its coverage.
#: Below it, it is not.
HF_CEILING_MHZ = 30.0


def _is_hf(department: Department) -> bool:
    """Whether every channel here is below :data:`HF_CEILING_MHZ`."""
    freqs = [c.freq_mhz for c in department.channels if c.freq_mhz is not None]
    return bool(freqs) and all(f < HF_CEILING_MHZ for f in freqs)


def _departments(favorite: FavoritesList) -> List[Tuple[System, Department]]:
    rows: List[Tuple[System, Department]] = []
    for system in favorite.systems:
        for department in system.departments:
            rows.append((system, department))
        for site in system.sites:
            for department in site.departments:
                rows.append((system, department))
    return rows


def fence_for(
    favorite: FavoritesList,
    system: System,
    department: Department,
    *,
    sisters: Sequence[Department] = (),
    statewide: bool = True,
) -> Optional[Fence]:
    """The fence :mod:`wasds150.catalog.locate` would give this department,
    or ``None`` when nothing in the catalog places it.

    ``statewide=False`` withholds the last rule. A circle over Washington is
    the right answer for the scanner, whose location control asks "is this
    list relevant where I am"; it is the wrong answer for a memory plan, which
    asks "how far away is this station". A statewide fence overlaps every
    radius circle, so a catch-all block that admits a channel whose department
    fence overlaps (``GEO_EITHER``) would take the whole state - Spokane
    towers arriving in a sixty-mile "Other Nearby". The plan already has a
    word for relevant-everywhere: ``ChannelSelector.anywhere``.
    """
    if department.lat is not None and department.lon is not None:
        return None
    if _is_hf(department):
        # Where an 80 m net is worked from is a propagation question, not a
        # geographic one: fencing "WA Traffic Net 80m" to the centre of the
        # counties its list names put it 112 miles away and dropped it from
        # every sweep. HF departments keep no fence and stay "anywhere".
        return None
    own = _fence_over(_placed(department.channels), "channels", SPREAD_MARGIN_MILES)
    if own is not None:
        return own
    named = _county_in(department.label or "") or _county_in(system.label or "")
    if named is not None:
        return named
    from_sisters = _fence_over(
        [(d.lat, d.lon) for d in sisters if d.lat is not None and d.lon is not None],
        "system",
        SPREAD_MARGIN_MILES,
    )
    if from_sisters is not None:
        return from_sisters
    if _STATEWIDE_METADATA.search(f"{favorite.counties} {favorite.region}"):
        return washington_fence() if statewide else None
    listed = _counties_fence(favorite.counties or "")
    if listed is not None:
        return listed
    if _STATEWIDE.search(f"{system.label} {department.label}"):
        return washington_fence() if statewide else None
    return None


def locate_favorite(favorite: FavoritesList, *, statewide: bool = True) -> Dict[str, int]:
    """Fill in every fence this list's catalog data supports, in place.

    Returns a count per rule, for the report.
    """
    filled: Dict[str, int] = {}
    for system in favorite.systems:
        groups = [list(system.departments)]
        groups.extend(list(site.departments) for site in system.sites)
        for departments in groups:
            sisters = [d for d in departments if d.lat is not None and d.lon is not None]
            for department in departments:
                fence = fence_for(favorite, system, department, sisters=sisters, statewide=statewide)
                if fence is None:
                    continue
                department.lat = round(fence.lat, 6)
                department.lon = round(fence.lon, 6)
                department.range_miles = fence.radius_miles
                department.fence_source = fence.source
                if not department.shape:
                    department.shape = "Circle"
                key = fence.source.split(":")[0]
                filled[key] = filled.get(key, 0) + 1
    return filled


def locate_departments(
    favorites: Iterable[FavoritesList], *, statewide: bool = True
) -> Tuple[List[FavoritesList], Dict[str, int]]:
    """Every list with its departments' fences filled in, and a count per rule.

    The lists are modified in place: this runs on already-generated copies
    (:func:`wasds150.fleet.service.scanner_favorites`,
    :func:`wasds150.plan.service.resolve_named_plan`), never on the operator's
    stored catalog.
    """
    lists = list(favorites)
    totals: Dict[str, int] = {}
    for favorite in lists:
        for key, count in locate_favorite(favorite, statewide=statewide).items():
            totals[key] = totals.get(key, 0) + count
    return lists, totals
