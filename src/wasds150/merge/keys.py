"""Merge-key field ownership: which `FavoritesList` fields are "facts" (owned
by upstream sources) vs "presentation/policy" (owned by the local profile).

This is the concrete implementation of the architecture doc's §5 "merge
keys" design for this project's flat, CSV-column-shaped
:class:`~wasds150.models.catalog.FavoritesList`: every catalog fact column
(frequencies, coverage, source citations, etc.) is upstream-owned, while
``notes`` (free-form user annotation) and ``flqk``/``enabled`` (profile-only
attributes, not even present in the baseline CSV) are always local-owned.

The rule this drives (see :mod:`wasds150.merge.three_way`): a genuine 3-way
conflict can only occur on a **fact** field where the local profile has an
explicit override *and* upstream independently changed the same field to a
different value. Presentation fields are never adopted from upstream and
never conflict — they are the user's alone.
"""
from __future__ import annotations

from wasds150.models.catalog import CSV_FIELDS

#: CSV columns considered upstream-owned "facts" about the radio system.
FACT_FIELDS: tuple = tuple(f for f in CSV_FIELDS if f != "notes")

#: Fields the local profile always owns; upstream never overwrites these,
#: and they can never produce a merge conflict.
PRESENTATION_FIELDS: tuple = ("notes", "flqk", "enabled")


def classify_field(field_name: str) -> str:
    """Return ``"fact"`` or ``"presentation"`` for a given field name."""
    if field_name in PRESENTATION_FIELDS:
        return "presentation"
    if field_name in FACT_FIELDS:
        return "fact"
    raise ValueError(f"unknown field {field_name!r}; not in FACT_FIELDS or PRESENTATION_FIELDS")


def is_fact_field(field_name: str) -> bool:
    return field_name in FACT_FIELDS


def is_presentation_field(field_name: str) -> bool:
    return field_name in PRESENTATION_FIELDS
