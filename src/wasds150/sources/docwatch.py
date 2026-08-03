"""Shared "document changed" link-discovery detector.

Several sources (WA EMD/SIEC, WA DNR, NIFC, NWAC) publish frequency/channel
information only inside PDFs or images with no stdlib-parseable text/table
layer available (confirmed directly for NWAC — its backcountry-radio page's
only "data" is an embedded infographic image, not text; the WA EMD/DNR/NIFC
PDFs were already established as text-layer-but-no-stdlib-parser-available
in earlier research). Rather than guess at fragile PDF-byte-stream parsing,
these adapters do **link discovery + change detection only**: find the
linked document(s) on a landing page, and report whether each looks new or
has changed since last checked, so a human can re-review it — never
attempt automated fact extraction from them.

Change detection reuses the HTTP cache's own conditional-GET bookkeeping
rather than tracking separate state: a linked document is fetched (small
size limit, since we only need to detect change, not necessarily keep the
whole PDF) through the same :class:`~wasds150.cache.http.CachedHttpClient`
every other adapter uses. If the cache had no prior entry for that URL, the
document is "new"; if the fetch actually pulled new bytes (``status ==
"fetched"``) for an existing entry, it "changed"; if the server said
``304``/the cache was already fresh, it's "unchanged".
"""
from __future__ import annotations

import datetime
from typing import List

from wasds150.sources.facts import ChangeAlert
from wasds150.sources.htmlutil import extract_links


def discover_document_links(html_text: str, *, base_url: str, pattern: str) -> List[str]:
    """Every absolute/relative link on the page matching ``pattern``
    (a plain substring, not a regex — kept simple/predictable), resolved
    against ``base_url`` if relative."""
    from urllib.parse import urljoin

    hrefs = extract_links(html_text, href_contains=pattern)
    return [urljoin(base_url, h) for h in hrefs]


def check_document_links(
    http_client,
    urls: List[str],
    *,
    source_id: str,
    ttl_seconds: int,
    max_bytes: int = 2 * 1024 * 1024,
) -> List[ChangeAlert]:
    """Fetch each URL (through the shared cache) and classify it as
    new/changed/unchanged based on the cache's own fetch status."""
    alerts: List[ChangeAlert] = []
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for url in urls:
        had_prior_entry = http_client.store.get(url) is not None
        result = http_client.fetch(url, ttl_seconds=ttl_seconds, source_id=source_id, max_bytes=max_bytes)
        if not had_prior_entry:
            kind = "new"
            message = "newly discovered document"
        elif result.status == "fetched":
            kind = "changed"
            message = "document content changed since last check"
        else:
            kind = "unchanged"
            message = "no change detected"
        alerts.append(
            ChangeAlert(source_id=source_id, doc_id=url, url=url, kind=kind, message=message, detected_at=now)
        )
    return alerts
