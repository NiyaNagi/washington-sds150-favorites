"""Shared fact/alert shapes produced by the online source adapters in
:mod:`wasds150.sources` (NOAA, USCG, AMSAT, NWAC, WWARA, IACC, FAA NASR,
FCC ULS, WA EMD/DNR, NIFC).

Kept adapter-agnostic and independent of the canonical
:mod:`wasds150.models.catalog` hierarchy on purpose: many sources produce
facts that only make sense combined with facts from *other* sources (a
repeater's frequency from WWARA, grouped with a county boundary from FCC
ULS, say) — that combination is :mod:`wasds150.recipes`' job, not any one
adapter's. Adapters stay simple: raw source data in, a flat list of
:class:`NormalizedFact`/:class:`ChangeAlert` out.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

#: "frequency" — a single frequency/channel fact (repeater, station, airport
#:   comm, marine channel, weather transmitter, satellite).
#: "coordination" — an amateur-radio coordination record (WWARA/IACC).
#: "channel_plan" — a reference table entry (USCG VHF channel plan).
#: "doc_ref" — a citation-only fact (a linked PDF/document, no extracted
#:   frequencies) — typically paired with a :class:`ChangeAlert`.
FACT_TYPES = ("frequency", "system", "site", "station", "coordination", "channel_plan", "doc_ref")

#: How precise ``lat``/``lon`` are. WWARA explicitly fuzzes some repeater
#: coordinates (to ~50 miles) at the owner's request — never present a
#: fuzzed coordinate as exact.
LOCATION_PRECISION = ("exact", "fuzzed", "unknown")


@dataclass
class NormalizedFact:
    entity_key: str
    fact_type: str
    name: str = ""
    freq_mhz: Optional[float] = None
    offset_mhz: Optional[float] = None
    tone: Optional[str] = None
    mode: Optional[str] = None
    county: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    location_precision: str = "unknown"
    source_id: str = ""
    source_url: str = ""
    source_updated: Optional[str] = None
    retrieved_at: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.fact_type not in FACT_TYPES:
            raise ValueError(f"fact_type must be one of {FACT_TYPES}, got {self.fact_type!r}")
        if self.location_precision not in LOCATION_PRECISION:
            raise ValueError(f"location_precision must be one of {LOCATION_PRECISION}")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChangeAlert:
    """"A document changed" signal for link-only sources (WA EMD/SIEC, WA
    DNR, NIFC) that intentionally do not attempt automated fact extraction
    from PDFs — see each adapter's module docstring for why."""

    source_id: str
    doc_id: str
    url: str
    #: "new" | "changed" | "unchanged"
    kind: str
    message: str = ""
    detected_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizeResult:
    facts: List[NormalizedFact] = field(default_factory=list)
    alerts: List[ChangeAlert] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": [f.to_dict() for f in self.facts],
            "alerts": [a.to_dict() for a in self.alerts],
            "warnings": list(self.warnings),
        }
