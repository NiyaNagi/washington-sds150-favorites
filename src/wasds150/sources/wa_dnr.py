"""WA DNR wildfire radio operations — document change detection.

**Confirmed live URL**: ``https://dnr.wa.gov/wildfire-resources/fighting-fire/fire-business-and-incident-management/dnr-radio-operations``.
Direct PDF assets confirmed present: ``rp_fire_radio_channel_guide.pdf``,
``rp_fire_radio_agreement.pdf``, ``rp_fire_radio_repeater_map.pdf``, etc.,
all under a dated folder (``/sites/default/files/<YYYY-MM>/...``) that
changes whenever DNR republishes — confirmed live during implementation.

Same PDF-text-extraction limitation as :mod:`wasds150.sources.wa_emd` —
link-discovery + change-detection only, never automated fact extraction.
"""
from __future__ import annotations

import datetime
from typing import Any, Optional

from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.docwatch import check_document_links, discover_document_links
from wasds150.sources.facts import NormalizeResult

DNR_LANDING_URL = (
    "https://dnr.wa.gov/wildfire-resources/fighting-fire/"
    "fire-business-and-incident-management/dnr-radio-operations"
)
#: Pre-fire-season check in spring is the important one.
DEFAULT_TTL_SECONDS = 90 * 24 * 3600


class WaDnrSource(OnlineSourceAdapter):
    name = "wa_dnr"
    available = True
    kind = "change_detection"

    def __init__(self, landing_url: str = DNR_LANDING_URL, ttl_seconds: int = DEFAULT_TTL_SECONDS):
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
        links = discover_document_links(html, base_url=self.landing_url, pattern="rp_fire_radio_")
        alerts = check_document_links(http_client, links, source_id=self.name, ttl_seconds=self.ttl_seconds)
        return NormalizeResult(facts=[], alerts=alerts)
