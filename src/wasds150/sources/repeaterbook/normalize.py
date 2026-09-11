"""Turn an Export API response into reviewable candidates, filtering locally.

The documentation lists the data items the North America export returns but
not their JSON keys, so :data:`FIELDS` is the one place the keys are named.
They are to be confirmed against the first approved response. Until then a
record missing a key this module needs is *dropped with a stated reason*, so a
mismatch fails closed and shows up in the drop summary rather than producing
wrong channels.

Rules, all from the design document:

* great-circle distance from one centre, within the chosen radius;
* the output frequency inside a selected band the target radio supports;
* analog FM only in this version -- a digital-only repeater is dropped, never
  coerced to FM;
* a record without usable coordinates is rejected;
* nothing is synthesized: a missing input frequency, tone or coordinate stays
  missing (a repeater without a published input becomes receive-only).
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from wasds150.radios.profile import RadioProfile
from wasds150.sources.repeaterbook.policy import AMATEUR_BANDS

#: Our name -> the response key. See the module docstring.
FIELDS: Dict[str, str] = {
    "state_id": "State ID",
    "rb_id": "Rptr ID",
    "output": "Frequency",
    "input": "Input Freq",
    "uplink_tone": "PL",
    "downlink_tone": "TSQ",
    "city": "Nearest City",
    "county": "County",
    "state": "State",
    "country": "Country",
    "lat": "Lat",
    "lon": "Long",
    "callsign": "Callsign",
    "use": "Use",
    "status": "Operational Status",
    "analog": "FM Analog",
    "last_update": "Last Update",
}

EARTH_RADIUS_MI = 3958.7613


class ResponseShapeError(ValueError):
    """The body is not the documented JSON export; nothing is imported."""


def parse_export(body: bytes) -> List[Dict[str, Any]]:
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ResponseShapeError("the RepeaterBook response is not JSON") from None
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list) or not all(isinstance(r, dict) for r in results):
        raise ResponseShapeError("the RepeaterBook response has no list of result records")
    return results


def great_circle_miles(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(min(1.0, math.sqrt(h)))


def _get(record: Dict[str, Any], name: str) -> str:
    value = record.get(FIELDS[name])
    return "" if value is None else str(value).strip()


def _float(text: str) -> Optional[float]:
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def tone(text: str) -> str:
    """A published CTCSS/DCS value in catalog notation, or ``""``. Unknown
    spellings become ``""`` rather than a guess."""
    value = text.strip().upper()
    if not value or value in ("CSQ", "NONE", "N/A"):
        return ""
    dcs = re.fullmatch(r"D0*(\d{1,3})[NI]?", value)
    if dcs:
        return f"D{int(dcs.group(1)):03d}"
    number = _float(value)
    if number is not None and 60.0 <= number <= 260.0:
        return f"TONE=C{number:g}"
    return ""


def _yes(text: str) -> bool:
    return text.strip().lower() in ("yes", "y", "true", "1")


@dataclass(frozen=True)
class FilterSpec:
    center: Tuple[float, float]
    radius_mi: int
    bands: Tuple[str, ...]
    profile: RadioProfile


@dataclass
class Drop:
    rb_key: str
    reason: str


@dataclass
class FilterResult:
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    drops: List[Drop] = field(default_factory=list)

    def drop_summary(self) -> Dict[str, int]:
        summary: Dict[str, int] = {}
        for drop in self.drops:
            summary[drop.reason] = summary.get(drop.reason, 0) + 1
        return dict(sorted(summary.items()))


def candidate(record: Dict[str, Any], spec: FilterSpec, region: str, retrieved_at: str):
    """``(candidate, None)`` or ``(None, Drop)`` for one response record."""
    state_id, rb_id = _get(record, "state_id"), _get(record, "rb_id")
    if not state_id or not rb_id:
        return None, Drop("?", "no RepeaterBook record id")
    rb_key = f"{state_id}:{rb_id}"

    output = _float(_get(record, "output"))
    if output is None or output <= 0:
        return None, Drop(rb_key, "no usable output frequency")
    lat, lon = _float(_get(record, "lat")), _float(_get(record, "lon"))
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        return None, Drop(rb_key, "no usable coordinates")
    distance = great_circle_miles(spec.center, (lat, lon))
    if distance > spec.radius_mi:
        return None, Drop(rb_key, "outside the radius")
    band = next((name for name in spec.bands if AMATEUR_BANDS[name][0] <= output <= AMATEUR_BANDS[name][1]), None)
    if band is None:
        return None, Drop(rb_key, "outside the selected bands")
    if not _yes(_get(record, "analog")):
        return None, Drop(rb_key, "not analog FM (digital-only repeaters are dropped, never coerced)")
    if not spec.profile.can_receive(output) or not spec.profile.supports_mode("FM"):
        return None, Drop(rb_key, "the target radio cannot receive it")

    input_mhz = _float(_get(record, "input"))
    if input_mhz is not None and input_mhz <= 0:
        input_mhz = None
    flags: List[str] = []
    if input_mhz is None:
        flags.append("no-input-published")
    elif not spec.profile.can_transmit(input_mhz):
        flags.append("receive-only-on-this-radio")
    status = _get(record, "status")
    if status.lower() != "on-air":
        flags.append(f"status:{status or 'unknown'}")
    use = _get(record, "use")
    if use.upper() != "OPEN":
        flags.append(f"use:{use or 'unknown'}")

    return {
        "rb_key": rb_key,
        "state_id": state_id,
        "rb_id": rb_id,
        "region": region,
        "callsign": _get(record, "callsign"),
        "output_mhz": output,
        "input_mhz": input_mhz,
        "rx_tone": tone(_get(record, "downlink_tone")),
        "tx_tone": tone(_get(record, "uplink_tone")),
        "mode": "FM",
        "band": band,
        "city": _get(record, "city"),
        "county": _get(record, "county"),
        "state": _get(record, "state"),
        "country": _get(record, "country"),
        "lat": lat,
        "lon": lon,
        "distance_mi": round(distance, 1),
        "status": status,
        "use": use,
        "last_update": _get(record, "last_update"),
        "retrieved_at": retrieved_at,
        "flags": flags,
    }, None


def filter_records(per_region: Sequence[Tuple[str, str, List[Dict[str, Any]]]], spec: FilterSpec) -> FilterResult:
    """Filter every region's records into one combined, de-duplicated,
    nearest-first candidate list."""
    result = FilterResult()
    seen = set()
    for region, retrieved_at, records in per_region:
        for record in records:
            item, drop = candidate(record, spec, region, retrieved_at)
            if drop is not None:
                result.drops.append(drop)
            elif item["rb_key"] in seen:
                result.drops.append(Drop(item["rb_key"], "duplicate record"))
            else:
                seen.add(item["rb_key"])
                result.candidates.append(item)
    result.candidates.sort(key=lambda c: (c["distance_mi"], c["output_mhz"]))
    return result
