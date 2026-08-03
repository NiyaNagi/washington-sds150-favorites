"""NOAA Weather Radio (NWR) / SAME transmitter source.

**Confirmed live source** (fetched directly during implementation): NWS's
own station-finder page (``weather.gov/nwr/stations?State=WA``) is
JavaScript-rendered from a plain, unauthenticated JS file —
``https://www.weather.gov/source/nwr/JS/ccl-data.js`` — containing
``var cclData = [...]`` : a nationwide JSON array (confirmed 1000+ entries
at fetch time), each station shaped exactly like::

    {"callsign": "KEC64", "sitename": "Seattle", "siteloc": "King",
     "sitestate": "WA", "freq": "162.550", "lat": "47.5", "lon": "-122.3",
     "status": "NORMAL", "power": "300", "wfo": "Seattle|WA",
     "counties": [{"county": "King", "same": "053033", "st": "WA",
                    "state": "Washington", "remarks": ""}, ...]}

This is a far more reliable integration point than scraping the rendered
HTML table (which requires executing the page's JS) — this module fetches
and parses the JS file directly (strip the ``var cclData = ...;`` wrapper,
``json.loads`` the rest), filtering to ``sitestate == "WA"``.

Public domain (US federal work) — fully ingestible/redistributable, no
attribution legally required.
"""
from __future__ import annotations

import datetime
import json
import re
from typing import Any, Dict, List, Optional

from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizedFact, NormalizeResult

CCL_DATA_URL = "https://www.weather.gov/source/nwr/JS/ccl-data.js"
#: Transmitter buildout changes rarely; re-check quarterly.
DEFAULT_TTL_SECONDS = 90 * 24 * 3600

_CCL_DATA_RE = re.compile(r"var\s+cclData\s*=\s*(\[.*\])\s*;?\s*$", re.DOTALL)


def parse_ccl_data_js(text: str) -> List[Dict[str, Any]]:
    match = _CCL_DATA_RE.search(text.strip())
    if not match:
        raise ValueError("could not find 'var cclData = [...]' in ccl-data.js response")
    return json.loads(match.group(1))


class NoaaNwrSource(OnlineSourceAdapter):
    name = "noaa_nwr"
    available = True
    kind = "facts"

    def __init__(self, state: str = "WA", url: str = CCL_DATA_URL, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.state = state
        self.url = url
        self.ttl_seconds = ttl_seconds

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        if http_client is None:
            raise ValueError(f"{self.name} requires an http_client")
        result = http_client.fetch(self.url, ttl_seconds=self.ttl_seconds, source_id=self.name)
        return RawDoc(
            source_adapter=self.name,
            payload=result.content.decode("utf-8"),
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        stations = parse_ccl_data_js(raw.payload)
        facts: List[NormalizedFact] = []
        warnings: List[str] = []
        for station in stations:
            if station.get("sitestate") != self.state:
                continue
            callsign = station.get("callsign", "")
            try:
                freq = float(station["freq"]) if station.get("freq") else None
            except ValueError:
                freq = None
                warnings.append(f"{callsign}: could not parse frequency {station.get('freq')!r}")
            try:
                lat = float(station["lat"]) if station.get("lat") else None
                lon = float(station["lon"]) if station.get("lon") else None
            except ValueError:
                lat = lon = None
            county = station.get("siteloc") or None
            facts.append(
                NormalizedFact(
                    entity_key=f"noaa_nwr:{callsign}",
                    fact_type="station",
                    name=f"NOAA Weather Radio {station.get('sitename', callsign)}",
                    freq_mhz=freq,
                    mode="FM",
                    county=county,
                    lat=lat,
                    lon=lon,
                    location_precision="exact" if lat is not None else "unknown",
                    source_id=self.name,
                    source_url=f"https://www.weather.gov/nwr/sites?site={callsign}",
                    retrieved_at=raw.fetched_at,
                    raw=station,
                )
            )
        return NormalizeResult(facts=facts, warnings=warnings)
