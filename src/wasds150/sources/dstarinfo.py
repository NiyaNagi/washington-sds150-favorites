"""DSTARInfo (dstarinfo.com) - the D-STAR repeater directory.

**Confirmed live 2026-09-13.** The download pages on dstarinfo.com are frames
around ASP.NET WebForms applications; nothing there is a static file:

* ``apps.dstarinfo.com/D-STAR_Repeater_List.aspx`` - the whole directory, one
  area at a time (22 areas, a postback on the ``Countries1`` list). A row is
  the callsign (linking ``Repeater.aspx?Repeater=<call>``), city, "Country,
  State", gateway directory (ircDDB, USROOT), and modules C (2 m), B (70 cm),
  A (23 cm voice) and DD (23 cm data), each ``<MHz> <offset>`` - ``RPS`` for
  the data module. "Info" and "Register" links carry the club and gateway
  registration URLs.
* ``apps.dstarinfo.com/Repeater.aspx?Repeater=<call>`` - one repeater's site
  and coverage descriptions, sponsor, URLs, time zone and created/updated
  dates. No coordinates.
* ``appserver.dstarinfo.com/downloads/nearest.aspx`` - the repeater list for a
  DR-mode radio: the repeaters nearest a point, FM and D-STAR, with position,
  duplex, offset and tone. Its FM rows are RepeaterBook's data ("US, Canada,
  and Mexico FM Repeater Data is compliments of RepeaterBook").
  :class:`DStarInfoFmSource` downloads it with "Percent FM" at 100 - the 2,500
  FM repeaters nearest home, out to about 730 miles - for the operator's
  personal use. It is opt-in (it runs only when named), its data stays in the
  ignored local cache, and it is not the RepeaterBook API path
  (:mod:`wasds150.sources.repeaterbook`).

Every page carries DSTARInfo's terms: "Information provided for personal use
only. Commerical use is prohibited. Compilation Copyright DSTARInfo." The pages
are cached locally for the operator's own radios and never committed or
republished; the owner email on a detail page is not kept.

Facts are one per module with a frequency (``station``), keyed
``dstarinfo:<call>:<module>``, and one per FM repeater, keyed
``dstarinfo_fm:<call>:<output>``. No list consumes either yet
(:data:`wasds150.recipes.systems.SOURCE_HOMES`): they are the reference the
TH-D75 and ID-52A D-STAR lists are checked against.
"""
from __future__ import annotations

import csv
import datetime
import html
import io
import re
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

from wasds150.cache.http import FetchError
from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizedFact, NormalizeResult

LIST_URL = "http://apps.dstarinfo.com/D-STAR_Repeater_List.aspx"
DETAIL_URL = "http://apps.dstarinfo.com/Repeater.aspx?Repeater={call}"
#: The ``Countries1`` options, verbatim.
AREAS: Tuple[str, ...] = (
    "Africa", "Asia", "Australia", "Canada", "Europe - Eastern", "Europe - Northern", "Europe - Southern",
    "Europe - Western", "Germany", "India", "Islands", "Italy", "Japan", "Latin America", "Middle East", "Oceania",
    "Sweden", "United Kingdom", "USA Midwest", "USA Northeast", "USA Southeast", "USA West",
)
#: Where a repeater's detail page is fetched too: the operator's region.
DETAIL_REGIONS: Tuple[str, ...] = (
    "United States, Washington", "United States, Oregon", "United States, Idaho", "Canada, British Columbia",
)
#: The directory changes when an owner edits a record; weekly is plenty.
LIST_TTL_SECONDS = 7 * 24 * 3600
DETAIL_TTL_SECONDS = 30 * 24 * 3600
#: Module letter and the mode a radio needs for it.
MODULES: Tuple[Tuple[str, str], ...] = (("C", "DV"), ("B", "DV"), ("A", "DV"), ("DD", "DD"))
_NOT_KEPT = frozenset({"Information_Email"})

_ROW = re.compile(r"(?s)<tr[^>]*>(.*?)</tr>")
_LIST_SPAN = re.compile(r'(?s)<span id="ListView1_(\w+?)Label_\d+"[^>]*>(.*?)</span>')
_DETAIL_SPAN = re.compile(r'(?s)<span id="DataList1_(\w+?)Label_\d+"[^>]*>(.*?)</span>')
_CALL = re.compile(r'Repeater\.aspx\?Repeater=([^"&]+)"')
_LINK = re.compile(r'(?s)<a href="([^"]+)"[^>]*>\s*(Info|Register)\s*</a>')
#: ``443.0625 +5.0000``, ``1247.0000 RPS``, and the odd ``145.6750 - 0.6000``.
_MODULE = re.compile(r"^(\d+(?:\.\d+)?)(?:\s+(RPS|[+-]?\s*\d*\.?\d+))?$", re.IGNORECASE)


def _text(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", value)).split())


def parse_directory(page: str) -> List[Dict[str, Any]]:
    """The repeaters of one area's directory page."""
    rows: List[Dict[str, Any]] = []
    for body in _ROW.findall(page):
        call = _CALL.search(body)
        if call is None:
            continue
        spans = {name: _text(value) for name, value in _LIST_SPAN.findall(body)}
        links = {kind.lower(): url for url, kind in _LINK.findall(body)}
        rows.append({
            "call": urllib.parse.unquote(call.group(1)).strip().upper(),
            "city": spans.get("City", ""),
            "country_state": spans.get("CountryState", ""),
            "directories": [d for d in (spans.get("ircDDBText", ""), spans.get("USROOTText", "")) if d],
            "modules": {module: spans.get(f"{module}_Mod", "") for module, _mode in MODULES},
            "info_url": links.get("info", ""),
            "register_url": links.get("register", ""),
        })
    return rows


def parse_detail(page: str) -> Dict[str, str]:
    """A repeater's detail page, label -> text (without the owner's email)."""
    return {name: _text(value) for name, value in _DETAIL_SPAN.findall(page) if name not in _NOT_KEPT}


def parse_module(cell: str) -> Optional[Tuple[float, Optional[float], str]]:
    """``(output MHz, offset MHz or None, note)`` from a module cell, ``None``
    when unreadable. ``RPS`` is the data module's simplex; an offset written
    without a sign has no direction, so it is not guessed."""
    match = _MODULE.match(cell.strip())
    if match is None:
        return None
    frequency = float(match.group(1))
    offset_text = match.group(2)
    if offset_text is not None:
        offset_text = offset_text.replace(" ", "")
    if offset_text is None:
        return frequency, None, "no offset published"
    if offset_text.upper() == "RPS":
        return frequency, None, "RPS: simplex data"
    value = float(offset_text)
    if offset_text[0] not in "+-" and value != 0.0:
        return frequency, None, f"offset {offset_text} published without a direction"
    return frequency, value, ""


class DStarInfoSource(OnlineSourceAdapter):
    name = "dstarinfo"
    available = True
    kind = "facts"

    def __init__(
        self,
        areas: Tuple[str, ...] = AREAS,
        detail_regions: Tuple[str, ...] = DETAIL_REGIONS,
        list_ttl_seconds: int = LIST_TTL_SECONDS,
        detail_ttl_seconds: int = DETAIL_TTL_SECONDS,
    ):
        self.areas = areas
        self.detail_regions = detail_regions
        self.list_ttl_seconds = list_ttl_seconds
        self.detail_ttl_seconds = detail_ttl_seconds

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        if http_client is None:
            raise ValueError(f"{self.name} requires an http_client")
        areas: Dict[str, str] = {}
        details: Dict[str, str] = {}
        errors: List[str] = []
        for area in self.areas:
            # One area failing must not lose the other twenty-one.
            try:
                result = http_client.fetch_form(
                    LIST_URL, fields={"Countries1": area}, event_target="Countries1",
                    cache_key=f"{LIST_URL}#Countries1={area}",
                    ttl_seconds=self.list_ttl_seconds, source_id=self.name,
                )
            except (FetchError, OSError) as exc:
                errors.append(f"{area}: {exc}")
                continue
            areas[area] = result.content.decode("utf-8", errors="replace")
        if not areas:
            raise RuntimeError("no DSTARInfo area could be fetched: " + "; ".join(errors))
        calls = sorted({
            row["call"] for page in areas.values() for row in parse_directory(page)
            if row["country_state"] in self.detail_regions
        })
        for call in calls:
            try:
                result = http_client.fetch(
                    DETAIL_URL.format(call=urllib.parse.quote(call)),
                    ttl_seconds=self.detail_ttl_seconds, source_id=self.name,
                )
            except (FetchError, OSError) as exc:
                errors.append(f"{call} details: {exc}")
                continue
            details[call] = result.content.decode("utf-8", errors="replace")
        return RawDoc(
            source_adapter=self.name,
            payload={"areas": areas, "details": details, "errors": errors},
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        payload = raw.payload if isinstance(raw.payload, dict) else {}
        details = payload.get("details") or {}
        facts: List[NormalizedFact] = []
        warnings: List[str] = list(payload.get("errors") or [])
        seen = set()
        for area, page in (payload.get("areas") or {}).items():
            for row in parse_directory(page):
                call = row["call"]
                detail = parse_detail(details[call]) if call in details else {}
                for module, mode in MODULES:
                    cell = row["modules"].get(module, "")
                    if not cell:
                        continue
                    parsed = parse_module(cell)
                    if parsed is None:
                        warnings.append(f"{call} module {module}: unreadable {cell!r}")
                        continue
                    key = f"dstarinfo:{call}:{module}"
                    if key in seen:
                        continue  # the directory lists some repeaters twice
                    seen.add(key)
                    frequency, offset, note = parsed
                    facts.append(NormalizedFact(
                        entity_key=key,
                        fact_type="station",
                        name=f"{call} {module} ({row['city']})" if row["city"] else f"{call} {module}",
                        freq_mhz=frequency,
                        offset_mhz=offset,
                        tx_freq_mhz=round(frequency + offset, 6) if offset is not None else None,
                        mode=mode,
                        source_id=self.name,
                        source_url=DETAIL_URL.format(call=urllib.parse.quote(call)),
                        retrieved_at=raw.fetched_at,
                        raw={
                            "call": call,
                            "module": module,
                            "module_text": cell,
                            "offset_note": note,
                            # The routing a D-STAR memory needs; the data module has none.
                            "rpt1": f"{call:<7}{module}" if len(module) == 1 else "",
                            "rpt2": f"{call:<7}G" if len(module) == 1 else "",
                            "city": row["city"],
                            "country_state": row["country_state"],
                            "directories": row["directories"],
                            "info_url": row["info_url"],
                            "register_url": row["register_url"],
                            "area": area,
                            "details": detail,
                        },
                    ))
        return NormalizeResult(facts=facts, warnings=warnings)


NEAREST_URL = "http://appserver.dstarinfo.com/downloads/nearest.aspx"
#: A radio whose DR list holds 2,500 entries (the TH-D74's holds 1,500).
DR_RADIO = "ID-52A"
FM_TTL_SECONDS = 7 * 24 * 3600
#: The DR list's ``TONE`` column -> (the tone is sent, the tone is required to hear).
_TONE_MODES = {"TONE": (True, False), "TSQL": (True, True)}
DR_HEADER = "Group No,"


def _signed_offset(dup: str, offset: str) -> Optional[float]:
    try:
        value = float(offset)
    except ValueError:
        return None
    direction = dup.strip().upper()
    if direction == "DUP+":
        return value
    if direction == "DUP-":
        return -value
    return 0.0


def _position(row: Dict[str, str]) -> Tuple[Optional[float], Optional[float]]:
    try:
        lat, lon = float(row.get("Latitude") or ""), float(row.get("Longitude") or "")
    except ValueError:
        return None, None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None, None  # some rows have the two swapped
    return lat, lon


class DStarInfoFmSource(OnlineSourceAdapter):
    """The FM repeaters nearest home, from DSTARInfo's DR repeater list.

    The rows are RepeaterBook's data, passed on by DSTARInfo for radio
    programming; kept for the operator's personal use only. Opt-in: fetched
    only when named, never by an update of every source."""

    name = "dstarinfo_fm"
    available = True
    kind = "facts"
    opt_in = True

    def __init__(
        self,
        points: Optional[Tuple[Tuple[float, float], ...]] = None,
        radio: str = DR_RADIO,
        ttl_seconds: int = FM_TTL_SECONDS,
    ):
        if points is None:
            from wasds150.plans.template import HOME

            points = (HOME,)
        self.points = points
        self.radio = radio
        self.ttl_seconds = ttl_seconds

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        if http_client is None:
            raise ValueError(f"{self.name} requires an http_client")
        files: Dict[str, str] = {}
        errors: List[str] = []
        for lat, lon in self.points:
            point = f"{lat:.4f},{lon:.4f}"
            try:
                result = http_client.fetch_form(
                    NEAREST_URL,
                    fields={"TextBox2": f"{lat:.4f}", "TextBox3": f"{lon:.4f}", "tbEmptySlots": "0"},
                    steps=(
                        # The placeholder's value starts with a space; anything
                        # else fails the page's event validation.
                        ("", {"bGeoLocate": "Lookup Location", "ddlRadio": " Select Radio"}),
                        ("ddlRadio", {"ddlRadio": self.radio}),
                        ("", {"ddlRadio": self.radio, "tbPercent": "100", "bDownload": "Download"}),
                    ),
                    cache_key=f"{NEAREST_URL}#{point}:{self.radio}:fm100",
                    ttl_seconds=self.ttl_seconds,
                    source_id=self.name,
                )
            except (FetchError, OSError) as exc:
                errors.append(f"{point}: {exc}")
                continue
            files[point] = result.content.decode("utf-8", errors="replace")
        if not files:
            raise RuntimeError("no DSTARInfo repeater list could be downloaded: " + "; ".join(errors))
        return RawDoc(
            source_adapter=self.name,
            payload={"files": files, "errors": errors},
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        payload = raw.payload if isinstance(raw.payload, dict) else {}
        facts: List[NormalizedFact] = []
        warnings: List[str] = list(payload.get("errors") or [])
        seen = set()
        for point, text in (payload.get("files") or {}).items():
            if not text.lstrip("﻿").startswith(DR_HEADER):
                warnings.append(f"{point}: the download is not a repeater list")
                continue
            for row in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
                if (row.get("Mode") or "").strip().upper() != "FM":
                    continue  # the D-STAR rows come from the directory itself
                call = (row.get("Repeater Call Sign") or "").strip().upper()
                try:
                    frequency = float(row.get("Frequency") or "")
                except ValueError:
                    warnings.append(f"{call}: unreadable frequency {row.get('Frequency')!r}")
                    continue
                key = f"dstarinfo_fm:{call}:{frequency:.4f}"
                if key in seen:
                    continue
                seen.add(key)
                offset = _signed_offset(row.get("Dup") or "", row.get("Offset") or "")
                tone_mode = (row.get("TONE") or "").strip().upper()
                sends, required = _TONE_MODES.get(tone_mode, (False, False))
                hertz = re.sub(r"[^\d.]", "", row.get("Repeater Tone") or "")
                access = f"TONE=C{float(hertz):g}" if sends and hertz else ""
                lat, lon = _position(row)
                place = ", ".join(part for part in ((row.get("Name") or "").strip(), (row.get("Sub Name") or "").strip()) if part)
                facts.append(NormalizedFact(
                    entity_key=key,
                    fact_type="station",
                    name=f"{call} ({place})" if place else call,
                    freq_mhz=frequency,
                    offset_mhz=offset,
                    tx_freq_mhz=round(frequency + offset, 6) if offset is not None else None,
                    tone=access if required else None,
                    mode="FM",
                    lat=lat,
                    lon=lon,
                    location_precision="fuzzed" if lat is not None else "unknown",
                    source_id=self.name,
                    source_url=NEAREST_URL,
                    retrieved_at=raw.fetched_at,
                    raw={
                        **{column: value for column, value in row.items() if column},
                        "tx_tone": access,
                        "tone_note": "DCS with no code in the download" if tone_mode in ("DTCS", "**DCOD") else "",
                        "point": point,
                        "data_origin": "RepeaterBook, via DSTARInfo's DR repeater list (personal use only)",
                    },
                ))
        return NormalizeResult(facts=facts, warnings=warnings)
