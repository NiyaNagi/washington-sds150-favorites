"""RadioReference Premium — safe, user-supplied-export-only integration.

**No scraping, no redistribution, no unverified SOAP calls.** This project
does not bulk-scrape RadioReference's public pages and does not implement
RadioReference's SOAP "Premium/API" programming-data service, because that
service's exact request/response contract has **not been independently
verified against real traffic in this project** (it requires an active
Premium subscription + an app key issued to a registered client
application — neither of which this session has). Rather than guess at a
SOAP client against unverified documentation and risk silently producing
wrong data (or violating RR's API terms), this adapter supports exactly
one thing today:

**Importing a file the user has already lawfully exported from their own
RadioReference Premium account** (RR's site lets a logged-in Premium
subscriber download a county/agency's data as CSV, and RR's Uniden-specific
tools can export DAT/XML for SDS-series radios). The user obtains the file
themselves, in their own browser, under their own subscription's terms;
this adapter only ever reads a local file the user points it at — never
touches the network.

Because the *exact* column/element names of a Premium export are not
independently byte-verified in this project (no fixture was legally
obtainable without an active subscription), the CSV/XML parsing below is
deliberately **tolerant and best-effort**: it reads whatever header/tag
names are present, maps the small set of names publicly documented as
stable (``County``, ``Agency``/``System``, ``Site``, ``Description``,
``Tag``/``Alpha Tag``, ``Frequency``/``Freq``, ``Tone``, ``Category``) when
found, and otherwise preserves every column verbatim in ``raw`` rather than
dropping it — the same "generic lossless" philosophy used by
:mod:`wasds150.hpe.record` for the on-card binary formats. A warning is
always emitted reminding the caller to review the mapped output before
trusting it in a generated bundle.

**Credentials / SOAP hook**: :class:`RadioReferenceCredentials` exists so a
future, *verified* SOAP client can be added later without changing this
adapter's public shape. Calling :meth:`RadioReferencePremiumSource.fetch`
with credentials configured but no ``export_path`` raises
:class:`RadioReferenceSoapNotImplemented` with a precise, actionable
message — it never pretends to make a live API call it hasn't verified.
Credentials are never logged (see ``__repr__``/``__str__`` overrides
below) and are never written into any generated bundle or provenance
record — only ``source_id="radioreference_premium"`` plus the *local*
export filename are recorded.
"""
from __future__ import annotations

import csv
import datetime
import io
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizedFact, NormalizeResult

#: Publicly documented (RadioReference help pages / long-standing Premium
#: CSV export column names) but NOT independently byte-verified against a
#: real export file in this project -- kept as a best-effort alias table,
#: matched case-insensitively, never assumed complete.
_CSV_COLUMN_ALIASES = {
    "county": ("county",),
    "system": ("system", "agency", "system/agency"),
    "site": ("site", "site description", "site name"),
    "name": ("description", "alpha tag", "tag", "name"),
    "freq_mhz": ("frequency output", "frequency", "freq", "output freq"),
    "tone": ("tone", "ctcss/dcs", "input tone"),
    "category": ("category", "service type", "mode"),
}


class RadioReferenceSoapNotImplemented(NotImplementedError):
    """Raised instead of attempting an unverified live SOAP call."""


@dataclass
class RadioReferenceCredentials:
    """Config hook for a *future* verified SOAP client. Never logged --
    ``__repr__`` intentionally redacts every field."""

    username: str = ""
    password: str = ""
    app_key: str = ""

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "RadioReferenceCredentials(<redacted>)"

    __str__ = __repr__

    def is_configured(self) -> bool:
        return bool(self.username and self.password and self.app_key)


def _match_alias(header: str) -> Optional[str]:
    lowered = header.strip().lower()
    for canonical, aliases in _CSV_COLUMN_ALIASES.items():
        if lowered in aliases:
            return canonical
    return None


def _parse_csv_export(text: str, *, retrieved_at: str) -> NormalizeResult:
    reader = csv.DictReader(io.StringIO(text))
    facts: List[NormalizedFact] = []
    warnings: List[str] = [
        "radioreference_premium CSV column mapping is best-effort/unverified; "
        "review mapped facts before trusting them in a generated bundle"
    ]
    if not reader.fieldnames:
        warnings.append("export file has no header row; nothing imported")
        return NormalizeResult(facts=facts, warnings=warnings)

    alias_by_header = {h: _match_alias(h) for h in reader.fieldnames}
    for i, row in enumerate(reader):
        mapped: Dict[str, Any] = {}
        for header, value in row.items():
            canonical = alias_by_header.get(header)
            if canonical:
                mapped[canonical] = value
        freq_mhz = None
        if mapped.get("freq_mhz"):
            try:
                freq_mhz = float(str(mapped["freq_mhz"]).strip())
            except ValueError:
                pass
        name = mapped.get("name") or mapped.get("system") or f"row-{i}"
        entity_key = f"rr_premium:{mapped.get('system', '')}:{mapped.get('site', '')}:{i}"
        facts.append(
            NormalizedFact(
                entity_key=entity_key,
                fact_type="frequency" if freq_mhz is not None else "system",
                name=str(name),
                freq_mhz=freq_mhz,
                tone=mapped.get("tone") or None,
                county=mapped.get("county") or None,
                location_precision="unknown",
                source_id="radioreference_premium",
                source_url="",
                retrieved_at=retrieved_at,
                raw=dict(row),
            )
        )
    return NormalizeResult(facts=facts, warnings=warnings)


def _local_tag(elem: ET.Element) -> str:
    tag = elem.tag
    return tag.split("}", 1)[1] if "}" in tag else tag


def _parse_xml_export(text: str, *, retrieved_at: str) -> NormalizeResult:
    warnings: List[str] = [
        "radioreference_premium XML element mapping is best-effort/unverified; "
        "review mapped facts before trusting them in a generated bundle"
    ]
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return NormalizeResult(facts=[], warnings=warnings + [f"could not parse XML export: {exc}"])

    facts: List[NormalizedFact] = []
    # Best-effort: treat any leaf-bearing element with a recognizable child
    # (by local-name alias) as one record; preserve every child verbatim.
    for i, elem in enumerate(root.iter()):
        children = list(elem)
        if not children:
            continue
        record: Dict[str, str] = {}
        for child in children:
            if list(child):  # skip further-nested containers
                continue
            record[_local_tag(child)] = (child.text or "").strip()
        if not record:
            continue
        mapped: Dict[str, Any] = {}
        for key, value in record.items():
            canonical = _match_alias(key)
            if canonical:
                mapped[canonical] = value
        if not mapped:
            continue
        freq_mhz = None
        if mapped.get("freq_mhz"):
            try:
                freq_mhz = float(str(mapped["freq_mhz"]).strip())
            except ValueError:
                pass
        name = mapped.get("name") or mapped.get("system") or f"{_local_tag(elem)}-{i}"
        entity_key = f"rr_premium:{_local_tag(elem)}:{i}"
        facts.append(
            NormalizedFact(
                entity_key=entity_key,
                fact_type="frequency" if freq_mhz is not None else "system",
                name=str(name),
                freq_mhz=freq_mhz,
                tone=mapped.get("tone") or None,
                county=mapped.get("county") or None,
                location_precision="unknown",
                source_id="radioreference_premium",
                source_url="",
                retrieved_at=retrieved_at,
                raw=record,
            )
        )
    if not facts:
        warnings.append("no recognizable records found in XML export")
    return NormalizeResult(facts=facts, warnings=warnings)


class RadioReferencePremiumSource(OnlineSourceAdapter):
    name = "radioreference_premium"
    available = True
    kind = "local"

    def __init__(
        self,
        export_path: Optional[Path] = None,
        credentials: Optional[RadioReferenceCredentials] = None,
    ):
        self.export_path = Path(export_path) if export_path is not None else None
        self.credentials = credentials

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        # kind == "local": never uses http_client, even if one is passed.
        if self.export_path is not None:
            if not self.export_path.is_file():
                raise FileNotFoundError(f"radioreference_premium export file not found: {self.export_path}")
            text = self.export_path.read_bytes().decode("utf-8-sig", errors="replace")
            fmt = "xml" if self.export_path.suffix.lower() == ".xml" else "csv"
            return RawDoc(
                source_adapter=self.name,
                payload={"format": fmt, "text": text, "filename": self.export_path.name},
                fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
        if self.credentials is not None and self.credentials.is_configured():
            raise RadioReferenceSoapNotImplemented(
                "radioreference_premium: a live SOAP 'Premium/API' call was requested, but this "
                "project has not independently verified RadioReference's SOAP request/response "
                "contract against real traffic, so no live call is attempted (to avoid silently "
                "producing wrong data or violating RR's API terms). Instead, export your data from "
                "your own radioreference.com Premium account (county/agency CSV, or a Uniden "
                "DAT/XML export) and pass it as export_path= to this source. See docs/data-sources.md "
                "for the current supported workflow."
            )
        return RawDoc(
            source_adapter=self.name,
            payload=None,
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        if raw.payload is None:
            return NormalizeResult(
                facts=[],
                warnings=["no radioreference_premium export_path configured; no facts produced"],
            )
        fmt = raw.payload["format"]
        text = raw.payload["text"]
        if fmt == "xml":
            return _parse_xml_export(text, retrieved_at=raw.fetched_at)
        return _parse_csv_export(text, retrieved_at=raw.fetched_at)
