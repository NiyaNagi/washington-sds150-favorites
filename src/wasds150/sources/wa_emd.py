"""WA Military Department (EMD) / SIEC / SCIP — document change detection.

**Confirmed live URLs** (already cited in this catalog's own docs):
``https://mil.wa.gov/asset/610b02188b53e`` (ESF-4 Appendix 1),
``https://mil.wa.gov/asset/610097d704789`` (ESF-2 Appendix 1). The SIEC
landing page (``https://mil.wa.gov/state-interoperability-executive-committee-siec``)
lists agendas/minutes/SCIP links as ``/asset/<13-hex-char-id>/<name>.pdf``
links — confirmed live and matching this pattern during implementation —
and these ids are **not guessable/predictable**, so they must be
re-discovered from the landing page each run, not hardcoded.

These are **text-layer PDFs with no pure-stdlib text-extraction library
available** (no third-party dependency is in scope for this project) — so
this adapter does **link-discovery + change-detection only**
(:mod:`wasds150.sources.docwatch`), never automated fact extraction. A
detected new/changed asset is a signal for a human to re-read the PDF and
manually update the catalog, not an auto-applied fact.
"""
from __future__ import annotations

import datetime
from typing import Any, Optional

from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.docwatch import check_document_links, discover_document_links
from wasds150.sources.facts import NormalizeResult

SIEC_LANDING_URL = "https://mil.wa.gov/state-interoperability-executive-committee-siec"
#: Landing-page link-discovery check cadence.
DEFAULT_TTL_SECONDS = 30 * 24 * 3600


class WaEmdSource(OnlineSourceAdapter):
    name = "wa_emd"
    available = True
    kind = "change_detection"

    def __init__(self, landing_url: str = SIEC_LANDING_URL, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.landing_url = landing_url
        self.ttl_seconds = ttl_seconds

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        if http_client is None:
            raise ValueError(f"{self.name} requires an http_client")
        result = http_client.fetch(self.landing_url, ttl_seconds=self.ttl_seconds, source_id=self.name)
        return RawDoc(
            source_adapter=self.name,
            payload={"html": result.content.decode("utf-8"), "http_client": http_client},
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        html = raw.payload["html"]
        http_client = raw.payload["http_client"]
        links = discover_document_links(html, base_url=self.landing_url, pattern="/asset/")
        alerts = check_document_links(http_client, links, source_id=self.name, ttl_seconds=self.ttl_seconds)
        return NormalizeResult(facts=[], alerts=alerts)
