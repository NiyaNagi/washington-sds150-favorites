"""Stable id/slug helpers and natural sort ordering for Favorites List keys.

``favorite_key`` values look like ``FL01``, ``FL09a``, ``FL74b`` — a
zero-padded number with an optional lower-case letter suffix for split
lists. Plain string sorting on the padded form happens to work for the
current catalog, but is not guaranteed to (e.g. ``FL9`` vs ``FL10``), so we
parse the number explicitly for a sort key that is correct regardless of
padding.
"""
from __future__ import annotations

import re
from typing import Tuple

from wasds150.util.hashing import stable_id as _stable_id  # re-exported

_KEY_PATTERN = re.compile(r"^FL(\d+)([a-z]*)$", re.IGNORECASE)

stable_id = _stable_id


def slugify(favorite_key: str) -> str:
    """Derive the stable slug for a Favorites List from its favorite_key.

    The slug is what merge keys and cross-references are built on (see
    architecture doc §5) — it must never be derived from ``favorite_name``,
    which is free text and can be edited by users.
    """
    return favorite_key.strip().lower()


def natural_sort_key(favorite_key: str) -> Tuple[int, str]:
    """Sort key ordering FL1 < FL2 < ... < FL9a < FL9b < FL10, regardless of
    zero-padding, so generated output order is deterministic and matches the
    intuitive numbering from the master guide."""
    match = _KEY_PATTERN.match(favorite_key.strip())
    if not match:
        # Unrecognized key shape: sort after all recognized keys, stably by
        # the raw string so output is still deterministic.
        return (10**9, favorite_key)
    number = int(match.group(1))
    suffix = match.group(2).lower()
    return (number, suffix)
