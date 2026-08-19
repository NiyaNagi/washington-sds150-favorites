"""Evaluate recipes against a batch of facts: coverage classification +
safe catalog enrichment.

Two additive things happen per matched baseline row (see
:mod:`wasds150.recipes` package docstring for the "never auto-rewrite the
free-text catalog fields" invariant this preserves): a traceable
:class:`~wasds150.models.provenance.Provenance` entry is appended (as
before), **and** a matched fact is turned into a real, populated
:class:`~wasds150.models.catalog.System` on ``FavoritesList.systems`` (see
:mod:`wasds150.recipes.systems` for the three tiers this draws on) --
`enrich_catalog` used to be provenance-only; it is not any more, which is
what lets :mod:`wasds150.hpe.builders` build a real per-list ``.hpe`` for
a row that needed a local HPDB/RadioReference Premium match instead of
staying stuck at ``systems=[]``. A run with zero facts is still guaranteed
to be a byte-for-byte no-op against
:func:`wasds150.merge.three_way.three_way_merge`, because
``FavoritesList.content_hash()`` never includes ``systems``/``provenance``
(see that method's docstring) -- only the *presentation* of a byte-
identical merge changes, never its hash.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from wasds150.models.catalog import Catalog, FavoritesList
from wasds150.models.provenance import Provenance
from wasds150.recipes import systems as systems_mod
from wasds150.recipes.default_recipes import Recipe
from wasds150.sources.facts import NormalizedFact

#: "full" — a local HPDB/RR system fact matched this recipe's SID (or the
#:   recipe doesn't need one); "partial" — some public-source facts matched
#:   (county/keyword) but full trunked detail (if required) is still
#:   missing; "none" — nothing matched at all.
COVERAGE_LEVELS = ("full", "partial", "none")


@dataclass
class RecipeCoverage:
    slug: str
    favorite_key: str
    status: str
    matched_fact_keys: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slug": self.slug,
            "favorite_key": self.favorite_key,
            "status": self.status,
            "matched_fact_keys": list(self.matched_fact_keys),
            "warnings": list(self.warnings),
        }


def _fact_matches(recipe: Recipe, fact: NormalizedFact) -> bool:
    configured_sids = recipe.match.configured_sids()
    if configured_sids:
        raw_sid = fact.raw.get("sid") if isinstance(fact.raw, dict) else None
        raw_sid_kind = fact.raw.get("sid_kind") if isinstance(fact.raw, dict) else None
        if (
            recipe.requires_local_hpdb
            and fact.source_id == "sentinel_local"
            and raw_sid_kind not in (None, "TrunkId", "SysId")
        ):
            return False
        try:
            if raw_sid is not None and int(raw_sid) in configured_sids:
                return True
        except (TypeError, ValueError):
            pass
        # Some normalized imports may omit raw SID while retaining a stable
        # HPDB/RR identity key. Match only a complete final numeric token;
        # substring matching would make SID 8217 collide with 18217.
        key_match = re.search(r"(?:^|:)(?:TrunkId|SysId):(\d+)$", fact.entity_key)
        return bool(key_match and int(key_match.group(1)) in configured_sids)
    if fact.source_id in ("sentinel_local", "radioreference_premium"):
        # Licensed database systems require an exact stable identity.
        # County and display-name fallbacks can absorb dozens of unrelated
        # systems and are reserved for public conventional-source facts.
        return False
    if not recipe.match.matches_source(fact.source_id):
        return False
    if recipe.match.county_contains:
        county = (fact.county or "").lower()
        if any(c.lower() in county for c in recipe.match.county_contains):
            return True
    if recipe.match.name_hint:
        # System-name fallback for rows with no SID to match on (most
        # conventional baseline rows): a conservative, length-gated
        # substring check from the specific recipe hint into the source
        # name. Reverse containment lets short/generic source labels match
        # overly broad Favorites List names.
        fact_name = (fact.name or "").strip().lower()
        hint = recipe.match.name_hint.strip().lower()
        if fact_name and len(hint) >= 6 and hint in fact_name:
            return True
    if recipe.match.source_ids and not (configured_sids or recipe.match.county_contains):
        # Keyword-derived source (service/scenario) match: any fact from
        # an already-matched source_id counts (the keyword match already
        # narrowed relevance) whenever there is no more specific SID/county
        # condition to prefer instead. Deliberately independent of
        # ``name_hint`` -- every recipe built by build_default_recipes now
        # carries one (see _detect_name_hint), so gating this fallback on
        # "name_hint is also unset" would silently disable it for every
        # real baseline row the moment that unconditional field was added;
        # name_hint is a supplementary, best-effort signal, never a reason
        # to withhold this otherwise-independent keyword match.
        return True
    return False


def evaluate_recipe(recipe: Recipe, facts: List[NormalizedFact]) -> RecipeCoverage:
    matched = [f for f in facts if _fact_matches(recipe, f)]
    warnings: List[str] = []

    local_matched = any(f.source_id in ("sentinel_local", "radioreference_premium") for f in matched)
    if recipe.requires_local_hpdb:
        status = "full" if local_matched else ("partial" if matched else "none")
        if not local_matched:
            warnings.append(
                f"{recipe.favorite_key}: full site/talkgroup detail requires a local Sentinel "
                "HPDB export or RadioReference Premium data; none configured/matched."
            )
    else:
        status = "full" if matched else "none"

    return RecipeCoverage(
        slug=recipe.slug,
        favorite_key=recipe.favorite_key,
        status=status,
        matched_fact_keys=[f.entity_key for f in matched],
        warnings=warnings,
    )


def _provenance_for(fact: NormalizedFact) -> Provenance:
    confidence = "verified" if fact.source_id in ("sentinel_local", "radioreference_premium") else "community"
    return Provenance(
        source_adapter=fact.source_id,
        source_url=fact.source_url or None,
        fetched_at=fact.retrieved_at or None,
        confidence=confidence,
    )


def enrich_catalog(
    base_catalog: Catalog, facts: List[NormalizedFact], recipes: List[Recipe]
) -> "EnrichResult":
    """Return an ``upstream``-shaped :class:`Catalog` (a deep copy of
    ``base_catalog``) plus a per-recipe coverage report.

    For every row with a matching recipe: matched facts are appended to
    ``provenance`` (as before, deduped by ``(source_adapter, source_url)``)
    **and** converted into real :class:`~wasds150.models.catalog.System`
    objects appended to ``systems`` (see :mod:`wasds150.recipes.systems`),
    deduped by system id and merged with whatever systems the row already
    carried (e.g. from :func:`wasds150.recipes.systems.static_systems_for`,
    already applied to the packaged baseline -- see
    :mod:`wasds150.catalog.baseline`). CSV fact fields are never touched,
    so a run with zero local facts is still a byte-for-byte content-hash
    no-op (``systems``/``provenance`` are excluded from
    ``FavoritesList.content_hash()``).
    """
    recipes_by_slug = {r.slug: r for r in recipes}
    new_favorites: List[FavoritesList] = []
    coverage: List[RecipeCoverage] = []

    for fl in base_catalog.favorites:
        recipe = recipes_by_slug.get(fl.slug)
        new_fl = copy.deepcopy(fl)
        if recipe is not None:
            cov = evaluate_recipe(recipe, facts)
            coverage.append(cov)
            matched_facts = [f for f in facts if f.entity_key in cov.matched_fact_keys]
            existing = {(p.source_adapter, p.source_url) for p in new_fl.provenance}
            for fact in matched_facts:
                prov = _provenance_for(fact)
                key = (prov.source_adapter, prov.source_url)
                if key not in existing:
                    new_fl.provenance.append(prov)
                    existing.add(key)
            new_systems = systems_mod.systems_from_matched_facts(new_fl, matched_facts)
            if new_systems:
                if systems_mod.rebuilds_systems_from_facts(new_fl):
                    # Freshly built systems win by id; anything the row carries
                    # that the source did not produce (operator-published net
                    # channels, for instance) is preserved.
                    new_fl.systems = systems_mod.dedupe_systems(new_systems + new_fl.systems)
                else:
                    new_fl.systems = systems_mod.dedupe_systems(new_fl.systems + new_systems)
        new_favorites.append(new_fl)

    enriched_catalog = Catalog(favorites=new_favorites)
    populated_rollups = systems_mod.populate_rollups(enriched_catalog)
    if populated_rollups:
        coverage_by_slug = {item.slug: item for item in coverage}
        for slug in populated_rollups:
            item = coverage_by_slug.get(slug)
            if item is not None:
                item.status = "full"
                item.warnings = []
                item.matched_fact_keys = [
                    f"derived:{key}" for key in populated_rollups[slug]
                ]

    return EnrichResult(catalog=enriched_catalog, coverage=coverage)


@dataclass
class EnrichResult:
    catalog: Catalog
    coverage: List[RecipeCoverage] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "catalog_hash": self.catalog.content_hash(),
            "coverage": [c.to_dict() for c in self.coverage],
        }

