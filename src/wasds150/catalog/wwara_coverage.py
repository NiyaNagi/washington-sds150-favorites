"""WWARA repeaters in the county and city lists their coverage names.

WWARA publishes each repeater's coverage (the extract's ``LOCALE``): a county
(``SNOHOMISH COUNTY-NORTH``), a city (``REDMOND``) or a region (``PUGET
SOUND-SOUTH``). PSHAM01 holds every record by region. This puts a copy of
each machine whose coverage names a county or a city into that county's
RadioReference list (``RRC-*``) and, for a King County city, its ``KC`` local
list: a county list is otherwise limited to the few repeaters RadioReference
happens to carry (Pierce County had one of WWARA's eight). Regional machines
stay in PSHAM01 alone. The copies are rebuilt whenever a catalog is loaded,
so they follow each WWARA refresh.
"""
from __future__ import annotations

import copy
import re
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

from wasds150.catalog.puget_ham import COVERAGE_NOTE, WWARA_SYSTEM_ID
from wasds150.catalog.wa_counties import county_point
from wasds150.models.catalog import Catalog, Channel, Department, System
from wasds150.util.hashing import stable_id

#: A city or area coverage -> (its county, the King County city it names).
COVERAGE_PLACES: Dict[str, Tuple[str, Optional[str]]] = {
    "SEATTLE": ("King", "Seattle"),
    "REDMOND": ("King", "Redmond"),
    "KIRKLAND": ("King", "Kirkland"),
    "RENTON": ("King", "Renton"),
    "SHORELINE": ("King", "Shoreline"),
    "MAPLE VALLEY": ("King", "Maple Valley"),
    "FEDERAL WAY": ("King", "Federal Way"),
    "SNOQUALMIE VALLEY": ("King", None),
    "VASHON ISLAND": ("King", None),
    "EVERETT": ("Snohomish", None),
    "MONROE": ("Snohomish", None),
    "SNOHOMISH": ("Snohomish", None),
    "TACOMA": ("Pierce", None),
    "EATONVILLE": ("Pierce", None),
    "BREMERTON": ("Kitsap", None),
    "BAINBRIDGE ISLAND": ("Kitsap", None),
    "BLAINE": ("Whatcom", None),
    "MT VERNON": ("Skagit", None),
    "WHIDBEY ISLAND": ("Island", None),
    "SAN JUAN ISLANDS": ("San Juan", None),
    "SEQUIM": ("Clallam", None),
    "PORT ANGELES": ("Clallam", None),
    "FORKS": ("Clallam", None),
    "OLYMPIA": ("Thurston", None),
    "CHEHALIS VALLEY": ("Lewis", None),
    "LONGVIEW": ("Cowlitz", None),
    "WOODLAND": ("Cowlitz", None),
}
_COUNTY = re.compile(r"^(.+?)\s*COUN?T?Y\b")
#: The system holding a list's copies. The SDS150's Near Me lists skip it:
#: they already take every WWARA machine from PSHAM01, located.
COVERAGE_SYSTEM_LABEL = "WWARA Coordinated Repeaters"
#: Modes a county copy carries. DMR and NXDN stay in PSHAM01: a county list's
#: digital rows feed the transceivers' business-digital block.
_MODES = frozenset({"FM", "NFM", "P25"})


def coverage_of(notes: str) -> str:
    for part in (notes or "").split("; "):
        if part.startswith(COVERAGE_NOTE):
            return part[len(COVERAGE_NOTE):]
    return ""


def place_for(coverage: str) -> Optional[Tuple[str, Optional[str]]]:
    """``(county, King County city or None)`` for a coverage naming one, else
    ``None`` (a region, a link, or an area spanning counties)."""
    text = re.sub(r"\s+", " ", (coverage or "").upper().replace(" .", ".")).strip()
    if text in COVERAGE_PLACES:
        return COVERAGE_PLACES[text]
    match = _COUNTY.match(text)
    if not match:
        return None
    county = " ".join(word.capitalize() for word in match.group(1).split())
    return (county, None) if county_point(county) is not None else None


def _county_key(county: str) -> str:
    from wasds150.recipes.rr_county import county_key

    return county_key(county).upper()


def place_wwara_repeaters(catalog: Catalog) -> int:
    """Rebuild the WWARA copies in every county and city list. Returns how many
    copies were placed."""
    by_key = {favorite.favorite_key.upper(): favorite for favorite in catalog.favorites}
    city_lists = {
        favorite.favorite_name[: -len(" Local")].upper(): favorite.favorite_key.upper()
        for favorite in catalog.favorites
        if favorite.favorite_key.upper().startswith("KC") and favorite.favorite_name.endswith(" Local")
    }
    targets: Dict[str, "OrderedDict[Tuple[str, str], List[Channel]]"] = {}
    psham = by_key.get("PSHAM01")
    for system in (psham.systems if psham is not None else []):
        if system.id != WWARA_SYSTEM_ID:
            continue
        for department in system.departments:
            if department.avoid:
                continue
            group = department.label.split(" - ", 1)[-1]
            for channel in department.channels:
                if channel.avoid or (channel.mode or "").upper() not in _MODES:
                    continue
                place = place_for(coverage_of(channel.notes))
                if place is None:
                    continue
                county, city = place
                keys = [_county_key(county)]
                if city is not None and city.upper() in city_lists:
                    keys.append(city_lists[city.upper()])
                for key in keys:
                    if key in by_key:
                        targets.setdefault(key, OrderedDict()).setdefault((county, group), []).append(channel)

    placed = 0
    for favorite in catalog.favorites:
        key = favorite.favorite_key.upper()
        system_id = stable_id(f"wwara-coverage:{key}", kind="system")
        favorite.systems = [system for system in favorite.systems if system.id != system_id]
        groups = targets.get(key)
        if not groups:
            continue
        departments = []
        for (county, group), channels in groups.items():
            point = county_point(county)
            departments.append(Department(
                id=stable_id(f"wwara-coverage:{key}:{group}", kind="department"),
                label=f"WWARA {group}"[:64],
                channels=[copy.deepcopy(c) for c in sorted(channels, key=lambda c: (c.freq_mhz or 0.0, c.label))],
                lat=point.lat if point else None,
                lon=point.lon if point else None,
                range_miles=point.radius_miles if point else None,
                shape="Circle" if point else "",
            ))
            placed += len(channels)
        favorite.systems.append(System(id=system_id, label=COVERAGE_SYSTEM_LABEL, departments=departments))
    return placed
