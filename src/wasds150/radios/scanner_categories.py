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

A list that mixes services is split by service first (:data:`SPLIT_BY_SERVICE`):
the operator's FTX-1 import is 731 channels of which all but 21 are already
in other lists, so it has no list of its own - its amateur rows join HAM
Repeaters, its marine rows MAR Marine & USCG and the rest BIZ Business/Util,
where the merge keeps only what those lists lack.
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
from wasds150.radios.services import AMATEUR, service_for
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
    # Amateur. FTX01 is split by service (SPLIT_BY_SERVICE); it is listed
    # here so its amateur rows rank after the coordinated lists'.
    # The registry leads: first to carry a station names it.
    Category("HAM-RPT", "HAM Repeaters", 50, ("HAMREG", "PSHAM01", "PSHAM02", "FL60", "BAND03", "FTX01")),
    Category("HAM-DMR", "HAM DMR Networks", 51, ("DMRNET", "BMNET")),
    Category("HAM-NETS", "HAM ARES & Nets", 52, ("FL61", "FL62", "SEAACS")),
    Category("HAM-CALL", "HAM Simplex & Sats", 53, ("FL63", "HAM01", "FL51")),
    Category("HAM-HF", "HAM HF Nets", 54, ("HFNET01",)),
    # Personal radio, business and events.
    Category("BIZ-PERS", "BIZ GMRS FRS MURS", 60, ("GMRS01", "FL65", "FL66", "BAND06")),
    Category("BIZ", "BIZ Business/Util", 61, ("FL68", "FL69", "FL15", "BAND12", "FCCDIG")),
    Category("BIZ-EVENT", "BIZ Events & Media", 62, ("FL73", "FL74a")),
)
CATEGORY_BY_KEY: Dict[str, Category] = {category.key: category for category in CATEGORIES}

#: Lists that mix services, split channel by channel before merging:
#: list key -> ((service, category key), ...). A service is ``amateur``,
#: ``marine`` or ``other``.
SPLIT_BY_SERVICE: Dict[str, Tuple[Tuple[str, str], ...]] = {
    "FTX01": (("amateur", "HAM-RPT"), ("marine", "MAR"), ("other", "BIZ")),
}

#: Names of category lists an earlier install wrote that no longer exist, so
#: the install removes them.
RETIRED_NAMES = frozenset({"HAM FTX-1 Import"})

#: Marine VHF, ship and shore channels (MHz).
_MARINE = (156.0, 162.1)


def _norm(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


_BY_MEMBER: Dict[str, Category] = {m.casefold(): c for c in CATEGORIES for m in c.members}
_BY_COUNTY: Dict[str, Category] = {_norm(county): c for c in CATEGORIES for county in c.counties}
_RADIOREFERENCE_COUNTY = re.compile(r"^RR[CT]-(.+)$", re.IGNORECASE)


def category_for(favorite_key: str) -> Optional[Category]:
    """The category a catalog list is merged into, or ``None``. A list split
    by service answers with the category its amateur rows go to."""
    key = favorite_key.strip()
    found = _BY_MEMBER.get(key.casefold())
    if found is not None:
        return found
    match = _RADIOREFERENCE_COUNTY.match(key)
    return _BY_COUNTY.get(_norm(match.group(1))) if match else None


def is_retired_name(user_name: str) -> bool:
    """Whether an installed list is one an earlier install wrote that this
    one supersedes: under a catalog key a category now holds (``"FL01 - WA
    SAR & Mutual Aid"``), or a category list that no longer exists. Lists
    the operator named themselves never match."""
    if user_name in RETIRED_NAMES:
        return True
    key, separator, _rest = user_name.partition(" - ")
    return bool(separator) and category_for(key) is not None


def _service_kind(channel: Channel) -> str:
    freq = channel.freq_mhz
    if freq is None:
        return "other"
    if service_for(freq) == AMATEUR:
        return "amateur"
    if _MARINE[0] <= freq <= _MARINE[1]:
        return "marine"
    return "other"


def _split_by_service(favorite: FavoritesList) -> List[Tuple[Category, FavoritesList]]:
    parts: List[Tuple[Category, FavoritesList]] = []
    for kind, category_key in SPLIT_BY_SERVICE[favorite.favorite_key.upper()]:
        part = copy.deepcopy(favorite)
        for system in part.systems:
            for department in system.departments:
                department.channels = [c for c in department.channels if _service_kind(c) == kind]
            system.departments = [d for d in system.departments if d.channels]
            system.sites = [] if kind != "other" else system.sites
        part.systems = [s for s in part.systems if s.departments or s.sites]
        if part.systems:
            parts.append((CATEGORY_BY_KEY[category_key], part))
    return parts


def compact_lists(favorites: Sequence[FavoritesList]) -> List[FavoritesList]:
    """The Near Me lists, then one list per populated category in quick-key
    order, then any list no category names, unchanged."""
    near_me = [f for f in favorites if f.favorite_key in NEAR_ME_NAMES]
    grouped: Dict[str, List[FavoritesList]] = {}
    passthrough: List[FavoritesList] = []
    for favorite in favorites:
        if favorite.favorite_key in NEAR_ME_NAMES:
            continue
        if favorite.favorite_key.upper() in SPLIT_BY_SERVICE:
            for category, part in _split_by_service(favorite):
                grouped.setdefault(category.key, []).append(part)
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
    from wasds150.radios.near_me import NEVER_MONITOR

    settings = near_me_list_settings(favorites)
    for favorite in favorites:
        key = favorite.favorite_key
        if key in NEAR_ME_NAMES:
            settings[key] = replace(settings[key], name=NEAR_ME_NAMES[key])
        elif key in CATEGORY_BY_KEY:
            category = CATEGORY_BY_KEY[key]
            # Monitored, because Select Lists to Monitor is the gate a quick
            # key cannot open: installed with it off, this category's quick
            # key does nothing but beep. See near_me.list_settings.
            settings[key] = ListSettings(
                monitor=key not in NEVER_MONITOR,
                quick_key=category.quick_key,
                lead=True,
                name=category.name,
            )
    return settings


def _in_priority_order(category: Category, lists: List[FavoritesList]) -> List[FavoritesList]:
    rank = {member.casefold(): index for index, member in enumerate(category.members)}
    return sorted(lists, key=lambda f: rank.get(f.favorite_key.casefold(), len(rank)))


#: Modes a scanner demodulates the same way; copies in any of them are one channel.
_ANALOG_FM = frozenset({"", "FM", "NFM", "FMN", "AUTO", "ALL"})


def _channel_key(channel: Channel) -> tuple:
    """One scanner channel. Analog FM copies of a frequency are the same
    channel whatever mode or tone text a list gave them - the scanner hears
    the frequency either way; a digital channel's colour code, NAC, RAN or
    talkgroup does tell two apart."""
    if channel.freq_mhz is None:
        return ("id", channel.id)
    mode = (channel.mode or "").upper()
    if mode in _ANALOG_FM and channel.dmr_talkgroup is None and channel.nxdn_ran is None:
        return (round(channel.freq_mhz, 5), "FM")
    return (
        round(channel.freq_mhz, 5), mode, channel.tone or "",
        channel.dmr_talkgroup, channel.dmr_timeslot, channel.nxdn_ran,
    )


def _drop_repeats(departments: List[Department], seen: Dict[tuple, Channel]) -> None:
    for department in departments:
        kept = []
        for channel in department.channels:
            if (channel.mode or "").upper() == "DV":
                continue  # D-STAR: the scanner cannot decode it (the registry carries these)
            key = _channel_key(channel)
            first = seen.get(key)
            if first is None:
                seen[key] = channel
                kept.append(channel)
            elif len(key) == 2 and (first.tone or "") != (channel.tone or ""):
                # Copies disagree on the tone: open squelch hears every machine.
                first.tone = ""
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
    seen: Dict[tuple, Channel] = {}
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
    # Every list reads in frequency order within each department.
    for system in systems:
        for department in system.departments:
            department.channels.sort(key=lambda c: (c.freq_mhz if c.freq_mhz is not None else 0.0, c.label))
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
