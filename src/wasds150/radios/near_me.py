"""Near Me: the few SDS150 Favorites Lists that make the scanner worth
turning on the moment the car starts.

The catalog installs 160-odd lists. Monitored together they cycle through
some 16,000 conventional entries - nine in ten of them copies, most with no
location fence - so a pass takes minutes and short transmissions are missed
while the scanner is elsewhere. The Near Me lists are built from those same
lists with three rules:

* **Fenced.** Every department carries a location and range: its county,
  airport, or a cluster of located stations. A trunked system keeps its
  fenced sites. The lists are installed with location control on, so with
  GPS the scanner covers only what is around the car.
* **Once.** A frequency lives in one Near Me list - the first, in the order
  public safety, air, ham, tactical, rail & marine, business - and a DMR
  repeater is one entry rather than one per talkgroup (the SDS150 hears
  every talkgroup on it either way).
* **Live.** Encrypted, data and continuous broadcasts (ATIS, ASOS/AWOS,
  NOAA) are left out: the first cannot be heard, the last would hold the
  scan for good.

Public safety, air and ham are monitored when installed; tactical, rail &
marine and business are one quick key away; every other list is installed
unmonitored (:func:`list_settings`).
"""
from __future__ import annotations

import copy
import math
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from wasds150.catalog.labels import StationLabels, areas_overlap, station_key
from wasds150.hpe.flist import ListSettings
from wasds150.models.catalog import ORIGIN_LOCAL, Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.plan.resolve import service_rank
from wasds150.util.geo import haversine_miles
from wasds150.util.hashing import stable_id


@dataclass(frozen=True)
class NearMeList:
    key: str
    name: str
    quick_key: int
    monitor: bool
    #: How far a cluster of located stations is worth hearing.
    reach_miles: float
    #: Service type for rows that arrive without one, so the scanner's
    #: service-type buttons can mute the whole list.
    default_service: Optional[int] = None


PUBLIC_SAFETY = NearMeList("NM-PS", "Public Safety", 1, True, 25.0)
TACTICAL = NearMeList("NM-TAC", "Tactical", 2, False, 20.0)
AIR = NearMeList("NM-AIR", "Air", 3, True, 30.0, 15)
HAM = NearMeList("NM-HAM", "Ham", 4, True, 30.0, 13)
RAIL_MARINE = NearMeList("NM-RM", "Rail & Marine", 5, False, 20.0, 21)
BUSINESS = NearMeList("NM-BIZ", "Business & GMRS", 6, False, 15.0, 17)
NEAR_ME: Tuple[NearMeList, ...] = (PUBLIC_SAFETY, TACTICAL, AIR, HAM, RAIL_MARINE, BUSINESS)
NEAR_ME_KEYS = frozenset(spec.key for spec in NEAR_ME)
#: Which list keeps a frequency more than one would take: the ones that are
#: on by default first.
_CLAIM_ORDER = {spec.key: index for index, spec in enumerate((PUBLIC_SAFETY, AIR, HAM, TACTICAL, RAIL_MARINE, BUSINESS))}

_DISPATCH = frozenset({1, 2, 3, 4, 11, 29})
_TACTICAL = frozenset({6, 7, 8, 9, 12, 16, 22, 23, 24, 25, 30, 37})
_RAIL = frozenset({20, 26})
_BUSINESS = frozenset({14, 17, 21, 31, 32, 33, 34})
_HAM_LISTS = frozenset({"PSHAM01", "PSHAM02", "DMRNET", "BMNET", "SEAACS", "FL60", "FL61", "FL62", "FL63", "HAM01"})
#: Lists whose unlocated channels are worth scanning anywhere: the marine
#: and rail channel plans and itinerant business channels (opt-in lists).
_ANYWHERE_LISTS = {
    RAIL_MARINE.key: frozenset({"FL52", "FL53", "FL54", "FL56", "FL58"}),
    BUSINESS.key: frozenset({"FL68"}),
}
#: National FM calling channels a ham listens for wherever the car is.
_HAM_CALLING = (52.525, 146.52, 223.5, 446.0)
_MARINE = ((156.2475, 157.4250), (161.7750, 161.9625))
_NOAA = (162.3875, 162.5625)
_CONTINUOUS = re.compile(r"\b(ATIS|D-ATIS|ASOS|AWOS|METRO|VOLMET|NOAA|WX)\b", re.IGNORECASE)
_DATA = re.compile(r"\b(APRS|PACKET|WINLINK|DATA|TELEMETRY|SCADA|PAGING|PAGER|POCSAG|DGPS|EOT|HOT|VOT)\b", re.IGNORECASE)
#: A department fence up to this wide is specific enough to keep for a
#: located station; a wider one (a region) gives way to the station's own.
_TIGHT_FENCE_MILES = 35.0
#: Located stations are grouped in cells about 15 miles on a side.
_CELL_LAT, _CELL_LON = 0.22, 0.32


def _fenced(department: Optional[Department]) -> bool:
    return bool(department is not None and department.lat is not None and department.lon is not None and department.range_miles)


def _classify(favorite_key: str, channel: Channel) -> Optional[NearMeList]:
    service = channel.service_type
    freq = channel.freq_mhz or 0.0
    if favorite_key == "FAAAIR" or service == 15:
        return AIR
    if favorite_key in _HAM_LISTS or service == 13:
        return HAM
    if favorite_key in ("GMRS01", "FCCDIG"):
        return BUSINESS
    if any(low <= freq <= high for low, high in _MARINE) or service in _RAIL or favorite_key in ("FL56", "FL58"):
        return RAIL_MARINE
    if service in _DISPATCH:
        return PUBLIC_SAFETY
    if service in _TACTICAL:
        return TACTICAL
    if service in _BUSINESS or favorite_key == "FL68":
        return BUSINESS
    return None


def _talkgroup_class(channel: Channel) -> NearMeList:
    service = channel.service_type
    if service == 15:
        return AIR
    if service == 13:
        return HAM
    if service in _RAIL:
        return RAIL_MARINE
    if service in _DISPATCH:
        return PUBLIC_SAFETY
    if service in _BUSINESS:
        return BUSINESS
    # Tactical, talk-around and anything the database left untyped.
    return TACTICAL


def _live(channel: Channel) -> bool:
    if channel.avoid or channel.freq_mhz is None or channel.tgid is not None:
        return False
    if _NOAA[0] <= channel.freq_mhz <= _NOAA[1]:
        return False
    return not (_CONTINUOUS.search(channel.label or "") or _DATA.search(channel.label or ""))


def _placement(spec: NearMeList, favorite_key: str, department: Department, channel: Channel) -> Optional[tuple]:
    located = channel.lat is not None and channel.lon is not None
    if _fenced(department) and (department.range_miles <= _TIGHT_FENCE_MILES or not located):
        return ("fence", favorite_key, department.id)
    if located:
        return ("cell", round(channel.lat / _CELL_LAT), round(channel.lon / _CELL_LON))
    if spec is HAM and any(abs((channel.freq_mhz or 0.0) - calling) < 0.0006 for calling in _HAM_CALLING):
        return ("anywhere",)
    if favorite_key in _ANYWHERE_LISTS.get(spec.key, ()):
        return ("anywhere",)
    return None


def _prefix(favorite: FavoritesList) -> str:
    key = favorite.favorite_key
    if key.startswith("RRC-"):
        return key[4:].replace("-", " ").title()
    if key == "FAAAIR":
        return ""
    return key


def _common_suffix(labels: List[str]) -> str:
    words = [label.split() for label in labels]
    suffix: List[str] = []
    for column in zip(*(reversed(w) for w in words)):
        if len(set(column)) != 1:
            break
        suffix.insert(0, column[0])
    return " ".join(suffix)


@dataclass
class _Entry:
    spec: NearMeList
    place: tuple
    favorite: FavoritesList
    department: Department
    channel: Channel
    order: int
    #: Every label this station arrived under, for naming a DMR repeater.
    labels: List[str] = field(default_factory=list)
    #: Every tone it arrived with: copies that disagree get open squelch.
    tones: set = field(default_factory=set)


def _area(entry: _Entry) -> Optional[Tuple[float, float, float]]:
    """Where the entry is scanned: its fence, its cell, or anywhere (None)."""
    kind = entry.place[0]
    if kind == "fence":
        department = entry.department
        return (department.lat, department.lon, float(department.range_miles))
    if kind == "cell":
        return (entry.channel.lat, entry.channel.lon, entry.spec.reach_miles)
    return None


def _better(a: _Entry, b: _Entry) -> bool:
    """True when ``a`` should keep a frequency ``b`` also wants."""
    def rank(entry: _Entry) -> tuple:
        fence = entry.department.range_miles if entry.place[0] == "fence" else (0.0 if entry.place[0] == "cell" else math.inf)
        return (_CLAIM_ORDER[entry.spec.key], entry.place[0] == "anywhere", fence or 0.0, entry.order)
    return rank(a) < rank(b)


def _conventional(favorites: Sequence[FavoritesList], home: Optional[Tuple[float, float]]) -> Dict[str, List[Department]]:
    names = StationLabels(
        ((f.favorite_key, d, c) for f in favorites for s in f.systems for d in s.departments for c in d.channels),
        home=home,
    )
    # A frequency is a duplicate only where two copies would be scanned at
    # the same time: the same frequency in two counties is two stations.
    kept: "OrderedDict[tuple, List[_Entry]]" = OrderedDict()
    order = 0
    for favorite in favorites:
        for system in favorite.systems:
            for department in system.departments:
                for channel in department.channels:
                    order += 1
                    if not _live(channel):
                        continue
                    spec = _classify(favorite.favorite_key, channel)
                    if spec is None:
                        continue
                    place = _placement(spec, favorite.favorite_key, department, channel)
                    if place is None:
                        continue
                    key = station_key(channel) or (round(channel.freq_mhz, 5), (channel.mode or "").upper(), channel.tone or "")
                    entry = _Entry(spec, place, favorite, department, channel, order, [channel.label], {channel.tone or ""})
                    rivals = kept.setdefault(key, [])
                    for index, rival in enumerate(rivals):
                        if areas_overlap(_area(rival), _area(entry)):
                            rival.labels.append(channel.label)
                            rival.tones.add(channel.tone or "")
                            if _better(entry, rival):
                                entry.labels, entry.tones = rival.labels, rival.tones
                                rivals[index] = entry
                            break
                    else:
                        rivals.append(entry)

    groups: "OrderedDict[tuple, List[Tuple[tuple, _Entry]]]" = OrderedDict()
    for key, entries in kept.items():
        for entry in entries:
            groups.setdefault((entry.spec.key,) + entry.place, []).append((key, entry))

    result: Dict[str, List[Tuple[float, Department]]] = {}
    for group_key, members in groups.items():
        spec = members[0][1].spec
        place = group_key[1:]
        channels = []
        for key, entry in sorted(members, key=lambda item: (service_rank(item[1].channel.service_type), item[1].channel.freq_mhz)):
            channel = copy.deepcopy(entry.channel)
            if len(entry.labels) > 1 and (channel.mode or "").upper() == "DMR":
                # One entry per DMR repeater: name it for the repeater, not a talkgroup.
                channel.label = (_common_suffix(entry.labels) or channel.label)[:64]
            else:
                # The name every radio uses for this station.
                channel.label = names.label(entry.department, entry.channel)[:64]
            if len(entry.tones) > 1 and key[2] == "":
                # Two agencies' copies with different tones: open squelch hears both.
                channel.tone = ""
            if channel.service_type is None and spec.default_service is not None:
                channel.service_type = spec.default_service
            channel.id = stable_id(f"nearme:{spec.key}:{key}:{entry.place}", kind="channel")
            channels.append(channel)
        first = members[0][1]
        if place[0] == "fence":
            source = first.department
            prefix = _prefix(first.favorite)
            department = Department(
                id=stable_id(f"nearme:{spec.key}:{first.favorite.favorite_key}:{source.id}", kind="department"),
                label=(f"{prefix}: {source.label}" if prefix else source.label)[:64],
                channels=channels, lat=source.lat, lon=source.lon, range_miles=source.range_miles, shape=source.shape or "Circle",
            )
        elif place[0] == "cell":
            points = [(c.lat, c.lon) for c in channels if c.lat is not None and c.lon is not None]
            lat = sum(p[0] for p in points) / len(points)
            lon = sum(p[1] for p in points) / len(points)
            spread = max(haversine_miles(lat, lon, p[0], p[1]) for p in points)
            department = Department(
                id=stable_id(f"nearme:{spec.key}:cell:{place[1]}:{place[2]}", kind="department"),
                label=f"{spec.name} {lat:.2f}N {abs(lon):.2f}W",
                channels=channels, lat=round(lat, 6), lon=round(lon, 6),
                range_miles=round(spec.reach_miles + spread, 1), shape="Circle",
            )
        else:
            department = Department(
                id=stable_id(f"nearme:{spec.key}:anywhere", kind="department"),
                label=f"{spec.name} - Anywhere", channels=channels,
            )
        if department.lat is not None and home is not None:
            distance = haversine_miles(home[0], home[1], department.lat, department.lon)
        else:
            distance = math.inf
        result.setdefault(spec.key, []).append((distance, department))
    return {key: [d for _distance, d in sorted(rows, key=lambda row: row[0])] for key, rows in result.items()}


def _nearest_site(system: System, home: Optional[Tuple[float, float]]) -> float:
    if home is None:
        return 0.0
    return min(
        (haversine_miles(home[0], home[1], site.lat, site.lon) for site in system.sites if site.lat is not None and site.lon is not None),
        default=math.inf,
    )


def _merged_systems(favorites: Sequence[FavoritesList]) -> List[System]:
    """One copy of each trunked system: the fullest copy, plus any
    talkgroups another list's (curated) copy has that it lacks."""
    copies: "OrderedDict[object, List[System]]" = OrderedDict()
    for favorite in favorites:
        for system in favorite.systems:
            if system.sites:
                copies.setdefault(system.sid if system.sid is not None else system.id, []).append(system)
    merged: List[System] = []
    for group in copies.values():
        def talkgroups(system: System) -> int:
            return sum(len(d.channels) for site in system.sites for d in site.departments)
        base = copy.deepcopy(max(group, key=talkgroups))
        known = {c.tgid for site in base.sites for d in site.departments for c in d.channels}
        holder = next((site for site in base.sites if site.departments), base.sites[0])
        for other in group:
            for site in other.sites:
                for department in site.departments:
                    new = [c for c in department.channels if c.tgid is not None and c.tgid not in known]
                    if not new:
                        continue
                    target = next((d for d in holder.departments if d.label == department.label), None)
                    if target is None:
                        target = copy.deepcopy(department)
                        target.channels = []
                        holder.departments.append(target)
                    target.channels.extend(copy.deepcopy(new))
                    known.update(c.tgid for c in new)
        fenced = [s for s in base.sites if s.lat is not None and s.lon is not None and s.range_miles]
        if fenced:
            # An unfenced site would be scanned everywhere; keep one only if
            # it carries the talkgroups.
            base.sites = [s for s in base.sites if s in fenced or s.departments]
        merged.append(base)
    return merged


def _trunked(favorites: Sequence[FavoritesList], home: Optional[Tuple[float, float]]) -> Dict[str, List[System]]:
    result: Dict[str, List[Tuple[float, System]]] = {}
    for system in _merged_systems(favorites):
        distance = _nearest_site(system, home)
        for spec in NEAR_ME:
            part = copy.deepcopy(system)
            part.id = stable_id(f"nearme:{spec.key}:{system.id}", kind="system")
            kept = 0
            for site in part.sites:
                for department in site.departments:
                    department.channels = [
                        c for c in department.channels
                        if c.tgid is not None and not c.avoid and _talkgroup_class(c) is spec
                    ]
                    kept += len(department.channels)
                site.departments = [d for d in site.departments if d.channels]
            if kept:
                if home is not None:
                    part.sites.sort(key=lambda s: haversine_miles(home[0], home[1], s.lat, s.lon) if s.lat is not None else math.inf)
                result.setdefault(spec.key, []).append((distance, part))
    return {key: [s for _d, s in sorted(rows, key=lambda row: row[0])] for key, rows in result.items()}


def build_near_me_lists(
    favorites: Sequence[FavoritesList], home: Optional[Tuple[float, float]] = None
) -> List[FavoritesList]:
    """The Near Me lists built from ``favorites`` (the lists the scanner
    is loaded with), in quick-key order; a list with nothing in it is left
    out."""
    sources = [f for f in favorites if f.favorite_key not in NEAR_ME_KEYS]
    conventional = _conventional(sources, home)
    trunked = _trunked(sources, home)
    licensed = any(f.licensed for f in sources)
    lists: List[FavoritesList] = []
    for spec in NEAR_ME:
        systems = list(trunked.get(spec.key, []))
        departments = conventional.get(spec.key, [])
        if departments:
            systems.append(System(id=stable_id(f"nearme:{spec.key}:conventional", kind="system"),
                                  label=f"{spec.name} Conventional", departments=departments))
        if not systems:
            continue
        channels = sum(len(d.channels) for d in departments)
        talkgroups = sum(len(d.channels) for s in systems for site in s.sites for d in site.departments)
        lists.append(FavoritesList(
            id=stable_id(f"nearme:{spec.key}"),
            slug=spec.key.lower(),
            favorite_key=spec.key,
            favorite_name=spec.name,
            region="Around the scanner (location control)",
            counties="Wherever the scanner is",
            scenario="In the car: " + ("on at startup" if spec.monitor else f"quick key {spec.quick_key}"),
            source_type="Built from the installed lists",
            system_or_category=f"{len(systems) - (1 if departments else 0)} trunked systems, {len(departments)} fenced groups",
            sites_or_coverage="Every department and site location-fenced",
            departments_or_channels=f"{channels} conventional channels, {talkgroups} talkgroups",
            mode="Mixed",
            monitorability="Clear and digital voice; encrypted, data and continuous broadcasts left out",
            upgrade_required="DMR/NXDN upgrade for digital conventional rows",
            source_url="",
            notes="Generated for the SDS150; rebuilt on every install.",
            enabled=True,
            licensed=licensed,
            origin=ORIGIN_LOCAL,
            systems=systems,
            provenance=[Provenance(source_adapter="near_me", confidence="derived")],
        ))
    return lists


def list_settings(favorites: Sequence[FavoritesList]) -> Dict[str, ListSettings]:
    """Scanner settings for every list being installed: the Near Me lists
    lead, location-controlled, on quick keys 1-6 and monitored as their spec
    says; every other list is installed but not monitored."""
    specs = {spec.key: spec for spec in NEAR_ME}
    settings: Dict[str, ListSettings] = {}
    for favorite in favorites:
        spec = specs.get(favorite.favorite_key)
        settings[favorite.favorite_key] = (
            ListSettings(monitor=spec.monitor, quick_key=spec.quick_key, location_control=True, lead=True)
            if spec is not None
            else ListSettings(monitor=False)
        )
    return settings
