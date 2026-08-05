"""Conservative public-intent curation for King County local lists.

Rules contain public agency/service words and Census place coordinates only.
They never contain frequencies, talkgroup IDs, site IDs, or copied HPDB data.
Unmatched content is excluded rather than inferred.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Dict, List, Tuple

from wasds150.catalog.ames_lake import (
    AMES_LAKE_LAT,
    AMES_LAKE_LON,
    KING_COUNTY_CITIES,
)
from wasds150.models.catalog import Department, FavoritesList, System


@dataclass(frozen=True)
class LocalAreaRule:
    lat: float
    lon: float
    range_miles: float
    direct_departments: Tuple[str, ...] = ()
    kcso_dispatch: Tuple[str, ...] = ()
    norcom_law_terms: Tuple[str, ...] = ()
    hospital_terms: Tuple[str, ...] = ()
    fire_dispatch: str = "norcom"
    extra_channel_terms: Tuple[str, ...] = ()
    regional: bool = False


RULES: Dict[str, LocalAreaRule] = {
    key: LocalAreaRule(
        spec.lat,
        spec.lon,
        spec.range_miles,
        spec.direct_departments,
        spec.kcso_dispatch,
        spec.norcom_law_terms,
        spec.hospital_terms,
        spec.fire_dispatch,
        spec.extra_channel_terms,
    )
    for key, spec in KING_COUNTY_CITIES.items()
}
RULES["LA01"] = LocalAreaRule(
    AMES_LAKE_LAT, AMES_LAKE_LON, 22,
    ("Redmond", "Woodinville", "Duval"),
    ("North",),
    (),
    ("Overlake", "Evergreen", "Snoqualmie Valley"),
)
RULES["LA17"] = LocalAreaRule(
    AMES_LAKE_LAT, AMES_LAKE_LON, 35,
    ("Bellevue", "Bothell", "Duval", "Issaquah", "Kirkland", "Redmond", "Renton", "Snoqualmie", "Woodinville"),
    ("North", "Southeast", "Southwest"),
    ("Bellevue", "Bothell", "Issaquah", "Kirkland", "Redmond", "Renton", "Snoqualmie"),
    ("Overlake", "Evergreen", "Snoqualmie Valley", "Valley Medical"),
    "valley",
    (),
    True,
)

_SHARED_KING_TERMS = (
    "AMR", "Emergency", "Incident", "Interop", "Mutual Aid", "Public Safety",
    "Fire", "Public Health",
)
_NORCOM_CLEAR_TERMS = ("Fire", "Ambulance", "Truck")
_VALLEY_CLEAR_TERMS = ("Fire", "Ambulance", "Operations")
_TRANSIT_CLEAR_TERMS = ("Operations", "Maintenance", "Administration", "Safety", "Yard", "Command")
_LAW_TERMS = (
    "Police", "Sheriff", "Narcotic", "Investigation", "Court", "Jail", "Data",
    "Special", "Law", "Security",
)
_LAW_DEPARTMENTS = ("King County Sheriff", "Seattle Police", "Sumner")


def _contains_any(value: str, terms: Tuple[str, ...]) -> bool:
    lowered = value.casefold()
    return any(term.casefold() in lowered for term in terms)


def _is_law(department: str, channel: str) -> bool:
    if department in _LAW_DEPARTMENTS:
        return True
    if _contains_any(channel, _LAW_TERMS):
        return True
    return "tactical" in channel.casefold() and "fire" not in channel.casefold()


def _include_channel(rule: LocalAreaRule, department: str, channel: str) -> bool:
    if _contains_any(channel, rule.extra_channel_terms):
        return True
    if department in rule.direct_departments:
        if department == "Snoqualmie" and not _contains_any(channel, ("Snoqualmie", "Issaquah", "Fire")):
            return False
        if department == "Sumner" and not _contains_any(channel, rule.extra_channel_terms):
            return False
        return True
    if department == "NORCOM" and rule.fire_dispatch == "norcom":
        return _contains_any(channel, _NORCOM_CLEAR_TERMS + rule.norcom_law_terms)
    if department == "NORCOM" and rule.norcom_law_terms:
        return _contains_any(channel, rule.norcom_law_terms)
    if department == "King County Sheriff":
        return _contains_any(channel, rule.kcso_dispatch)
    if department == "King County":
        return _contains_any(channel, _SHARED_KING_TERMS + rule.extra_channel_terms)
    if department == "Hospital":
        return _contains_any(channel, rule.hospital_terms + ("Hospital Common", "Helicopter EMS"))
    if department == "Valley Communications" and rule.fire_dispatch == "valley":
        return _contains_any(channel, _VALLEY_CLEAR_TERMS)
    if department == "Sound Transit" and rule.regional:
        return _contains_any(channel, _TRANSIT_CLEAR_TERMS) and not _contains_any(channel, ("Police", "Security"))
    return False


def _located_department(source: Department, channels: list, rule: LocalAreaRule, *, encrypted: bool) -> Department:
    department = copy.deepcopy(source)
    department.channels = channels
    department.lat = rule.lat
    department.lon = rule.lon
    department.range_miles = rule.range_miles
    department.shape = "Circle"
    if encrypted:
        department.id = f"{department.id}:encrypted"
        department.label = f"[E]-ENCRYPTED {department.label}"
        department.encrypted_bucket = True
        department.avoid = True
    return department


def curate_local_area_systems(favorite: FavoritesList, systems: List[System]) -> List[System]:
    rule = RULES.get(favorite.favorite_key)
    if rule is None:
        return systems
    curated_systems: List[System] = []
    for source_system in systems:
        system = copy.deepcopy(source_system)
        for site in system.sites:
            departments: List[Department] = []
            for source_department in site.departments:
                clear_channels = []
                law_channels = []
                for channel in source_department.channels:
                    if not _include_channel(rule, source_department.label, channel.label):
                        continue
                    (law_channels if _is_law(source_department.label, channel.label) else clear_channels).append(channel)
                if clear_channels:
                    departments.append(_located_department(source_department, clear_channels, rule, encrypted=False))
                if law_channels:
                    departments.append(_located_department(source_department, law_channels, rule, encrypted=True))
            site.departments = departments
        if any(site.departments for site in system.sites):
            curated_systems.append(system)
    return curated_systems
