"""FLQK (Favorites List Quick Key) helpers.

Implements only allocation/reporting utilities; the numbering *policy*
(which ranges mean what: statewide anchors, western WA counties, mountain
regions, etc.) lives in ``washington-sds150-favorites-master.md`` Section 2
and is not hard-coded here, since the CSV baseline does not currently carry
FLQK assignments at all (see :mod:`wasds150.models.catalog` docstring) —
users assign them explicitly via the profile, and these helpers just keep
that assignment sane.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from wasds150.catalog.validate import FLQK_MAX, FLQK_MIN, FLQK_RESERVED
from wasds150.models.catalog import FavoritesList


def used_flqks(favorites: List[FavoritesList]) -> Dict[int, List[str]]:
    """Map each assigned FLQK to the slugs using it. Multiple slugs sharing
    one FLQK is expected/valid (see master guide §2.2) and is not an error;
    this is for reporting/allocation only."""
    used: Dict[int, List[str]] = {}
    for fl in favorites:
        if fl.flqk is not None:
            used.setdefault(fl.flqk, []).append(fl.slug)
    return used


def next_available_flqk(
    favorites: List[FavoritesList], start: int = 1, end: int = 98
) -> Optional[int]:
    """First FLQK in ``[start, end]`` not already assigned to any favorite,
    skipping the reserved keys (0 and 99) by default range bounds."""
    if start < FLQK_MIN or end > FLQK_MAX or start > end:
        raise ValueError(f"invalid FLQK range [{start}, {end}]")
    in_use = set(used_flqks(favorites).keys())
    for candidate in range(start, end + 1):
        if candidate in FLQK_RESERVED:
            continue
        if candidate not in in_use:
            return candidate
    return None
