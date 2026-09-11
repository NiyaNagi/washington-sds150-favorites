"""FAA airband: every published airport, approach, centre and weather
frequency in Washington as one located Favorites List.

The FAA's NASR 28-day subscription is the canonical source. Its ``FRQ.csv``
lists each facility's frequencies with a use (tower ``LCL/P``, ground,
clearance, ATIS, CTAF/UNICOM, approach/departure, Seattle Center outlets,
ASOS/AWOS...) and a position; :mod:`wasds150.sources.faa_nasr` turns those
rows into frequency facts and this recipe collects them into ``FAAAIR``.

* One department per providing facility: an airport's tower, the Seattle
  approach control (TRACON ``S46``), a Seattle Center outlet (RCAG), a
  non-towered field's CTAF. Each department carries a geo-fence, the
  scanner's location control, sized to how far that service is heard.
* One channel per frequency and area. Approach control publishes the same
  frequency once for every airport it serves; the copy nearest home is
  kept. When facilities within reach of each other share a frequency, the
  higher-ranked one keeps it (Renton Tower's 124.7, which the Lake
  Washington seaplane base uses as its CTAF), and a CTAF or UNICOM that
  several fields share becomes one "Common CTAF" channel fenced around all
  of them, so every radio names it the same honest way.
* Navigation aids (VOR, TACAN, VOT, NDB) are Morse identifiers or test
  signals, not voice, and are left out.

The data is public domain (US federal work). The list has ``origin=local``
because it is built on this machine from the download, and it is rebuilt
whenever the FAA source ran, like the RadioReference county lists.
"""
from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from wasds150.models.catalog import ORIGIN_LOCAL, Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.sources.facts import NormalizedFact
from wasds150.util.geo import haversine_miles
from wasds150.util.hashing import stable_id

FAA_AIRBAND_KEY = "FAAAIR"
#: Uniden service type 15 is Aircraft (``AIRCRAFT`` in the fleet template).
AIRCRAFT_SERVICE_TYPE = 15
#: Civil VHF airband, the military VHF operations channels the FAA lists at
#: towers (Gray AAF OPS 138.6), and military UHF airband; all AM.
AIRBAND = ((108.0, 144.0), (225.0, 400.0))
#: The part of :data:`AIRBAND` above the civil air band.
MILITARY_VHF = (137.0, 144.0)
_SOURCE_URL = "https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/"

#: (pattern over the FAA frequency use, short label, order within a facility)
_USES: Tuple[Tuple[str, str, int], ...] = (
    (r"^LCL", "TWR", 0),
    (r"^D-ATIS", "D-ATIS", 1),
    (r"^ATIS", "ATIS", 1),
    (r"APCH", "APP", 2),
    (r"^DEP", "DEP", 3),
    (r"^CLASS [BC]|\bSTAR$|\bDP$", "APP", 2),
    (r"^GND", "GND", 4),
    (r"^CD", "CLR", 5),
    (r"^CTAF", "CTAF", 6),
    (r"^UNICOM", "UNICOM", 7),
    (r"RCAG$|ARTCC$", "CTR", 8),
    (r"RCO$", "RADIO", 9),
    (r"\bASOS\b", "ASOS", 10),
    (r"\bAWOS", "AWOS", 10),
    (r"^EMERG", "GUARD", 11),
    (r"PMSV|METRO", "METRO", 12),
)
_NAVAID_USE = re.compile(r"\b(VOR|VORTAC|TACAN|VOT|NDB|DME|ILS|LOC)\b")
#: Uses a field's own pilots talk on; shared by several fields, they become
#: one "Common" channel.
_SHARED_USES = ("CTAF", "UNICOM")

#: Facility type -> (department order, geo-fence miles): how far out each
#: service is worth hearing. Aircraft talk from altitude, so every fence is
#: wider than the field itself.
_CLASSES: Dict[str, Tuple[int, float]] = {
    "ATCT": (0, 25.0),
    "ATCT-TRACON": (0, 30.0),
    "ATCT-RATCF": (0, 30.0),
    "TRACON": (1, 40.0),
    "ARTCC": (2, 80.0),
    "RCAG": (2, 80.0),
    "RCO": (3, 40.0),
    "NON-ATCT": (4, 15.0),
    "ASOS_AWOS": (5, 20.0),
}
_OTHER_CLASS = (4, 20.0)
_FIELD_FENCE = _CLASSES["NON-ATCT"][1]


def _text(raw: Dict[str, Any], key: str) -> str:
    return " ".join(str(raw.get(key) or "").split())


def _title(text: str) -> str:
    return text.title() if text.isupper() else text


def _in_airband(freq: float) -> bool:
    return any(low <= freq <= high for low, high in AIRBAND)


def _use(use: str) -> Tuple[str, int]:
    text = use.strip().upper()
    for pattern, short, rank in _USES:
        if re.search(pattern, text):
            return short, rank
    return (_title(text)[:12] or "AIR"), len(_USES)


def _sector(short: str, sectorization: str) -> str:
    text = sectorization.upper()
    if short == "TWR":
        match = re.match(r"RWY\s+([\w/]+)", text)
        return match.group(1) if match else ""
    if short in ("APP", "DEP"):
        match = re.match(r"(\d{3}-\d{3})", text)
        if match:
            return match.group(1)
        return text if text.isalpha() and len(text) <= 8 else ""
    return ""


def _label(raw: Dict[str, Any], provider: str, served: str, short: str) -> str:
    facility_type = _text(raw, "FACILITY_TYPE").upper()
    if short == "GUARD":
        return "Guard"
    if short in ("APP", "DEP") and facility_type in ("TRACON", "ATCT-TRACON", "ATCT-RATCF"):
        call = _text(raw, "PRIMARY_APPROACH_RADIO_CALL")
        ident = _title(call) if call else provider
    elif short == "CTR":
        ident = _title(_text(raw, "FAC_NAME") or provider)
    elif short == "RADIO":
        ident = _title(_text(raw, "TOWER_OR_COMM_CALL") or provider)
    else:
        ident = served or provider
    sector = _sector(short, _text(raw, "SECTORIZATION"))
    return " ".join(part for part in (ident, short, sector) if part)[:64]


def _department_label(provider: str, rows: List[Dict[str, Any]]) -> str:
    types = {_text(r, "FACILITY_TYPE").upper() for r in rows}
    names = [_text(r, "FAC_NAME") for r in rows if _text(r, "FAC_NAME")]
    if "RCAG" in types:
        return f"{_title(provider)} RCAG"
    if "ARTCC" in types:
        return f"{provider} {_title(names[0])} Center" if names else f"{provider} Center"
    name = next((n for n in names if n.upper() != provider), "")
    return f"{provider} {_title(name)}" if name else provider


def _facility_class(rows: List[Dict[str, Any]]) -> Tuple[int, float]:
    return min((_CLASSES.get(_text(r, "FACILITY_TYPE").upper(), _OTHER_CLASS) for r in rows), default=_OTHER_CLASS)


def _miles(home: Optional[Tuple[float, float]], lat: Optional[float], lon: Optional[float]) -> float:
    if home is None or lat is None or lon is None:
        return 0.0 if home is None else float("inf")
    return haversine_miles(home[0], home[1], lat, lon)


def _centre(points: List[Tuple[float, float]]) -> Tuple[float, float, float]:
    lat = sum(p[0] for p in points) / len(points)
    lon = sum(p[1] for p in points) / len(points)
    return lat, lon, max(haversine_miles(lat, lon, p[0], p[1]) for p in points)


def _merge_shared(providers: "OrderedDict[str, Dict[str, Any]]", home: Optional[Tuple[float, float]]) -> List[tuple]:
    """Leave one channel per frequency and area. Facilities within reach of
    each other that share a frequency hand it to the highest-ranked one; a
    CTAF or UNICOM shared only among fields becomes a Common department
    (returned, with its sort key) fenced around every field that uses it."""
    by_freq: Dict[float, List[tuple]] = {}
    for provider, info in providers.items():
        order, fence = info["class"]
        for item in info["channels"]:
            rank, freq, short, channel = item
            if channel.lat is None or channel.lon is None:
                continue
            by_freq.setdefault(freq, []).append(((order, rank, _miles(home, channel.lat, channel.lon)), fence, provider, item))
    dropped = set()
    commons: List[tuple] = []
    for freq, rows in by_freq.items():
        if len(rows) < 2:
            continue
        rows.sort(key=lambda row: row[0])
        clusters: List[List[tuple]] = []
        for row in rows:
            for cluster in clusters:
                keeper = cluster[0]
                a, b = keeper[3][3], row[3][3]
                if haversine_miles(a.lat, a.lon, b.lat, b.lon) <= max(keeper[1], row[1]):
                    cluster.append(row)
                    break
            else:
                clusters.append([row])
        for cluster in clusters:
            if len(cluster) < 2:
                continue
            keeper, others = cluster[0], cluster[1:]
            _key, _fence, keeper_provider, (_rank, _freq, short, channel) = keeper
            for row in others:
                dropped.add(id(row[3][3]))
            if all(row[3][2] in _SHARED_USES for row in cluster):
                dropped.add(id(channel))
                fields = sorted({row[2] for row in cluster})
                lat, lon, spread = _centre([(row[3][3].lat, row[3][3].lon) for row in cluster])
                common = Channel(
                    id=stable_id(f"faaair:common:{freq:.4f}:{keeper_provider}", kind="channel"),
                    label=f"Common {short}",
                    freq_mhz=freq,
                    mode="AM",
                    notes=f"FAA NASR: {short} shared by {', '.join(fields[:12])}" + (f" and {len(fields) - 12} more" if len(fields) > 12 else ""),
                    service_type=AIRCRAFT_SERVICE_TYPE,
                    lat=round(lat, 6),
                    lon=round(lon, 6),
                    location_precision="exact",
                )
                department = Department(
                    id=stable_id(f"faaair:dept:common:{freq:.4f}:{keeper_provider}", kind="department"),
                    label=f"Common {short} {freq:.3f}",
                    channels=[common],
                    lat=round(lat, 6),
                    lon=round(lon, 6),
                    range_miles=round(_FIELD_FENCE + spread, 1),
                    shape="Circle",
                )
                commons.append(((_CLASSES["NON-ATCT"][0], _miles(home, lat, lon), f"~{freq:.4f}"), department))
            else:
                also = sorted({row[3][3].label for row in others})
                channel.notes = "; ".join(part for part in (channel.notes, "also " + ", ".join(also[:12])) if part)
    for info in providers.values():
        info["channels"] = [item for item in info["channels"] if id(item[3]) not in dropped]
    return commons


def build_faa_airband_favorite(
    facts: Iterable[NormalizedFact], home: Optional[Tuple[float, float]] = None
) -> Optional[FavoritesList]:
    """``FAAAIR`` from the FAA NASR frequency facts, or ``None`` when the
    FAA source did not run. ``home`` picks which serviced airport's position
    an approach frequency keeps and orders the departments nearest first."""
    rows = []
    for fact in facts:
        if fact.source_id != "faa_nasr" or fact.fact_type != "frequency" or fact.freq_mhz is None:
            continue
        raw = fact.raw if isinstance(fact.raw, dict) else {}
        use = _text(raw, "FREQ_USE")
        if _text(raw, "FACILITY_TYPE").upper() == "NAVAID" or _NAVAID_USE.search(use.upper()):
            continue
        if not _in_airband(fact.freq_mhz):
            continue
        rows.append((fact, raw, use))
    if not rows:
        return None

    #: provider -> frequency -> candidate rows
    grouped: "OrderedDict[str, OrderedDict[float, List[Tuple[NormalizedFact, Dict[str, Any], str]]]]" = OrderedDict()
    for fact, raw, use in rows:
        served = _text(raw, "SERVICED_FACILITY").upper()
        provider = _text(raw, "FACILITY").upper() or served or fact.entity_key
        grouped.setdefault(provider, OrderedDict()).setdefault(round(fact.freq_mhz, 4), []).append((fact, raw, use))

    providers: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
    for provider, by_freq in grouped.items():
        channels: List[Tuple[int, float, str, Channel]] = []
        facility_rows: List[Dict[str, Any]] = []
        for freq, candidates in by_freq.items():
            facility_rows.extend(raw for _fact, raw, _use_text in candidates)
            nearest = min(candidates, key=lambda c: _miles(home, c[0].lat, c[0].lon))
            fact, raw, use = min(candidates, key=lambda c: (_use(c[2])[1], _miles(home, c[0].lat, c[0].lon)))
            short, rank = _use(use)
            served_all = sorted({_text(r, "SERVICED_FACILITY").upper() for _f, r, _u in candidates} - {""})
            served = _text(raw, "SERVICED_FACILITY").upper()
            notes = "; ".join(
                part for part in (
                    f"FAA NASR {provider}",
                    use,
                    _text(raw, "SECTORIZATION"),
                    f"serves {', '.join(served_all[:12])}" if len(served_all) > 1 else "",
                    f"effective {_text(raw, 'EFF_DATE')}" if _text(raw, "EFF_DATE") else "",
                ) if part
            )
            lat, lon = nearest[0].lat, nearest[0].lon
            channels.append((rank, freq, short, Channel(
                id=stable_id(f"faaair:{provider}:{freq:.4f}", kind="channel"),
                label=_label(raw, provider, served, short),
                freq_mhz=freq,
                mode="AM",
                notes=notes,
                service_type=AIRCRAFT_SERVICE_TYPE,
                lat=lat,
                lon=lon,
                location_precision="exact" if lat is not None else "unknown",
            )))
        providers[provider] = {"rows": facility_rows, "class": _facility_class(facility_rows), "channels": channels}

    commons = _merge_shared(providers, home)

    departments: List[Tuple[Tuple[int, float, str], Department]] = []
    for provider, info in providers.items():
        items = sorted(info["channels"], key=lambda item: (item[0], item[1]))
        if not items:
            continue
        channels = [item[3] for item in items]
        located = [c for c in channels if c.lat is not None and c.lon is not None]
        order, fence = info["class"]
        lat = lon = radius = None
        if located:
            lat, lon, spread = _centre([(c.lat, c.lon) for c in located])
            radius = round(fence + spread, 1)
        department = Department(
            id=stable_id(f"faaair:dept:{provider}", kind="department"),
            label=_department_label(provider, info["rows"])[:64],
            channels=channels,
            lat=round(lat, 6) if lat is not None else None,
            lon=round(lon, 6) if lon is not None else None,
            range_miles=radius,
            shape="Circle" if lat is not None else "",
        )
        departments.append(((order, _miles(home, lat, lon), provider), department))
    departments.extend(commons)
    departments.sort(key=lambda item: item[0])

    total = sum(len(d.channels) for _k, d in departments)
    facts_used = [fact for fact, _raw, _use_text in rows]
    newest = max((f.retrieved_at for f in facts_used if f.retrieved_at), default=None)
    cycle = max((_text(raw, "EFF_DATE") for _f, raw, _u in rows if _text(raw, "EFF_DATE")), default="")
    source_url = next((f.source_url for f in facts_used if f.source_url), None) or _SOURCE_URL
    return FavoritesList(
        id=stable_id(FAA_AIRBAND_KEY.lower()),
        slug=FAA_AIRBAND_KEY.lower(),
        favorite_key=FAA_AIRBAND_KEY,
        favorite_name="FAA Airband - Washington",
        region="Washington",
        counties="Facility locations",
        scenario="Airport towers, approach control, Seattle Center, CTAF/UNICOM and weather broadcasts",
        source_type="FAA NASR 28-day subscription (public domain)",
        system_or_category=f"{len(departments)} facilities",
        sites_or_coverage="Each department geo-fenced around its facility",
        departments_or_channels=f"{total} frequencies",
        mode="AM",
        monitorability="Clear AM voice; ATIS and ASOS/AWOS broadcast continuously",
        upgrade_required="",
        source_url=source_url,
        notes=(
            "Built from the FAA NASR facility frequency file (FRQ.csv)"
            + (f", cycle effective {cycle}" if cycle else "")
            + ". Navigation aids are left out."
        ),
        enabled=True,
        origin=ORIGIN_LOCAL,
        systems=[
            System(
                id=stable_id("faaair:system", kind="system"),
                label="FAA Airband",
                departments=[d for _k, d in departments],
            )
        ],
        provenance=[Provenance(source_adapter="faa_nasr", source_url=source_url, fetched_at=newest, confidence="community")],
    )
