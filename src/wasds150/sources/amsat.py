"""AMSAT satellite/ISS amateur-radio status API.

**Confirmed live, documented REST API** (fetched directly during
implementation) — not scraping: ``https://www.amsat.org/status/api/v1/catalog.php?include_stats=true``
returns::

    {"data": [{"id": 7, "name": "ISS_[FM]", "display_name": "ISS [FM]",
               "website": "...", "links": {...},
               "report_count": 4565, "latest_reported_time": "2026-08-03T02:30:00Z"}, ...],
     "meta": {"count": 85}}

OpenAPI spec at ``.../openapi.php``; human docs at ``.../docs.php``. The
ARISS status page (``ariss.org/current-status-of-iss-stations.html``) is
JS-rendered and not scriptable with stdlib alone — this AMSAT API is the
actual machine-readable data source; ARISS remains a link-only citation.

Internationally-coordinated amateur frequencies/status are public,
citable facts — no ToS blocker found.
"""
from __future__ import annotations

import datetime
import json
from typing import Any, List, Optional

from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizedFact, NormalizeResult

CATALOG_URL = "https://www.amsat.org/status/api/v1/catalog.php?include_stats=true"
#: ISS mode-of-day can change; re-check daily-ish.
DEFAULT_TTL_SECONDS = 12 * 3600
#: If a satellite's last report is older than this, flag it as stale rather
#: than presenting its "current mode" as trustworthy.
STALE_AFTER_DAYS = 30


class AmsatSource(OnlineSourceAdapter):
    name = "amsat"
    available = True
    kind = "facts"

    def __init__(self, url: str = CATALOG_URL, ttl_seconds: int = DEFAULT_TTL_SECONDS):
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
        payload = json.loads(raw.payload)
        entries = payload.get("data", [])
        facts: List[NormalizedFact] = []
        warnings: List[str] = []
        now = datetime.datetime.now(datetime.timezone.utc)

        for entry in entries:
            catalog_id = entry.get("id")
            name = entry.get("display_name") or entry.get("name", "")
            latest = entry.get("latest_reported_time")
            stale = False
            if latest:
                try:
                    reported = datetime.datetime.fromisoformat(latest.replace("Z", "+00:00"))
                    stale = (now - reported).days > STALE_AFTER_DAYS
                except ValueError:
                    warnings.append(f"{name}: could not parse latest_reported_time {latest!r}")
            note = "status uncertain, verify before pass" if stale else ""
            facts.append(
                NormalizedFact(
                    entity_key=f"amsat:{catalog_id}",
                    fact_type="station",
                    name=name,
                    mode=None,
                    location_precision="unknown",
                    source_id=self.name,
                    source_url=entry.get("website", ""),
                    source_updated=latest,
                    retrieved_at=raw.fetched_at,
                    raw={**entry, "stale": stale, "note": note},
                )
            )
        return NormalizeResult(facts=facts, warnings=warnings)
