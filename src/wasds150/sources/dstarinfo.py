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
* ``appserver.dstarinfo.com/downloads/`` - radio import files built from the
  same directory (memories by region or by location, and the DR repeater
  list). The DR list mixes in RepeaterBook's FM repeaters, which this project
  takes only through the RepeaterBook API (:mod:`wasds150.sources.repeaterbook`),
  so none of these are fetched here.

Every page carries DSTARInfo's terms: "Information provided for personal use
only. Commerical use is prohibited. Compilation Copyright DSTARInfo." The pages
are cached locally for the operator's own radios and never committed or
republished; the owner email on a detail page is not kept.

Facts are one per module with a frequency (``station``), keyed
``dstarinfo:<call>:<module>``. No list consumes them yet
(:data:`wasds150.recipes.systems.SOURCE_HOMES`): they are the reference the
TH-D75 and ID-52A D-STAR lists are checked against.
"""
from __future__ import annotations

import datetime
import html
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
