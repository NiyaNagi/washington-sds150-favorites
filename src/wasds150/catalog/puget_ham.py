"""Puget Sound amateur repeater monitoring intent and WWARA curation.

The committed row contains only a small set of repeater/net facts published by
their operators. The comprehensive repeater inventory is derived locally from
WWARA's nightly coordination extract, which is licensed for radio programming
but not republished wholesale by this repository.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.sources.facts import NormalizedFact
from wasds150.util.hashing import stable_id

WWARA_URL = "https://www.wwara.org/DataBaseExtract.zip"
PSRG_NETS_URL = "https://web.psrg.org/net_schedule/"
PSRG_REPEATER_URL = "https://web.psrg.org/repeater-system/"
MIKE_KEY_URL = "https://mikeandkey.org/repeaters.php"
MIKE_KEY_NETS_URL = "https://mikeandkey.org/nets.php"
MASON_NETS_URL = "https://mc-arc.org/nets/"
ISLAND_REPEATER_URL = "https://www.w7avm.org/repeater-system"

# Broad Puget Sound / eastern Olympic / western Cascade listening region.
PUGET_BOUNDS = (46.75, 49.05, -123.55, -121.25)
_REGION_SPECS = {
    "North Sound & Islands": (48.45, -122.55, 80.0),
    "Olympic & Kitsap": (47.75, -122.95, 90.0),
    "South Sound": (47.15, -122.65, 75.0),
    "Eastside & Cascades": (47.55, -121.95, 70.0),
    "Seattle Metro": (47.62, -122.33, 55.0),
}


def _ascii(value: str) -> str:
    return (value or "").encode("ascii", "replace").decode("ascii")


def _channel(label: str, frequency: float, tone: str, mode: str, notes: str, *, priority: bool = False) -> Channel:
    return Channel(
        id=stable_id(f"puget-ham:official:{label}:{frequency}", kind="channel"),
        label=label,
        freq_mhz=frequency,
        mode=mode,
        tone=tone,
        service_type=13,
        priority=priority,
        notes=notes,
    )


def favorite() -> FavoritesList:
    net_channels = [
        _channel("WW7PSR Seattle 2m", 146.960, "TONE=C103.5", "FM",
                 "PSRG: daily 07:47 Boaters, 09:00/12:00/21:00 social; Mon 19:00 Seattle ACS and 19:30 PSRG", priority=True),
        _channel("WW7PSR Seattle 6m", 52.870, "TONE=C103.5", "FM",
                 "PSRG 6m voter/AllStar; linked to 2m for Monday 19:00/19:30 nets"),
        _channel("WW7PSR Seattle DMR", 440.775, "ColorCode=2", "DMR",
                 "PSRG dedicated DMR repeater; paid DMR upgrade required"),
        _channel("PSRG Saturday Simplex Net", 146.560, "", "FM",
                 "Official PSRG weekly simplex voice net, Saturday 20:00 Pacific"),
        _channel("K7LED Mike & Key 2m", 146.820, "TONE=C103.5", "FM",
                 "Nightly 19:30 social except Wed technical; Wed 19:00 emergency; Thu 18:30 check-in", priority=True),
        _channel("K7LED Mike & Key 1.25m", 224.120, "TONE=C103.5", "FM",
                 "Mike & Key informal net Sunday 19:00 Pacific"),
        _channel("Mason County ARC 2m", 146.720, "TONE=C103.5", "FM",
                 "MCARC weekly ragchew net Sunday 19:00 Pacific", priority=True),
        _channel("W7AVM Oak Harbor", 146.8625, "TONE=C114.8", "NFM",
                 "Island County ARC north repeater; official site reports normal operation"),
        _channel("W7AVM Clinton", 147.220, "TONE=C127.3", "FM",
                 "Island County ARC south repeater; RF-linked to Oak Harbor"),
        _channel("N7KN Greenbank", 441.425, "TONE=C110.9", "FM",
                 "Island County ARC; official page reports repeater operational, linking temporarily disabled"),
    ]
    net_department = Department(
        id=stable_id("puget-ham:official-nets", kind="department"),
        label="Operator-Published Repeaters & Nets",
        channels=net_channels,
        lat=47.62,
        lon=-122.33,
        range_miles=120.0,
        shape="Circle",
    )
    net_system = System(
        id=stable_id("puget-ham:official-nets", kind="system"),
        label="Puget Sound Published Net Channels",
        departments=[net_department],
    )
    return FavoritesList(
        id=stable_id("puget-ham:PSHAM01", kind="favorites-list"),
        slug="psham01",
        favorite_key="PSHAM01",
        favorite_name="Puget Sound Ham Repeaters & Nets",
        region="Puget Sound / eastern Olympic Peninsula / western Cascades",
        counties="King, Snohomish, Pierce, Thurston, Kitsap, Mason, Jefferson, Clallam, Island, San Juan, Skagit, Whatcom",
        scenario="Amateur repeater coordination / linked systems / emergency and social nets",
        source_type="WWARA nightly coordination + operator-published net channels",
        system_or_category="All current Puget-region WWARA coordinated repeaters, grouped by region and mode",
        sites_or_coverage="Puget bounding box 46.75-49.05 N, 123.55-121.25 W; broad location groups because WWARA coordinates may be fuzzed",
        departments_or_channels="Analog FM/NFM; linked analog; P25; DMR; unsupported D-Star/Fusion carriers avoided; official PSRG/Mike & Key/Mason/Island net channels",
        mode="FM/NFM + P25 + DMR; AUTO/avoided for unsupported D-Star/Fusion-only carriers",
        monitorability="Analog and P25 native; DMR requires paid upgrade; D-Star/Fusion voice unsupported",
        upgrade_required="DMR upgrade for DMR repeaters; D-Star/YSF cannot be decoded by SDS150",
        source_url=WWARA_URL,
        notes="Run sources update with WWARA to populate the full list. Net times are Pacific local time and may change; verify operator pages.",
        systems=[net_system],
        provenance=[
            Provenance(source_adapter="operator_pages", source_url=PSRG_NETS_URL, confidence="verified"),
            Provenance(source_adapter="operator_pages", source_url=PSRG_REPEATER_URL, confidence="verified"),
            Provenance(source_adapter="operator_pages", source_url=MIKE_KEY_URL, confidence="verified"),
            Provenance(source_adapter="operator_pages", source_url=MIKE_KEY_NETS_URL, confidence="verified"),
            Provenance(source_adapter="operator_pages", source_url=MASON_NETS_URL, confidence="verified"),
            Provenance(source_adapter="operator_pages", source_url=ISLAND_REPEATER_URL, confidence="verified"),
        ],
    )


def _inside_puget(fact: NormalizedFact) -> bool:
    if fact.source_id != "wwara" or fact.freq_mhz is None or fact.lat is None or fact.lon is None:
        return False
    south, north, west, east = PUGET_BOUNDS
    return south <= fact.lat <= north and west <= fact.lon <= east


def _scanner_frequency(frequency: float) -> bool:
    return any(low <= frequency <= high for low, high in (
        (25.0, 512.0), (758.0, 824.0), (849.0, 869.0), (894.0, 960.0), (1240.0, 1300.0),
    ))


def _region(fact: NormalizedFact) -> str:
    if fact.lat >= 48.10:
        return "North Sound & Islands"
    if fact.lon <= -122.75:
        return "Olympic & Kitsap"
    if fact.lat < 47.35:
        return "South Sound"
    if fact.lon >= -122.15:
        return "Eastside & Cascades"
    return "Seattle Metro"


def _mode_group(fact: NormalizedFact) -> str:
    raw = fact.raw if isinstance(fact.raw, dict) else {}
    linked = bool((raw.get("LINK") or "").strip())
    if fact.mode == "DMR":
        return "DMR (Upgrade Required)"
    if fact.mode == "P25":
        return "P25 Digital"
    if fact.mode == "AUTO":
        digital = "/".join(name for name, field in (("D-Star", "DSTAR_DV"), ("Fusion", "FUSION")) if raw.get(field) == "Y")
        return f"Unsupported Digital - {digital or 'Other'}"
    if linked:
        return "Linked Analog"
    if fact.freq_mhz < 54:
        return "Analog 6 Meter"
    if fact.freq_mhz < 148:
        return "Analog 2 Meter"
    if fact.freq_mhz < 230:
        return "Analog 1.25 Meter"
    if fact.freq_mhz < 500:
        return "Analog 70 Centimeter"
    if fact.freq_mhz < 1000:
        return "Analog 33 Centimeter"
    return "Analog 23 Centimeter"


def _fact_channel(fact: NormalizedFact) -> Channel:
    raw = fact.raw if isinstance(fact.raw, dict) else {}
    city = _ascii((raw.get("CITY") or "").strip())
    call = _ascii((raw.get("CALL") or fact.name or "Repeater").strip())
    offset = f"{fact.offset_mhz:+.4f} MHz" if fact.offset_mhz is not None else "offset unknown"
    modes = [label for label, field in (("FM", "FM_WIDE"), ("NFM", "FM_NARROW"), ("P25", "P25_PHASE_1"), ("DMR", "DMR"), ("D-Star", "DSTAR_DV"), ("Fusion", "FUSION")) if raw.get(field) == "Y"]
    details = [f"input {(raw.get('INPUT_FREQ') or '').strip()}", offset, "/".join(modes), (raw.get("LINK") or "").strip(), (raw.get("SPONSOR") or "").strip(), (raw.get("COMMENT") or "").strip(), fact.source_url]
    return Channel(
        id=stable_id(f"puget-ham:wwara:{fact.entity_key}", kind="channel"),
        label=f"{call} - {city}" if city else call,
        freq_mhz=fact.freq_mhz,
        mode=fact.mode or "AUTO",
        tone=fact.tone or "",
        service_type=13,
        avoid=fact.mode == "AUTO",
        notes=_ascii("; ".join(value for value in details if value)),
    )


def system_from_wwara_facts(favorite: FavoritesList, facts: Iterable[NormalizedFact]) -> Optional[System]:
    grouped: Dict[Tuple[str, str], List[Channel]] = defaultdict(list)
    seen = set()
    for fact in facts:
        if not _inside_puget(fact) or not _scanner_frequency(fact.freq_mhz):
            continue
        channel = _fact_channel(fact)
        key = (round(channel.freq_mhz, 6), channel.mode, channel.label.casefold())
        if key in seen:
            continue
        seen.add(key)
        grouped[(_region(fact), _mode_group(fact))].append(channel)
    if not grouped:
        return None

    departments = []
    for (region, mode_group), channels in sorted(grouped.items()):
        lat, lon, radius = _REGION_SPECS[region]
        departments.append(Department(
            id=stable_id(f"puget-ham:{region}:{mode_group}", kind="department"),
            label=f"{region} - {mode_group}",
            channels=sorted(channels, key=lambda channel: (channel.freq_mhz or 0, channel.label)),
            lat=lat,
            lon=lon,
            range_miles=radius,
            shape="Circle",
            avoid=mode_group.startswith("Unsupported Digital"),
        ))
    return System(
        id=stable_id("puget-ham:wwara-current", kind="system"),
        label="WWARA Current Puget Sound Coordinated Repeaters",
        departments=departments,
    )
