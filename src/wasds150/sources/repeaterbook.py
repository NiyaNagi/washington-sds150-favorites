"""Placeholder: RepeaterBook public API source (amateur radio repeaters).

NOT IMPLEMENTED. Pending research into RepeaterBook's API terms/rate limits.
"""
from __future__ import annotations

from typing import List

from wasds150.models.catalog import FavoritesList
from wasds150.sources.base import RawDoc, SourceAdapter


class RepeaterBookSource(SourceAdapter):
    name = "repeaterbook"
    available = False

    def fetch(self) -> RawDoc:
        raise NotImplementedError("repeaterbook source is not implemented yet; pending research.")

    def normalize(self, raw: RawDoc) -> List[FavoritesList]:
        raise NotImplementedError
