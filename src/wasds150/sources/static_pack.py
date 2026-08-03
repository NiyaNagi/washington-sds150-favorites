"""The one fully-implemented source: this repository's checked-in
``washington-sds150-favorites.csv``.

This is what phases 1-4 use as "the catalog" — the 75-list human-curated
baseline. It is intentionally the only concrete :class:`SourceAdapter` in
this phase; :mod:`wasds150.catalog.baseline` packages its output as the
frozen default so ``wasds150 init`` works even without this repo checked
out.
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import List

from wasds150.catalog import loader
from wasds150.models.catalog import FavoritesList
from wasds150.sources.base import RawDoc, SourceAdapter


class StaticPackSource(SourceAdapter):
    name = "static_pack"
    available = True

    def __init__(self, csv_path: Path):
        self.csv_path = Path(csv_path)

    def fetch(self) -> RawDoc:
        text = self.csv_path.read_text(encoding="utf-8")
        return RawDoc(
            source_adapter=self.name,
            payload=text,
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def normalize(self, raw: RawDoc) -> List[FavoritesList]:
        # loader.load_csv re-reads from disk rather than parsing raw.payload
        # directly; the CSV module needs newline='' file-object semantics
        # that are simplest to get right by reusing the existing path-based
        # loader rather than re-implementing CSV parsing over a string here.
        catalog = loader.load_csv(self.csv_path)
        return catalog.favorites
