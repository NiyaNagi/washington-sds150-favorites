"""Favorites Lists for the regional DMR networks and the Seattle ACS analog set.

Built from :mod:`wasds150.sources.k7abd` facts - the community-maintained
Config Builder files for PNWDigital and SeattleDMR - either fetched live by
the ``seattledmr`` source or replayed from the checked-in snapshot in
:mod:`wasds150.catalog.atd890_dmr`.

Two lists come out:

``DMRNET`` "Pacific Northwest DMR Networks"
    One department per region ("Puget Sound", "Western Washington",
    "Eastern Washington", "Outside Washington"), one channel per
    repeater/talkgroup/timeslot with the DMR identity a transceiver needs.
    Repeater coordinates come from the coordinator (WWARA) rows already in
    the catalog when the output frequency and colour code match.

``SEAACS`` "Seattle ACS Analog"
    The Seattle Auxiliary Communications Service voice, simplex and packet
    channels, with the access tones the ACS publishes.
"""
from __future__ import annotations

import re
from collections import OrderedDict
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from wasds150.hpe.validation import tone_is_valid
from wasds150.models.catalog import ORIGIN_LOCAL, Catalog, Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.recipes.systems import dedupe_channels
from wasds150.sources.facts import NormalizedFact
from wasds150.util.hashing import stable_id

K7ABD_SOURCE_IDS = ("seattledmr", "atd890_dmr_snapshot")
DMRNET_KEY = "DMRNET"
SEAACS_KEY = "SEAACS"
SEATTLEDMR_INFO_URL = "https://seattledmr.com/"

CoordLookup = Callable[[float, Optional[int], Iterable[str]], Optional[Tuple[float, float]]]

_WORD_RE = re.compile(r"[A-Za-z]{4,}")


def coordinate_lookup_from_catalog(catalog: Catalog) -> CoordLookup:
    """Map a Config Builder repeater to the coordinator's site position.

    WWARA-derived DMR rows carry ``tone="ColorCode=N"``, a label naming the
    site (``WA7DMR - Cougar Mtn``) and a position; the Config Builder files
    carry a zone label (``Bellevu/Cougar``) but no callsign or position. The
    join therefore needs the output frequency, the colour code *and* a shared
    site word: the same pair and colour code recur across the state (Pullman
    and Clinton both sit on 440.700 CC1), so frequency alone would attach the
    wrong hill. No shared word means no position rather than a guess.
    """
    index: Dict[Tuple[float, Optional[int]], List[Tuple[frozenset, Tuple[float, float]]]] = {}
    for fl in catalog.favorites:
        for system in fl.systems:
            departments = list(system.departments)
            for site in system.sites:
                departments.extend(site.departments)
            for department in departments:
                for channel in department.channels:
                    if (channel.mode or "").upper() != "DMR" or channel.lat is None or channel.lon is None:
                        continue
                    if channel.freq_mhz is None:
                        continue
                    color = channel.dmr_color_code
                    if color is None and (channel.tone or "").startswith("ColorCode="):
                        try:
                            color = int(channel.tone.split("=", 1)[1])
                        except ValueError:
                            color = None
                    key = (round(channel.freq_mhz, 4), color)
                    words = frozenset(w.lower() for w in _WORD_RE.findall(channel.label))
                    point = (round(channel.lat, 5), round(channel.lon, 5))
                    entry = (words, point)
                    if entry not in index.setdefault(key, []):
                        index[key].append(entry)

    def lookup(freq_mhz: float, color: Optional[int], site_words: Iterable[str]) -> Optional[Tuple[float, float]]:
        wanted = {w.lower() for w in site_words}
        matches = [
            point for words, point in index.get((round(freq_mhz, 4), color), [])
            if wanted & words
        ]
        unique = {m for m in matches}
        if len(unique) == 1:
            return matches[0]
        return None

    return lookup


def _digital_channel(fact: NormalizedFact, coords: Optional[CoordLookup]) -> Channel:
    raw = fact.raw
    point = None
    if coords and fact.freq_mhz is not None:
        point = coords(fact.freq_mhz, fact.dmr_color_code, raw.get("site_tokens") or ())
    return Channel(
        id=stable_id(f"dmrnet:{fact.entity_key}", kind="channel"),
        label=fact.name,
        freq_mhz=round(fact.freq_mhz, 6) if fact.freq_mhz is not None else None,
        tx_freq_mhz=round(fact.tx_freq_mhz, 6) if fact.tx_freq_mhz is not None else None,
        mode="DMR",
        tone=fact.tone or "",
        service_type=13,
        lat=point[0] if point else None,
        lon=point[1] if point else None,
        location_precision="unknown" if point else "",
        notes=(
            f"{raw.get('network')} repeater {raw.get('repeater_label')} ({raw.get('repeater_code')}); "
            f"talkgroup {raw.get('talkgroup_name')} on timeslot {fact.dmr_timeslot}; "
            f"{fact.source_url}"
        ),
        dmr_color_code=fact.dmr_color_code,
        dmr_timeslot=fact.dmr_timeslot,
        dmr_talkgroup=fact.dmr_talkgroup,
        dmr_talkgroup_name=str(raw.get("talkgroup_name") or ""),
        network=str(raw.get("network") or ""),
    )


def _analog_channel(fact: NormalizedFact) -> Channel:
    raw = fact.raw
    tone = fact.tone or ""
    tx_tone = str(raw.get("tx_tone") or "")
    return Channel(
        id=stable_id(f"seaacs:{fact.entity_key}", kind="channel"),
        label=fact.name,
        freq_mhz=round(fact.freq_mhz, 6) if fact.freq_mhz is not None else None,
        tx_freq_mhz=round(fact.tx_freq_mhz, 6) if fact.tx_freq_mhz is not None else None,
        mode=fact.mode or "FM",
        tone=tone if tone_is_valid(tone) else "",
        tx_tone=tx_tone if tone_is_valid(tx_tone) else "",
        service_type=13,
        notes=f"Seattle ACS Config Builder zone {raw.get('zone')}; {fact.source_url}",
    )


def build_network_favorites(
    facts: Iterable[NormalizedFact],
    *,
    coords: Optional[CoordLookup] = None,
    retrieved_at: str = "",
) -> List[FavoritesList]:
    digital: "OrderedDict[str, List[Channel]]" = OrderedDict()
    analog: "OrderedDict[str, List[Channel]]" = OrderedDict()
    provenance_url = ""
    for fact in facts:
        if fact.source_id not in K7ABD_SOURCE_IDS or fact.freq_mhz is None:
            continue
        provenance_url = provenance_url or fact.source_url
        kind = fact.raw.get("kind")
        if kind == "digital":
            digital.setdefault(str(fact.raw.get("region") or "Unknown"), []).append(_digital_channel(fact, coords))
        elif kind == "analog":
            analog.setdefault(str(fact.raw.get("zone") or "Other"), []).append(_analog_channel(fact))

    favorites: List[FavoritesList] = []
    if digital:
        order = ["Puget Sound", "Western Washington", "Eastern Washington", "Outside Washington"]
        departments = [
            Department(
                id=stable_id(f"dmrnet:{region}", kind="department"),
                label=region,
                channels=dedupe_channels(digital[region]),
            )
            for region in order + [r for r in digital if r not in order]
            if region in digital
        ]
        total = sum(len(d.channels) for d in departments)
        favorites.append(
            FavoritesList(
                id=stable_id("dmrnet"),
                slug="dmrnet",
                favorite_key=DMRNET_KEY,
                favorite_name="Pacific Northwest DMR Networks",
                region="Pacific Northwest",
                counties="Statewide",
                scenario="Amateur DMR repeaters with their talkgroup and timeslot layout",
                source_type="PNWDigital / SeattleDMR Config Builder files",
                system_or_category="PNWDigital c-Bridge network and SeattleDMR bridge",
                sites_or_coverage="Every listed repeater, grouped by region",
                departments_or_channels=f"{total} repeater/talkgroup channels",
                mode="DMR",
                monitorability="DMR upgrade on the scanner; native on DMR transceivers",
                upgrade_required="DMR",
                source_url=SEATTLEDMR_INFO_URL,
                notes=(
                    "One channel per repeater and talkgroup, timeslot as the network carries it. "
                    "Talkgroup usage rules: " + "https://pnwdigital.net/talkgroups/"
                ),
                origin=ORIGIN_LOCAL,
                systems=[System(id=stable_id("dmrnet:system", kind="system"), label="Pacific Northwest DMR Networks", departments=departments)],
                provenance=[Provenance(source_adapter="seattledmr", source_url=provenance_url or SEATTLEDMR_INFO_URL, fetched_at=retrieved_at or None, confidence="community")],
            )
        )
    if analog:
        departments = [
            Department(id=stable_id(f"seaacs:{zone}", kind="department"), label=zone, channels=dedupe_channels(channels))
            for zone, channels in analog.items()
        ]
        total = sum(len(d.channels) for d in departments)
        favorites.append(
            FavoritesList(
                id=stable_id("seaacs"),
                slug="seaacs",
                favorite_key=SEAACS_KEY,
                favorite_name="Seattle ACS Analog Channels",
                region="Seattle / King County",
                counties="King, Snohomish, Pierce, Kitsap",
                scenario="Seattle Auxiliary Communications Service voice, simplex and packet channels",
                source_type="SeattleDMR Config Builder analog file",
                system_or_category="Seattle ACS channel plan",
                sites_or_coverage="Seattle and Puget Sound repeaters the ACS uses",
                departments_or_channels=f"{total} channels in {len(departments)} zones",
                mode="FM/NFM",
                monitorability="Analog; programs on every radio",
                upgrade_required="None",
                source_url=SEATTLEDMR_INFO_URL,
                notes="FRS/GMRS/NOAA zones duplicate the project's own lists and are deduplicated at plan time.",
                origin=ORIGIN_LOCAL,
                systems=[System(id=stable_id("seaacs:system", kind="system"), label="Seattle ACS Analog", departments=departments)],
                provenance=[Provenance(source_adapter="seattledmr", source_url=provenance_url or SEATTLEDMR_INFO_URL, fetched_at=retrieved_at or None, confidence="community")],
            )
        )
    return favorites
