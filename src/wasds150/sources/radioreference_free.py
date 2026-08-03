"""Placeholder: fetch public RadioReference pages (no account required).

NOT IMPLEMENTED. Pending research into which public pages/rate limits are
safe to depend on, plus a caching/ToS-respecting fetch strategy. See the
architecture doc's provenance/caching and security sections.
"""
from __future__ import annotations

from typing import List

from wasds150.models.catalog import FavoritesList
from wasds150.sources.base import RawDoc, SourceAdapter


class RadioReferenceFreeSource(SourceAdapter):
    name = "radioreference_free"
    available = False

    def fetch(self) -> RawDoc:
        raise NotImplementedError(
            "radioreference_free source is not implemented yet; pending research."
        )

    def normalize(self, raw: RawDoc) -> List[FavoritesList]:
        raise NotImplementedError
