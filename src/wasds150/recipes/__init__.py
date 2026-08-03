"""Default recipes: deterministic, safe mapping from source facts onto the
existing baseline catalog.

**Design constraint driving everything here**: the existing catalog's
per-row fields (``system_or_category``, ``sites_or_coverage``,
``departments_or_channels``, ``notes``, ...) are hand-authored free-text
prose describing a Favorites List (see
:mod:`wasds150.models.catalog`'s module docstring) — not a machine-editable
list of channels. Automatically rewriting that prose from adapter facts
would be both lossy (facts are per-frequency; the field is a paragraph
summarizing many) and unverifiable (no adapter's facts are complete enough
to safely regenerate a correct paragraph). So a "recipe" here never
rewrites those 14 CSV fields. Instead it:

1. Classifies each baseline row's **coverage** — "full" (matched local
   HPDB/RadioReference facts, or no local data was ever required), "partial"
   (some public-source facts matched but full trunked detail is missing),
   or "none" — so a user/generator run can surface exactly which rows would
   benefit from a local HPDB export or RR Premium data.
2. Attaches matched facts as additional :class:`~wasds150.models.provenance.Provenance`
   entries (source, URL, retrieval time) — additive, traceable enrichment
   that never conflicts with :mod:`wasds150.merge.three_way` (provenance
   isn't a merge "fact field").
3. **Converts matched facts into a real, populated**
   :class:`~wasds150.models.catalog.System` **on** ``FavoritesList.systems``
   (see :mod:`wasds150.recipes.systems`) — this *is* new structural data
   (not a change to any of the 14 free-text fields), so it is also
   merge-inert: ``systems`` is deliberately excluded from
   :meth:`~wasds150.models.catalog.FavoritesList.content_hash`, the same
   way ``provenance`` already was.

This means: with **no** local HPDB/RadioReference input, running the
update pipeline against every public adapter produces an upstream catalog
that is *fact-identical* to the baseline (only provenance/systems, both
merge-inert, differ) — i.e. "generate a default import bundle from all
facts available without private inputs" degrades gracefully to exactly
today's shipped catalog's CSV fields and content hash, never silently
corrupting it. A no-private-input `generate` still produces real per-list
``.hpe`` output for roughly 56 of the 78 baseline rows, though, because
:func:`wasds150.recipes.systems.static_systems_for` — a separate, pure,
no-fact-matching-required tier — runs on every ``generate``/``preview``
regardless (see that module's docstring). Supplying a local HPDB/RR export
lets :func:`wasds150.recipes.engine.evaluate_recipe` report "full" coverage
and attach ``confidence="verified"`` provenance **and** a fully populated
``System`` for the rows it actually matches (mainly the
``requires_local_hpdb`` trunked rows), satisfying "enrich deterministically
when local HPDB/RR inputs are present" without ever fabricating
unverifiable prose or talkgroups.
"""
from wasds150.recipes.default_recipes import Recipe, RecipeMatch, build_default_recipes
from wasds150.recipes.engine import COVERAGE_LEVELS, EnrichResult, RecipeCoverage, enrich_catalog, evaluate_recipe

__all__ = [
    "Recipe",
    "RecipeMatch",
    "build_default_recipes",
    "COVERAGE_LEVELS",
    "EnrichResult",
    "RecipeCoverage",
    "enrich_catalog",
    "evaluate_recipe",
]
