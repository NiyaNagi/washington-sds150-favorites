"""Provenance tracking: where did a catalog fact come from, and how much do
we trust it.

Only ``static_pack`` (the checked-in CSV/MD catalog) is populated by phases
1-4. The ``confidence`` vocabulary and field names are chosen to match what
the future online source adapters (RadioReference, RepeaterBook, NOAA, ...)
will also produce, so :mod:`wasds150.merge` can treat every source uniformly
once it is implemented.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

#: Confidence vocabulary shared with the (not-yet-implemented) merge engine.
CONFIDENCE_LEVELS = ("verified", "community", "derived")


@dataclass(frozen=True)
class Provenance:
    source_adapter: str
    source_url: Optional[str] = None
    fetched_at: Optional[str] = None
    confidence: str = "community"

    def __post_init__(self) -> None:
        if self.confidence not in CONFIDENCE_LEVELS:
            raise ValueError(
                f"confidence must be one of {CONFIDENCE_LEVELS}, got {self.confidence!r}"
            )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Provenance":
        return cls(
            source_adapter=data["source_adapter"],
            source_url=data.get("source_url"),
            fetched_at=data.get("fetched_at"),
            confidence=data.get("confidence", "community"),
        )
