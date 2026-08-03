"""Deterministic ordering and content hashing for generated output.

"Deterministic" here means: given the same baseline catalog and the same
profile, ``generate`` always produces byte-identical output and the same
content hash, regardless of machine, run order, or wall-clock time.
Timestamps (e.g. "generated_at") are tracked separately in bundle manifests
and snapshot metadata — they are never part of a content hash.
"""
from __future__ import annotations

from typing import List

from wasds150.catalog.ids import natural_sort_key
from wasds150.models.catalog import FavoritesList
from wasds150.util.hashing import content_hash


def sort_favorites(favorites: List[FavoritesList]) -> List[FavoritesList]:
    """Stable, deterministic ordering: baseline FL01, FL02, ... FL09a, FL09b,
    ... first (numeric order), then any non-standard/local keys sorted
    alphabetically after them.
    """
    return sorted(favorites, key=lambda fl: natural_sort_key(fl.favorite_key))


def generation_content_hash(favorites: List[FavoritesList]) -> str:
    """Hash of the *sorted* effective favorites list content, independent of
    the order they were assembled in."""
    ordered = sort_favorites(favorites)
    return content_hash([fl.content_hash() for fl in ordered])
