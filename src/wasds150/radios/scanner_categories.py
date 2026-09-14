"""Compact, category-named Favorites Lists for the SDS150.

The scanner shows about 18 characters of a list's name, so the catalog's
"FL01 - WA SAR & Mutual Aid" reads "FL01 - WA SAR & Mu", and 169 lists are a
long scroll. Many of them are copies of each other: the 39 King County city
lists hold the same PSERN system, and the county RadioReference lists repeat
the regional ones. After the Near Me lists are built
(:mod:`wasds150.radios.near_me`), every other list is merged into a category
named with a short category word first ("PS King County", "HAM Repeaters")
and given a quick key in its category's decade:

=====  ==============================================
1-6    NM: Near Me
10s    PS: public safety by region, statewide, encrypted
20s    OUT: wildfire, mountains, trips, weather
30s    AIR, MIL, MED
40s    MAR, RAIL, TRAN
50s    HAM
60s    BIZ
=====  ==============================================

Merging keeps every station once. A trunked system that several lists carry
becomes one system with the union of their sites and talkgroups, and a
conventional frequency already in the category is not repeated. A list no
category names is installed as it is, so a new catalog list never goes
missing. The catalog keeps its own keys: only what reaches the scanner
changes.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, replace
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from wasds150.hpe.flist import ListSettings
from wasds150.models.catalog import ORIGIN_LOCAL, Channel, Department, FavoritesList, Site, System
from wasds150.models.provenance import Provenance
from wasds150.radios.near_me import NEAR_ME
from wasds150.radios.near_me import list_settings as near_me_list_settings
from wasds150.util.hashing import stable_id

#: How many characters of a list name the scanner's list view shows.
DISPLAY_WIDTH = 18


@dataclass(frozen=True)
class Category:
    key: str
    #: The name the scanner shows, at most :data:`DISPLAY_WIDTH` characters.
    name: str
    quick_key: int
    #: Catalog list keys merged into this category, in priority order: the
    #: first list to carry a station names it.
    members: Tuple[str, ...] = ()
    #: Counties whose RadioReference lists (``RRC-``/``RRT-``) belong here.
    counties: Tuple[str, ...] = ()


def _numbered(prefix: str, first: int, last: int) -> Tuple[str, ...]:
    return tuple(f"{prefix}{n:02d}" for n in range(first, last + 1))


NEAR_ME_NAMES: Dict[str, str] = {spec.key: f"NM {spec.name}" for spec in NEAR_ME}

CATEGORIES: Tuple[Category, ...] = (
    # Public safety, by region: the curated system, then the county's
    # RadioReference conventional and trunked lists.
    Category("PS-KING", "PS King County", 10, ("FL09a",) + _numbered("KC", 1, 39) + ("LA01", "LA17"), ("King",)),
    Category("PS-SNO", "PS Snohomish", 11, ("FL10",), ("Snohomish",)),
    Category("PS-PIERCE", "PS Pierce", 12, ("FL11",), ("Pierce",)),
    Category("PS-SOUTH", "PS South Sound", 13, ("FL12", "FL13", "FL19"),
             ("Thurston", "Mason", "Lewis", "Grays Harbor", "Pacific", "Wahkiakum", "Cowlitz", "Clark", "Skamania")),
    Category("PS-OLY", "PS Kitsap/Olympic", 14, ("FL14", "FL18"), ("Kitsap", "Jefferson", "Clallam")),
    Category("PS-NORTH", "PS North Sound", 15, ("FL16", "FL17"), ("Skagit", "Island", "San Juan", "Whatcom")),
    Category("PS-EAST", "PS Eastern WA", 16,
             ("FL20a", "FL21", "FL22", "FL23", "FL24", "FL25a", "FL26", "FL27", "FL28", "FL29", "FL30"),
             ("Chelan", "Douglas", "Okanogan", "Ferry", "Stevens", "Pend Oreille", "Spokane", "Lincoln", "Adams",
              "Grant", "Kittitas", "Yakima", "Klickitat", "Benton", "Franklin", "Walla Walla", "Columbia",
              "Garfield", "Asotin", "Whitman")),
    Category("PS-STATE", "PS Statewide", 17, ("FL01", "FL02", "FL03", "FL04", "BAND07", "RRWA", "RRT-WA")),
    Category("PS-ENC", "PS Encrypted", 18, ("FL08", "FL09b", "FL20b", "FL25b", "FL50b")),
    # Outdoors.
    Category("OUT-FIRE", "OUT Wildfire", 20, ("FL06", "FL07", "BAND09")),
    Category("OUT-WEST", "OUT West Mountains", 21, ("FL32", "FL33", "FL34", "FL35", "FL37", "FL38", "FL39")),
    Category("OUT-EAST", "OUT East Mountains", 22, ("FL36", "FL40", "FL41", "FL42", "FL43")),
    Category("OUT-ALL", "OUT WA Safety All", 23, ("OUT01",)),
    Category("OUT-LENA", "OUT Upper Lena", 24, ("UL00", "UL01", "UL02", "UL03")),
    Category("OUT-OZETTE", "OUT Lake Ozette", 25, ("OZ01",)),
    Category("OUT-WX", "OUT Weather/SAR", 26, ("FL75", "BAND08")),
    # Air, military, medical.
    Category("AIR-CIVIL", "AIR Civil & ATC", 30, ("FAAAIR", "FL46", "FL47", "FL48", "BAND01")),
    Category("AIR-SAR", "AIR SAR & Medevac", 31, ("FL44", "FL55")),
    Category("MIL", "MIL Air & Ground", 32, ("FL49", "BAND02", "FL50a", "FL59")),
    Category("MED", "MED EMS & Hospital", 33, ("FL71", "FL70b", "BAND10")),
    # Marine, rail, roads and transit.
    Category("MAR", "MAR Marine & USCG", 40, ("FL52", "FL54", "BAND04")),
    Category("MAR-FERRY", "MAR Ferries & VTS", 41, ("FL53",)),
    Category("RAIL", "RAIL Freight Rail", 42, ("FL56", "FL57", "BAND05")),
    Category("TRAN", "TRAN Transit", 43, ("FL58", "FL70a")),
    Category("TRAN-ROAD", "TRAN Roads & WSDOT", 44, ("FL05", "FL74b", "BAND11")),
    # Amateur.
    Category("HAM-RPT", "HAM Repeaters", 50, ("PSHAM01", "PSHAM02", "FL60", "BAND03")),
    Category("HAM-DMR", "HAM DMR Networks", 51, ("DMRNET", "BMNET")),
    Category("HAM-NETS", "HAM ARES & Nets", 52, ("FL61", "FL62", "SEAACS")),
    Category("HAM-CALL", "HAM Simplex & Sats", 53, ("FL63", "HAM01", "FL51")),
    Category("HAM-HF", "HAM HF Nets", 54, ("HFNET01",)),
    Category("HAM-FTX", "HAM FTX-1 Import", 55, ("FTX01",)),
    # Personal radio, business and events.
    Category("BIZ-PERS", "BIZ GMRS FRS MURS", 60, ("GMRS01", "FL65", "FL66", "BAND06")),
    Category("BIZ", "BIZ Business/Util", 61, ("FL68", "FL69", "FL15", "BAND12", "FCCDIG")),
    Category("BIZ-EVENT", "BIZ Events & Media", 62, ("FL73", "FL74a")),
)
CATEGORY_BY_KEY: Dict[str, Category] = {category.key: category for category in CATEGORIES}


def _norm(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


_BY_MEMBER: Dict[str, Category] = {m.casefold(): c for c in CATEGORIES for m in c.members}
_BY_COUNTY: Dict[str, Category] = {_norm(county): c for c in CATEGORIES for county in c.counties}
_RADIOREFERENCE_COUNTY = re.compile(r"^RR[CT]-(.+)$", re.IGNORECASE)


def category_for(favorite_key: str) -> Optional[Category]:
    """The category a catalog list is merged into, or ``None``."""
    key = favorite_key.strip()
    found = _BY_MEMBER.get(key.casefold())
    if found is not None:
        return found
    match = _RADIOREFERENCE_COUNTY.match(key)
    return _BY_COUNTY.get(_norm(match.group(1))) if match else None


def is_retired_name(user_name: str) -> bool:
    """Whether an installed list is one an earlier install wrote under a
    catalog key (``"FL01 - WA SAR & Mutual Aid"``) that a category now
    holds. Lists the operator named themselves never match."""
    key, separator, _rest = user_name.partition(" - ")
    return bool(separator) and category_for(key) is not None


def compact_lists(favorites: Sequence[FavoritesList]) -> List[FavoritesList]:
    """The Near Me lists, then one list per populated category in quick-key
    order, then any list no category names, unchanged."""
    near_me = [f for f in favorites if f.favorite_key in NEAR_ME_NAMES]
    grouped: Dict[str, List[FavoritesList]] = {}
    passthrough: List[FavoritesList] = []
    for favorite in favorites:
        if favorite.favorite_key in NEAR_ME_NAMES:
            continue
        category = category_for(favorite.favorite_key)
        if category is None:
            passthrough.append(favorite)
        else:
            grouped.setdefault(category.key, []).append(favorite)
    merged = [
        _merge(category, _in_priority_order(category, grouped[category.key]))
        for category in sorted(CATEGORIES, key=lambda c: c.quick_key)
        if category.key in grouped
    ]
    return near_me + [m for m in merged if m.systems] + passthrough


def list_settings(favorites: Sequence[FavoritesList]) -> Dict[str, ListSettings]:
    """Scanner settings for every list being installed: Near Me as
    :func:`wasds150.radios.near_me.list_settings` has it, under its short
    name; each category after it on its quick key, unmonitored; anything
    else unmonitored under its catalog name."""
    settings = near_me_list_settings(favorites)
    for favorite in favorites:
        key = favorite.favorite_key
        if key in NEAR_ME_NAMES:
            settings[key] = replace(settings[key], name=NEAR_ME_NAMES[key])
        elif key in CATEGORY_BY_KEY:
            category = CATEGORY_BY_KEY[key]
            settings[key] = ListSettings(monitor=False, quick_key=category.quick_key, lead=True, name=category.name)
    return settings


def _in_priority_order(category: Category, lists: List[FavoritesList]) -> List[FavoritesList]:
    rank = {member.casefold(): index for index, member in enumerate(category.members)}
    return sorted(lists, key=lambda f: rank.get(f.favorite_key.casefold(), len(rank)))


def _channel_key(channel: Channel) -> tuple:
    if channel.freq_mhz is None:
        return ("id", channel.id)
    return (
        round(channel.freq_mhz, 5), (channel.mode or "").upper(), channel.tone or "",
        channel.dmr_talkgroup, channel.dmr_timeslot, channel.nxdn_ran,
    )


def _drop_repeats(departments: List[Department], seen: Set[tuple]) -> None:
    for department in departments:
        kept = []
        for channel in department.channels:
            key = _channel_key(channel)
            if key not in seen:
                seen.add(key)
                kept.append(channel)
        department.channels = kept
    departments[:] = [d for d in departments if d.channels]


def _trunk_key(system: System) -> tuple:
    if system.sid is None:
        return ("id", system.id)
    return (system.tech or "", system.sid, (system.wacn or "").upper())


def _site_key(site: Site) -> tuple:
    return (
        site.label.casefold(),
        round(site.lat, 4) if site.lat is not None else None,
        round(site.lon, 4) if site.lon is not None else None,
    )


def _merge_trunk(target: System, source: System) -> None:
    sites = {_site_key(site): site for site in target.sites}
    for site in source.sites:
        existing = sites.get(_site_key(site))
        if existing is None:
            target.sites.append(site)
            sites[_site_key(site)] = site
            continue
        heard = {c.tgid for d in existing.departments for c in d.channels}
        groups = {d.label.casefold(): d for d in existing.departments}
        for department in site.departments:
            fresh = [c for c in department.channels if c.tgid not in heard]
            heard.update(c.tgid for c in fresh)
            if not fresh:
                continue
            group = groups.get(department.label.casefold())
            if group is None:
                department.channels = fresh
                existing.departments.append(department)
                groups[department.label.casefold()] = department
            else:
                group.channels.extend(fresh)
    known = {(f.lcn, f.freq_mhz) for f in target.trunk_frequencies}
    target.trunk_frequencies.extend(f for f in source.trunk_frequencies if (f.lcn, f.freq_mhz) not in known)
    target.departments.extend(source.departments)


def _joined(values: Iterable[str]) -> str:
    unique: List[str] = []
    for value in values:
        if value and value not in unique:
            unique.append(value)
    return "; ".join(unique)


def _merge(category: Category, lists: List[FavoritesList]) -> FavoritesList:
    seen: Set[tuple] = set()
    trunks: Dict[tuple, System] = {}
    systems: List[System] = []
    for favorite in lists:
        for original in favorite.systems:
            system = copy.deepcopy(original)
            _drop_repeats(system.departments, seen)
            if system.sites:
                existing = trunks.get(_trunk_key(system))
                if existing is not None:
                    _merge_trunk(existing, system)
                    continue
                trunks[_trunk_key(system)] = system
            elif not system.departments:
                continue
            systems.append(system)
    channels = sum(len(d.channels) for s in systems for d in s.departments)
    talkgroups = sum(len(d.channels) for s in systems for site in s.sites for d in site.departments)
    return FavoritesList(
        id=stable_id(f"scanner-category:{category.key}"),
        slug=category.key.lower(),
        favorite_key=category.key,
        favorite_name=category.name,
        region=_joined(f.region for f in lists),
        counties=_joined(f.counties for f in lists),
        scenario=f"Quick key {category.quick_key}",
        source_type="Merged for the scanner",
        system_or_category=", ".join(f.favorite_key for f in lists),
        sites_or_coverage=_joined(f.sites_or_coverage for f in lists),
        departments_or_channels=f"{channels} conventional channels, {talkgroups} talkgroups",
        mode=_joined(f.mode for f in lists),
        monitorability=_joined(f.monitorability for f in lists),
        upgrade_required=_joined(f.upgrade_required for f in lists),
        source_url=_joined(f.source_url for f in lists),
        notes="Merged from " + ", ".join(f"{f.favorite_key} ({f.favorite_name})" for f in lists),
        enabled=True,
        reference_only=any(f.reference_only for f in lists),
        licensed=any(f.licensed for f in lists),
        origin=ORIGIN_LOCAL,
        systems=systems,
        provenance=[Provenance(source_adapter="scanner_categories", confidence="derived")],
    )
