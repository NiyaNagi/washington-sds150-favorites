"""Three-way merge: base (last-pinned catalog) + upstream (freshly fetched
catalog) + local (current profile) -> a merged catalog and a conflict
report, preserving the user's presentation/policy overrides untouched while
fact fields adopt upstream's latest values.

See :mod:`wasds150.merge.keys` for the fact-vs-presentation field
classification this is built on, and the architecture doc §5 "merge keys"
for the original design this implements.

**How "upstream" is supplied**: this engine only needs two
:class:`~wasds150.models.catalog.Catalog` snapshots — it has no dependency
on *how* ``upstream`` was obtained. Today that's typically a freshly
regenerated packaged baseline or an edited CSV re-loaded via
:mod:`wasds150.catalog.loader`; a future online source adapter (out of
scope here — see :mod:`wasds150.sources`) would simply be another way to
produce an ``upstream`` :class:`Catalog` to hand to
:func:`three_way_merge`.

**Merge policy:**

* A slug in ``base`` but not ``upstream`` -> reported as ``removed``; any
  profile entry for it is pruned by :func:`apply_merge` (a baseline that no
  longer exists can't be overridden) but the removal is always reported so
  nothing silently disappears.
* A slug in ``upstream`` but not ``base`` -> reported as ``added``
  (informational only; the merge does not auto-enable it — that is a
  distinct profile-editing decision for the user to make).
* A **fact** field (see :mod:`wasds150.merge.keys`) that differs between
  ``base`` and ``upstream``:
    * If the local profile has **no** override for that field -> silently
      adopt upstream's value (reported as ``updated``). This is what
      "upstream fact fields update" means in practice: the merged catalog's
      baseline simply reflects upstream, so any un-overridden field is
      automatically current after a merge.
    * If the local profile **has** an override for that field:
        * and the override already equals upstream's new value -> no
          conflict (they agree; reported as ``updated`` like any other).
        * and it disagrees -> a :class:`~wasds150.merge.conflicts.MergeConflict`
          is reported. The override is deliberately **left in place**
          (untouched) rather than silently discarded or silently forced to
          win — this is the "preserving user overrides" guarantee: an
          explicit customization is never clobbered by a merge, but the
          user is told it may now disagree with upstream so they can decide
          (keep it, or ``profile restore``/re-edit it).
* **Presentation/policy** fields (``notes``, ``flqk``, ``enabled``) are
  never compared against upstream and can never produce a conflict — they
  are not part of ``upstream`` at all (upstream is baseline-shaped facts
  only); the local profile always owns them.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from wasds150.merge.conflicts import MergeConflict
from wasds150.merge.keys import FACT_FIELDS
from wasds150.models.catalog import Catalog
from wasds150.models.profile import Profile


@dataclass
class MergeChange:
    #: "added" | "removed" | "updated"
    op: str
    slug: str
    field: Optional[str] = None
    before: Any = None
    after: Any = None
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MergeResult:
    merged_catalog: Catalog
    changes: List[MergeChange] = field(default_factory=list)
    conflicts: List[MergeConflict] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "merged_catalog_hash": self.merged_catalog.content_hash(),
            "changes": [c.to_dict() for c in self.changes],
            "conflicts": [c.to_dict() for c in self.conflicts],
        }


def three_way_merge(base: Catalog, upstream: Catalog, local: Profile) -> MergeResult:
    base_by_slug = {fl.slug: fl for fl in base.favorites}
    upstream_by_slug = {fl.slug: fl for fl in upstream.favorites}

    changes: List[MergeChange] = []
    conflicts: List[MergeConflict] = []

    for slug, base_fl in base_by_slug.items():
        if slug not in upstream_by_slug:
            changes.append(MergeChange(op="removed", slug=slug, label=base_fl.favorite_name))

    for slug, up_fl in upstream_by_slug.items():
        if slug not in base_by_slug:
            changes.append(MergeChange(op="added", slug=slug, label=up_fl.favorite_name))
            continue  # nothing to diff against for a brand-new slug

        base_fl = base_by_slug[slug]
        entry = local.entries.get(slug)
        for field_name in FACT_FIELDS:
            base_value = getattr(base_fl, field_name)
            upstream_value = getattr(up_fl, field_name)
            if base_value == upstream_value:
                continue

            has_override = entry is not None and field_name in entry.overrides
            if has_override:
                local_value = entry.overrides[field_name]
                if local_value == upstream_value:
                    changes.append(
                        MergeChange(
                            op="updated", slug=slug, field=field_name,
                            before=base_value, after=upstream_value, label=up_fl.favorite_name,
                        )
                    )
                else:
                    conflicts.append(
                        MergeConflict(
                            slug=slug, field=field_name, base_value=base_value,
                            upstream_value=upstream_value, local_value=local_value,
                            label=up_fl.favorite_name,
                        )
                    )
            else:
                changes.append(
                    MergeChange(
                        op="updated", slug=slug, field=field_name,
                        before=base_value, after=upstream_value, label=up_fl.favorite_name,
                    )
                )

    merged_catalog = Catalog(favorites=list(upstream.favorites))
    return MergeResult(merged_catalog=merged_catalog, changes=changes, conflicts=conflicts)


def apply_merge(profile: Profile, result: MergeResult) -> Profile:
    """Return a **new** :class:`Profile` with ``based_on_catalog_hash``
    repinned to the merged catalog, and any overrides for slugs the merged
    catalog no longer contains pruned (see :func:`three_way_merge`'s
    "removed" case). Local-only lists are always carried through unchanged.
    Conflicting overrides are left exactly as they were — see module
    docstring.
    """
    merged_slugs = {fl.slug for fl in result.merged_catalog.favorites}
    new_entries = {slug: entry for slug, entry in profile.entries.items() if slug in merged_slugs}
    return Profile(
        profile_id=profile.profile_id,
        based_on_catalog_hash=result.merged_catalog.content_hash(),
        entries=new_entries,
        local_lists=dict(profile.local_lists),
    )
