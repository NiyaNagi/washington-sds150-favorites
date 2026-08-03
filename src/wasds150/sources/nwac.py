"""NWAC backcountry radio channels — document/graphic change detection.

**Confirmed live during implementation** — correcting the initial research
pass's assumption: ``https://nwac.us/backcountry-radio-channels/`` has
**no parseable ``<table>`` or frequency text at all**. The actual
zone-to-FRS-channel mapping is published only as a static infographic image
(``NWAC_RadioChannelGraphic_v2-1.jpg``, referenced via the page's own
``og:image`` meta tag), with the page's body text only explaining the
notation (e.g. "7-3" = FRS channel 7, tone/code 3) in prose, not listing
actual zone assignments as text.

Since there is no stdlib-feasible way to extract structured data from an
image, this adapter — like the WA EMD/DNR/NIFC PDF sources — does
**link/asset change-detection only**: it tracks the ``og:image`` URL (and
any link whose ``href`` contains "RadioChannel") via
:mod:`wasds150.sources.docwatch`, so a changed graphic surfaces as a
"re-verify the backcountry radio zones" signal for a human, rather than
pretending to extract facts that aren't there.
"""
from __future__ import annotations

import datetime
import re
from typing import Any, List, Optional

from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.docwatch import check_document_links
from wasds150.sources.facts import NormalizeResult

NWAC_PAGE_URL = "https://nwac.us/backcountry-radio-channels/"
#: Seasonal program; force-check pre-winter-season (November).
DEFAULT_TTL_SECONDS = 180 * 24 * 3600

_OG_IMAGE_RE = re.compile(r'<meta\s+property="og:image"\s+content="([^"]+)"', re.IGNORECASE)


class NwacSource(OnlineSourceAdapter):
    name = "nwac"
    available = True
    kind = "change_detection"

    def __init__(self, url: str = NWAC_PAGE_URL, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.url = url
        self.ttl_seconds = ttl_seconds

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        if http_client is None:
            raise ValueError(f"{self.name} requires an http_client")
        result = http_client.fetch(self.url, ttl_seconds=self.ttl_seconds, source_id=self.name)
        return RawDoc(
            source_adapter=self.name,
            payload={"html": result.content.decode("utf-8"), "http_client": http_client},
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        html = raw.payload["html"]
        http_client = raw.payload["http_client"]
        warnings: List[str] = []

        links: List[str] = []
        match = _OG_IMAGE_RE.search(html)
        if match:
            links.append(match.group(1))
        else:
            warnings.append("no og:image meta tag found; NWAC page structure may have changed")

        from wasds150.sources.htmlutil import extract_links

        links.extend(extract_links(html, href_contains="RadioChannel"))
        links = sorted(set(links))

        alerts = check_document_links(http_client, links, source_id=self.name, ttl_seconds=self.ttl_seconds)
        return NormalizeResult(facts=[], alerts=alerts, warnings=warnings)
