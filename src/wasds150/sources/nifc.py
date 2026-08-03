"""NIFC NIRSC User's Guide — document change detection.

**Confirmed URL** (already this catalog's FL7 source, live at implementation
time): ``https://www.nifc.gov/sites/default/files/NIICD/docs/2024_NIRSC_User_Guide_Webview.pdf``.
The filename encodes the year; NIFC's own resources pages are the place a
new year's filename would be discovered — this adapter scrapes a
configurable landing page for ``NIRSC_User_Guide`` links rather than
guessing next year's URL, since NIICD has changed naming conventions
before.

Same PDF-text-extraction limitation as :mod:`wasds150.sources.wa_emd` —
link-discovery + change-detection only. The actual Command/Tac/Air-Guard
frequency tables are historically very stable year to year and are kept as
static catalog entries between guide revisions; a new guide year found here
is a "go re-verify FL7 against the new PDF" signal, not an auto-applied
fact change.
"""
from __future__ import annotations

import datetime
from typing import Any, Optional

from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.docwatch import check_document_links, discover_document_links
from wasds150.sources.facts import NormalizeResult

#: Best-effort default; NIFC's resource-listing structure changes
#: periodically, re-verify this landing page occasionally.
NIFC_LANDING_URL = "https://www.nifc.gov/nicc-files/radio"
#: Force-check every spring before fire season.
DEFAULT_TTL_SECONDS = 180 * 24 * 3600


class NifcSource(OnlineSourceAdapter):
    name = "nifc"
    available = True
    kind = "change_detection"

    def __init__(self, landing_url: str = NIFC_LANDING_URL, ttl_seconds: int = DEFAULT_TTL_SECONDS):
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
        links = discover_document_links(html, base_url=self.landing_url, pattern="NIRSC_User_Guide")
        alerts = check_document_links(http_client, links, source_id=self.name, ttl_seconds=self.ttl_seconds)
        warnings = []
        if not links:
            warnings.append(
                f"no 'NIRSC_User_Guide' links found on {self.landing_url}; "
                "the landing page URL may need re-verifying"
            )
        return NormalizeResult(facts=[], alerts=alerts, warnings=warnings)
