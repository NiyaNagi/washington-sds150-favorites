"""Structural diffing between the baseline catalog and a profile's effective
changes (used by ``wasds150 preview`` and the Dashboard/Profile UI).

This is *not* the three-way merge described in the architecture doc (that
needs an "upstream" source, which is out of scope here) — it is a two-way,
local-only diff: baseline-as-shipped vs. baseline-as-modified-by-profile.
:mod:`wasds150.merge` will reuse :class:`~wasds150.models.diff.ChangeRecord`
when it is implemented.
"""
from __future__ import annotations

from typing import List

from wasds150.models.catalog import Catalog
from wasds150.models.diff import ChangeRecord
from wasds150.models.profile import EDITABLE_FIELDS, Profile


def diff_profile(catalog: Catalog, profile: Profile) -> List[ChangeRecord]:
    """Every effective change a profile makes relative to the raw baseline:
    removals, field edits, enable/disable, and local additions."""
    changes: List[ChangeRecord] = []
    baseline_by_slug = {fl.slug: fl for fl in catalog.favorites}

    for slug, entry in sorted(profile.entries.items()):
        baseline = baseline_by_slug.get(slug)
        label = baseline.favorite_name if baseline else slug
        if entry.removed:
            changes.append(ChangeRecord(op="remove", slug=slug, label=label))
            continue
        if entry.enabled is not None:
            baseline_enabled = baseline.enabled if baseline else True
            if entry.enabled != baseline_enabled:
                op = "enable" if entry.enabled else "disable"
                changes.append(ChangeRecord(op=op, slug=slug, label=label))
        for field_name in EDITABLE_FIELDS:
            if field_name in entry.overrides:
                before = getattr(baseline, field_name, None) if baseline else None
                after = entry.overrides[field_name]
                if before != after:
                    changes.append(
                        ChangeRecord(
                            op="edit", slug=slug, field=field_name, before=before, after=after, label=label
                        )
                    )

    for slug, fl in sorted(profile.local_lists.items()):
        changes.append(ChangeRecord(op="add", slug=slug, label=fl.favorite_name))

    return changes
