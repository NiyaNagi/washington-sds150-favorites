"""One label per station, whichever radio programs it.

The catalog carries many copies of a busy frequency - the RadioReference
county row, a curated trip list's row, a band rollup's row - each labelled
its own way. Left alone, every radio shows whichever copy its first group
reaches, so one station reads "SAR F-3" on one radio and "KC SAR F-2/F-3
(2)" on another. :class:`StationLabels` makes the choice once for the whole
catalog, and every memory plan and the SDS150's Near Me lists read it:

* A station is a frequency, mode and tone *in one area*: two copies are the
  same station when their areas overlap - a channel's own site with
  :data:`LOCATED_REACH_MILES` around it, else its department's fence. The
  same frequency in two counties is two stations and keeps two labels.
* Its label comes from the preferred source (:func:`source_rank`: the FAA;
  then the names written for these radios - the curated lists, WWARA and
  the other coordinated amateur and GMRS lists, NOAA; then the database
  descriptions - RadioReference, the FCC; then a radio's own local lists),
  and within a source from the copy nearest home. A copy with no position
  counts toward the area nearest home.
* FM and narrow FM, and a monitoring channel's tone, do not make two
  stations: lists disagree on both for the same transmitter, and a
  monitoring radio opens for either.
* An amateur repeater's **access tone** does: two machines can share one
  pair and differ only by tone (K7PG and W7FEL on 147.06/147.66), and a
  memory must carry the name of the machine whose tone it transmits. A copy
  with no tone takes the name of the one toned machine on its pair, when
  there is only one.
* A DMR or NXDN talkgroup channel keeps its own name: two talkgroups on one
  repeater share a frequency but are two memories.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple

from wasds150.models.catalog import Channel, Department
from wasds150.radios.services import AMATEUR, service_for
from wasds150.radios.tones import TONE_CTCSS, TONE_DCS, parse_tone
from wasds150.util.geo import haversine_miles

#: How far around its own site a located station counts as "here".
LOCATED_REACH_MILES = 30.0
_DESCRIPTIONS = frozenset({"RRWA", "FCCDIG"})
_RADIO_LOCAL = ("THD75", "ATD890", "FTX0", "NM-")
_ANALOG_FM = frozenset({"", "FM", "NFM", "FMN", "AUTO", "ALL"})
_DIGITAL = frozenset({"DMR", "NXDN", "P25", "DV", "DSTAR"})

Key = Tuple[float, str, str]
Area = Tuple[float, float, float]


def source_rank(favorite_key: str) -> int:
    """0 the FAA, 1 a list written for radios, 2 a database's descriptions,
    3 a radio's own local list."""
    key = favorite_key.upper()
    if key == "FAAAIR":
        return 0
    if key.startswith(("RRC-", "RRT-")) or key in _DESCRIPTIONS:
        return 2
    if key.startswith(_RADIO_LOCAL):
        return 3
    return 1


def mode_family(mode: Optional[str]) -> str:
    text = (mode or "").upper()
    return "FM" if text in _ANALOG_FM else text


def station_key(channel: Channel) -> Optional[Key]:
    if channel.freq_mhz is None or channel.tgid is not None:
        return None
    if channel.dmr_talkgroup is not None or channel.nxdn_group_id is not None:
        return None
    family = mode_family(channel.mode)
    # A digital channel's colour code or NAC does tell two systems apart.
    return (round(channel.freq_mhz, 5), family, (channel.tone or "") if family in _DIGITAL else "")


def access_tone(channel: Channel) -> str:
    """An analog amateur repeater's access tone as text - ``103.5`` for
    CTCSS, ``D172`` for DCS - and empty for anything else. A DCS machine is
    not a copy with no tone: V71 Lynnwood's DCS 172 on 146.78 is not WW7CH
    Ashford's 103.5."""
    if channel.freq_mhz is None or channel.tx_freq_mhz is None or service_for(channel.freq_mhz) != AMATEUR:
        return ""
    tone = parse_tone(channel.tx_tone or channel.tone)
    if tone.kind == TONE_CTCSS and tone.ctcss_hz:
        return f"{tone.ctcss_hz:g}"
    if tone.kind == TONE_DCS and tone.dcs_code:
        return f"D{tone.dcs_code}"
    return ""


def _label_key(channel: Channel) -> Optional[Key]:
    key = station_key(channel)
    if key is None or key[1] in _DIGITAL:
        return key
    return (key[0], key[1], access_tone(channel))


def station_area(department: Optional[Department], channel: Channel) -> Optional[Area]:
    if channel.lat is not None and channel.lon is not None:
        return (channel.lat, channel.lon, LOCATED_REACH_MILES)
    if department is not None and department.lat is not None and department.lon is not None and department.range_miles:
        return (department.lat, department.lon, float(department.range_miles))
    return None


def areas_overlap(a: Optional[Area], b: Optional[Area]) -> bool:
    """An area of ``None`` (anywhere) overlaps everything."""
    if a is None or b is None:
        return True
    return haversine_miles(a[0], a[1], b[0], b[1]) <= max(a[2], b[2])


@dataclass
class _Station:
    area: Area
    rank: int
    label: str


class StationLabels:
    def __init__(
        self,
        rows: Iterable[Tuple[str, Optional[Department], Channel]],
        home: Optional[Tuple[float, float]] = None,
    ) -> None:
        self.home = home
        located: Dict[Key, List[tuple]] = {}
        unlocated: Dict[Key, tuple] = {}
        #: The access tones seen on each (frequency, family).
        self._tones: Dict[Tuple[float, str], Set[str]] = {}
        for order, (favorite_key, department, channel) in enumerate(rows):
            key = _label_key(channel)
            if key is None or not channel.label:
                continue
            if key[2] and key[1] not in _DIGITAL:
                self._tones.setdefault(key[:2], set()).add(key[2])
            rank = source_rank(favorite_key)
            area = station_area(department, channel)
            if area is None:
                candidate = (rank, order, channel.label)
                if key not in unlocated or candidate < unlocated[key]:
                    unlocated[key] = candidate
            else:
                located.setdefault(key, []).append((rank, self._miles(area), order, area, channel.label))

        self._stations: Dict[Key, List[_Station]] = {}
        for key, copies in located.items():
            stations: List[_Station] = []
            # Best first, so the first copy in an area names it.
            for rank, _miles, _order, area, label in sorted(copies, key=lambda c: (c[0], c[1], c[2])):
                if not any(areas_overlap(station.area, area) for station in stations):
                    stations.append(_Station(area, rank, label))
            self._stations[key] = stations
        self._unlocated: Dict[Key, str] = {}
        for key, (rank, _order, label) in unlocated.items():
            stations = self._stations.get(key)
            if not stations:
                self._unlocated[key] = label
                continue
            nearest = min(stations, key=lambda station: self._miles(station.area))
            if rank < nearest.rank:
                nearest.label, nearest.rank = label, rank

    def _miles(self, area: Area) -> float:
        return haversine_miles(self.home[0], self.home[1], area[0], area[1]) if self.home else 0.0

    def _key_for(self, channel: Channel) -> Optional[Key]:
        key = _label_key(channel)
        if key is None or key[2] or key[1] in _DIGITAL:
            return key
        # A copy with no tone is named for the one toned machine on its pair.
        tones = self._tones.get(key[:2], set())
        return (key[0], key[1], next(iter(tones))) if len(tones) == 1 else key

    def label(self, department: Optional[Department], channel: Channel) -> str:
        key = self._key_for(channel)
        if key is None:
            return channel.label
        stations = self._stations.get(key)
        if not stations:
            return self._unlocated.get(key, channel.label)
        area = station_area(department, channel)
        if area is None:
            return min(stations, key=lambda station: self._miles(station.area)).label
        for station in stations:
            if areas_overlap(station.area, area):
                return station.label
        return channel.label
