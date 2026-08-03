"""Abstract source adapter contracts.

Two contracts exist:

* :class:`SourceAdapter` (legacy/local) — used by
  :class:`wasds150.sources.static_pack.StaticPackSource` and the
  not-yet-implemented ``repeaterbook``/``radioreference_free`` placeholders.
  ``fetch``/``normalize`` directly produce
  :class:`~wasds150.models.catalog.FavoritesList` objects.
* :class:`OnlineSourceAdapter` — used by every online/local-file adapter
  added for the update-pipeline phase (NOAA, USCG, AMSAT, NWAC, WWARA,
  IACC, FAA NASR, FCC ULS, WA EMD/DNR, NIFC, Sentinel HPDB, RadioReference
  Premium). ``fetch`` takes an optional
  :class:`~wasds150.cache.http.CachedHttpClient` (``None`` for local-file-only
  sources); ``normalize`` returns a
  :class:`~wasds150.sources.facts.NormalizeResult` (flat, adapter-agnostic
  facts/alerts) rather than catalog objects directly — turning facts into
  :class:`~wasds150.models.catalog.System`/``FavoritesList`` objects is
  :mod:`wasds150.recipes`' job, since that often needs facts from more than
  one adapter at once.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional

from wasds150.models.catalog import FavoritesList
from wasds150.sources.facts import NormalizeResult


@dataclass
class RawDoc:
    """Opaque raw payload returned by ``fetch``, before normalization."""

    source_adapter: str
    payload: Any
    fetched_at: str = ""


class SourceAdapter(ABC):
    #: Short, stable identifier stored in ``Provenance.source_adapter``.
    name: str = "base"

    #: False for adapters that are defined but not yet implemented; the CLI
    #: and web UI use this to gray out / explain unavailable sources instead
    #: of letting them fail unpredictably.
    available: bool = False

    @abstractmethod
    def fetch(self) -> RawDoc:
        """Retrieve raw data for this source. May hit network/disk/cache."""
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw: RawDoc) -> List[FavoritesList]:
        """Pure transform: RawDoc -> normalized FavoritesList facts."""
        raise NotImplementedError


class OnlineSourceAdapter(ABC):
    """Base for the update-pipeline's fact-producing adapters."""

    #: Short, stable identifier stored in ``NormalizedFact.source_id`` /
    #: ``CacheEntry.source_id`` / ``ChangeAlert.source_id``.
    name: str = "base"
    available: bool = True
    #: "facts" (produces NormalizedFact rows) | "change_detection" (produces
    #: only ChangeAlert rows — the PDF/link-only sources) | "local" (reads
    #: local files only, e.g. Sentinel HPDB; never touches the network).
    kind: str = "facts"

    @abstractmethod
    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        """Retrieve raw data. ``http_client`` is a
        :class:`wasds150.cache.http.CachedHttpClient`, or ``None`` for
        ``kind == "local"`` adapters that never make network requests."""
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw: RawDoc) -> NormalizeResult:
        """Pure transform: RawDoc -> NormalizeResult (facts/alerts/warnings)."""
        raise NotImplementedError

