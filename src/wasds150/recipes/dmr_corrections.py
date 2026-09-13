"""Corrections to the regional DMR layout where a network's own site disagrees.

The PNWDigital / SeattleDMR layout comes from the community Config Builder
files (:mod:`wasds150.sources.k7abd`). They are the best single source for
which talkgroup is on which timeslot of which machine, but they lag the
networks: a repeater that moved keeps its old frequency there, and one that
joined may not be there at all. A wrong row is worse than a missing one, since
it programs a zone of DMR talkgroups onto a machine that will never decode
them.

Each correction here names the network page that contradicts the file. They
are applied to any ``DMRNET`` list - the one :func:`build_network_favorites`
rebuilds when the ``seattledmr`` source runs, the checked-in snapshot, and
(through :func:`wasds150.plan.service.resolve_named_plan`) a copy already in
the operator's catalog that was built before the correction existed - so no
refresh, and no regenerated snapshot, can bring a corrected row back.
"""
from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from wasds150.models.catalog import Channel, Department, FavoritesList
from wasds150.util.hashing import stable_id

DMRNET_KEY = "DMRNET"

SEATTLEDMR_REPEATERS_URL = "https://seattledmr.org/"
RETRIEVED = "2026-09-13"

#: Repeater rows to leave out, keyed by (site code, output MHz).
SUPERSEDED: Dict[Tuple[str, float], str] = {
    ("BWT", 442.075): (
        "'BEARS W.Tiger' as a SeattleDMR DMR repeater on 442.075, CC2. SeattleDMR's own "
        f"repeater list ({SEATTLEDMR_REPEATERS_URL}, retrieved {RETRIEVED}) has K7NWS West "
        "Tiger Mountain on 440.3375, CC2, and nothing on 442.075 - which the coordinated "
        "catalog holds as K7NWS's analog repeater, CTCSS 110.9."
    ),
}


@dataclass(frozen=True)
class AddedRepeater:
    """A network repeater the Config Builder file lacks.

    ``layout_from`` names a repeater on the same network whose talkgroups and
    timeslots it carries; that is only sound where the network publishes one
    talkgroup table for all of its machines, as SeattleDMR does.
    """

    code: str
    site: str
    rx_mhz: float
    tx_mhz: float
    color_code: int
    lat: float
    lon: float
    layout_from: str
    department: str
    citation: str


ADDED: Tuple[AddedRepeater, ...] = (
    AddedRepeater(
        code="KNW",
        site="K7NWS West Tiger Mountain",
        rx_mhz=440.3375,
        tx_mhz=445.3375,
        color_code=2,
        # West Tiger Mountain, as the checked-in snapshot's Seattle/East row gives it.
        lat=47.50875,
        lon=-121.98519,
        layout_from="SCE",
        department="Puget Sound",
        citation=(
            f"SeattleDMR lists K7NWS West Tiger Mountain, 440.3375 +5 MHz CC2, as one of its "
            f"four repeaters, with one talkgroup table for all of them ({SEATTLEDMR_REPEATERS_URL}, "
            f"retrieved {RETRIEVED}); layout copied from Seattle/Central, which carries that table."
        ),
    ),
)


def _site_code(channel: Channel) -> str:
    """``King County BWT`` -> ``BWT``: the layout names channels "<talkgroup> <code>"."""
    return (channel.label or "").rsplit(" ", 1)[-1]


def _is_dmr(channel: Channel) -> bool:
    return (channel.mode or "").upper() == "DMR"


def _departments(fl: FavoritesList) -> List[Department]:
    departments: List[Department] = []
    for system in fl.systems:
        departments.extend(system.departments)
        for site in system.sites:
            departments.extend(site.departments)
    return departments


def _superseded(channel: Channel) -> bool:
    if not _is_dmr(channel) or channel.freq_mhz is None:
        return False
    return (_site_code(channel), round(channel.freq_mhz, 4)) in SUPERSEDED


def correct_network_list(fl: FavoritesList) -> FavoritesList:
    """``fl`` with the corrections applied; any list but ``DMRNET`` unchanged."""
    if (fl.favorite_key or "").upper() != DMRNET_KEY:
        return fl
    fl = copy.deepcopy(fl)
    departments = _departments(fl)
    for department in departments:
        department.channels = [c for c in department.channels if not _superseded(c)]
    for added in ADDED:
        channels = [c for d in departments for c in d.channels if _is_dmr(c)]
        if any(_site_code(c) == added.code and c.freq_mhz is not None
               and abs(c.freq_mhz - added.rx_mhz) < 5e-4 for c in channels):
            continue
        template = [c for c in channels if _site_code(c) == added.layout_from]
        if not template:
            continue
        target = next((d for d in departments if d.label == added.department), None)
        if target is None:
            continue
        for channel in template:
            tone = channel.tone or ""
            target.channels.append(dataclasses.replace(
                channel,
                id=stable_id(
                    f"dmrnet:added:{added.code}:{channel.dmr_talkgroup}:{channel.dmr_timeslot}", kind="channel"
                ),
                label=channel.label[: -len(added.layout_from)] + added.code,
                freq_mhz=added.rx_mhz,
                tx_freq_mhz=added.tx_mhz,
                dmr_color_code=added.color_code,
                tone=f"ColorCode={added.color_code}" if tone.startswith("ColorCode=") else tone,
                lat=added.lat,
                lon=added.lon,
                location_precision="unknown",
                notes=(
                    f"{channel.network} repeater {added.site} ({added.code}); talkgroup "
                    f"{channel.dmr_talkgroup_name} on timeslot {channel.dmr_timeslot}; {added.citation}"
                ),
            ))
    return fl


#: DMR colour codes the coordinator's record gets wrong, keyed by (callsign,
#: output MHz). Every copy of these rows in the catalog descends from one
#: coordination entry, so fixing the catalog would mean fixing every list
#: that repeats it; the correction is applied to every list instead. A
#: colour code matters: a scanner or radio set to the wrong one decodes
#: nothing from the repeater.
COLOR_CODES: Dict[Tuple[str, float], Tuple[int, str]] = {
    ("N7QT", 442.325): (
        1,
        "N7QT Redmond reports colour code 1 to BrandMeister (api.brandmeister.network/v2/"
        f"device/311757, last seen {RETRIEVED}, both slots linked); the coordination record "
        "every other list copies says 2.",
    ),
}


def _color_fix(channel: Channel) -> Optional[int]:
    if not _is_dmr(channel) or channel.freq_mhz is None:
        return None
    label = (channel.label or "").upper()
    for (call, mhz), (color, _why) in COLOR_CODES.items():
        if abs(channel.freq_mhz - mhz) < 5e-4 and call in label:
            current = channel.dmr_color_code
            tone = channel.tone or ""
            if current is None and tone.startswith("ColorCode="):
                try:
                    current = int(tone.split("=", 1)[1])
                except ValueError:
                    current = None
            return color if current != color else None
    return None


def correct_color_codes(fl: FavoritesList) -> FavoritesList:
    """``fl`` with :data:`COLOR_CODES` applied; the same object when nothing matches."""
    if not any(_color_fix(c) is not None for d in _departments(fl) for c in d.channels):
        return fl
    fl = copy.deepcopy(fl)
    for department in _departments(fl):
        for index, channel in enumerate(department.channels):
            color = _color_fix(channel)
            if color is None:
                continue
            tone = channel.tone or ""
            department.channels[index] = dataclasses.replace(
                channel,
                dmr_color_code=color,
                tone=f"ColorCode={color}" if (not tone or tone.startswith("ColorCode=")) else tone,
            )
    return fl


def correct_network_lists(favorites: Iterable[FavoritesList]) -> List[FavoritesList]:
    return [correct_color_codes(correct_network_list(fl)) for fl in favorites]
