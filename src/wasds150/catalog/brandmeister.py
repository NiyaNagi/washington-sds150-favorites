"""BrandMeister repeaters near home, as the ``BMNET`` Favorites List.

Built from the committed snapshot in
:mod:`wasds150.catalog.brandmeister_snapshot`, which
``scripts/radios/build_brandmeister_snapshot.py`` regenerates from the
network's public API. One channel per repeater and static talkgroup, with the
DMR identity a transceiver needs, in the same shape as the PNWDigital and
SeattleDMR rows of ``DMRNET`` (:mod:`wasds150.recipes.dmr_networks`), so the
fleet template's DMR blocks and the talkgroup tiers treat them alike.
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from wasds150.models.catalog import ORIGIN_LOCAL, Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.recipes.systems import dedupe_channels
from wasds150.util.hashing import stable_id

BMNET_KEY = "BMNET"
NETWORK = "BrandMeister"
API_URL = "https://api.brandmeister.network/v2"
INFO_URL = "https://brandmeister.network/"

RepeaterRow = Tuple[int, str, str, float, float, int, float, float, str, Tuple[Tuple[int, int], ...]]


def _channel(row: RepeaterRow, talkgroup: int, slot: int, name: str) -> Channel:
    bm_id, call, site, output, input_, color, lat, lon, seen, _statics = row
    return Channel(
        id=stable_id(f"bmnet:{bm_id}:{talkgroup}:{slot}", kind="channel"),
        label=f"{call} {name}"[:64],
        freq_mhz=round(output, 6),
        tx_freq_mhz=round(input_, 6),
        mode="DMR",
        tone=f"ColorCode={color}",
        service_type=13,
        lat=lat,
        lon=lon,
        location_precision="unknown",
        notes=(
            f"BrandMeister repeater {call} ({site}), device {bm_id}; static talkgroup {name} "
            f"({talkgroup}) on timeslot {slot}; last seen {seen}; {API_URL}/device/{bm_id}"
        ),
        dmr_color_code=color,
        dmr_timeslot=slot,
        dmr_talkgroup=talkgroup,
        dmr_talkgroup_name=name,
        network=NETWORK,
    )


def favorites_from_snapshot(
    talkgroups: Dict[int, str], repeaters: Sequence[RepeaterRow], retrieved: str
) -> List[FavoritesList]:
    channels = [
        _channel(row, talkgroup, slot, talkgroups.get(talkgroup, f"TG {talkgroup}"))
        for row in repeaters
        for talkgroup, slot in row[9]
    ]
    if not channels:
        return []
    department = Department(
        id=stable_id("bmnet:repeaters", kind="department"),
        label="BrandMeister Repeaters",
        channels=dedupe_channels(channels),
    )
    return [
        FavoritesList(
            id=stable_id("bmnet"),
            slug="bmnet",
            favorite_key=BMNET_KEY,
            favorite_name="BrandMeister Repeaters Near Home",
            region="Puget Sound and the Olympic Peninsula",
            counties="King, Kitsap, Jefferson, Clallam, Snohomish, Pierce",
            scenario="Amateur DMR repeaters on the BrandMeister network with their static talkgroups",
            source_type="BrandMeister API v2 (committed snapshot)",
            system_or_category="BrandMeister repeaters and their owner-set static talkgroups",
            sites_or_coverage="Repeaters near home, at their owners' registered positions",
            departments_or_channels="One channel per repeater and static talkgroup",
            mode="DMR",
            monitorability="DMR upgrade on the scanner; native on DMR transceivers",
            upgrade_required="DMR",
            source_url=INFO_URL,
            notes=(
                f"Snapshot retrieved {retrieved}. Only static talkgroups are programmed; any other "
                "BrandMeister talkgroup is reached by keying it on the repeater (dynamic)."
            ),
            origin=ORIGIN_LOCAL,
            systems=[System(id=stable_id("bmnet:system", kind="system"), label="BrandMeister", departments=[department])],
            provenance=[Provenance(source_adapter="brandmeister_snapshot", source_url=API_URL,
                                   fetched_at=f"{retrieved}T00:00:00Z", confidence="community")],
        )
    ]
