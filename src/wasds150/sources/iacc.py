"""IACC (Inland Amateur Coordination Council) — Eastern WA / North Idaho
amateur repeater coordination.

**Confirmed live during implementation** — correcting an earlier research
pass's assumption: ``https://www.iacc.online/?mm=repeaters`` **does**
contain a real, parseable HTML ``<table>`` (308 coordinated repeaters at
fetch time), not an unstructured/image-only listing as initially assumed.
Columns confirmed: ``Details, Output, Offset, Reg, "State, County City",
Callsign, CTCSS/DCS, Features``, with band-section header rows (e.g. "6m
Band - VHF Low Band") interspersed as single-cell rows to skip, and every
listed state mixed together (Eastern WA + North Idaho) — filtered here to
``State, County City`` starting with ``"WA,"``.

IACC is the coordinator of record for Eastern Washington (east of the
Cascades) and North Idaho, the counterpart to WWARA for Western WA. Per
this project's existing conflict-resolution framework
(``docs/data-sources.md``: "Amateur-radio coordinator records" outrank
generic aggregators), this is the authoritative source for that region's
repeater frequencies. As with WWARA, this data is cached locally and used
to derive facts for the user's own generated catalog (frequency, offset,
tone, callsign, county/city, coordination status) — not wholesale
republished as a competing coordination database.
"""
from __future__ import annotations

import datetime
from typing import Any, List, Optional, Tuple

from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizedFact, NormalizeResult
from wasds150.sources.htmlutil import extract_tables

REPEATERS_URL = "https://www.iacc.online/?mm=repeaters"
#: Repeaters database is regenerated on each coordination action; check daily.
DEFAULT_TTL_SECONDS = 24 * 3600

_EXPECTED_HEADER = ["Details", "Output", "Offset", "Reg", "State, County City", "Callsign", "CTCSS/DCS", "Features"]


def _parse_state_county_city(value: str) -> Tuple[str, str, str]:
    """``"WA, Okanogan Twisp"`` -> ``("WA", "Okanogan", "Twisp")``."""
    state, _, rest = value.partition(",")
    rest = rest.strip()
    parts = rest.split(" ", 1)
    county = parts[0] if parts else ""
    city = parts[1] if len(parts) > 1 else ""
    return state.strip(), county, city


class IaccSource(OnlineSourceAdapter):
    name = "iacc"
    available = True
    kind = "facts"

    def __init__(self, state: str = "WA", url: str = REPEATERS_URL, ttl_seconds: int = DEFAULT_TTL_SECONDS):
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
        tables = extract_tables(raw.payload)
        facts: List[NormalizedFact] = []
        warnings: List[str] = []

        data_table = None
        for table in tables:
            if any(row == _EXPECTED_HEADER for row in table):
                data_table = table
                break
        if data_table is None:
            warnings.append("could not find the IACC repeater data table (expected header row not found)")
            return NormalizeResult(facts=facts, warnings=warnings)

        for row in data_table:
            if row == _EXPECTED_HEADER or len(row) < 5 or not row[4] or "," not in row[4]:
                continue  # band-section header or non-data row
            _details, output, offset, reg, location, callsign, tone, features = (row + [""] * 8)[:8]
            state, county, city = _parse_state_county_city(location)
            if state != self.state:
                continue
            try:
                freq = float(output)
            except ValueError:
                warnings.append(f"{callsign}: could not parse output frequency {output!r}")
                continue
            try:
                offset_mhz = float(offset)
            except ValueError:
                offset_mhz = None
            entity_key = f"iacc:{callsign}:{output}" if callsign else f"iacc:{output}:{county}:{city}"
            facts.append(
                NormalizedFact(
                    entity_key=entity_key,
                    fact_type="coordination",
                    name=f"{callsign} ({city}, {county} Co.)" if callsign else f"{city}, {county} Co.",
                    freq_mhz=freq,
                    offset_mhz=offset_mhz,
                    tone=tone or None,
                    mode="FM",
                    county=county or None,
                    location_precision="unknown",
                    source_id=self.name,
                    source_url=self.url,
                    retrieved_at=raw.fetched_at,
                    raw={
                        "callsign": callsign,
                        "reg": reg,
                        "city": city,
                        "features": features,
                    },
                )
            )
        return NormalizeResult(facts=facts, warnings=warnings)
