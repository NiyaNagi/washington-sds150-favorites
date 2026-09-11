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

#: Sources whose facts come from a database the user is licensed to use
#: personally. They match baseline rows only by exact system identity, and
#: their conventional rows are collected into separate ``licensed`` lists
#: (see :mod:`wasds150.recipes.rr_county`) rather than folded into the
#: public catalog.
LICENSED_SOURCE_IDS = ("sentinel_local", "radioreference_premium", "radioreference_api")

#: County lists built from RadioReference start enabled only near home;
#: the rest of the state is imported but switched off until the user asks.
RR_ENABLE_RADIUS_MILES = 60.0


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
    if fact.source_id == "fcc_uls" and (fact.raw or {}).get("radio_service_code") != "ZA":
        # Land-mobile licences have their own list (FCCDIG, built in
        # enrich_catalog). Matched by county or keyword they would pour every
        # business and public-safety frequency in a county into whichever
        # public row names that county; only GMRS licences enrich a row.
        return False
    if fact.source_id == "faa_nasr" and fact.freq_mhz is not None:
        # Airport, approach, centre and navigation-aid frequencies have their
        # own located list (FAAAIR, built in enrich_catalog). Matched by the
        # "aviation" keyword they poured every facility in the state, beacons
        # included, into each aviation row without positions.
        return False
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
    if fact.source_id in LICENSED_SOURCE_IDS:
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

    local_matched = any(f.source_id in LICENSED_SOURCE_IDS for f in matched)
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
    confidence = "verified" if fact.source_id in LICENSED_SOURCE_IDS else "community"
    return Provenance(
        source_adapter=fact.source_id,
        source_url=fact.source_url or None,
        fetched_at=fact.retrieved_at or None,
        confidence=confidence,
    )


def _refresh_trunk_sites(
    fl: FavoritesList, recipe: Recipe, coverage: RecipeCoverage, facts: List[NormalizedFact]
) -> None:
    """Tier D: RadioReference trunked-site rows refresh a SID row's frequency
    table (see :func:`wasds150.recipes.systems.refresh_trunk_frequencies`)."""
    sids = recipe.match.configured_sids()
    site_facts = systems_mod.rr_site_facts_for(fl, facts, sids)
    if not site_facts:
        return
    refreshed, message = systems_mod.refresh_trunk_frequencies(fl, site_facts, sids=sids)
    known = set(coverage.matched_fact_keys)
    coverage.matched_fact_keys.extend(f.entity_key for f in site_facts if f.entity_key not in known)
    if coverage.status == "none":
        coverage.status = "partial"
    coverage.warnings.append(message)
    if refreshed:
        prov = _provenance_for(site_facts[0])
        if (prov.source_adapter, prov.source_url) not in {(p.source_adapter, p.source_url) for p in fl.provenance}:
            fl.provenance.append(prov)


def _drop_keyword_faa_rows(fl: FavoritesList, entity_keys: List[str]) -> None:
    """Remove the FAA frequencies an earlier keyword match put into ``fl``'s
    aggregate public-facts system (ids as :func:`systems_mod.systems_from_flat_facts`
    makes them), now that FAAAIR carries them with their positions."""
    from wasds150.util.hashing import stable_id

    aggregate = stable_id(f"{fl.slug}:public-facts", kind="system")
    leaked = {stable_id(f"{fl.slug}:faa_nasr:{key}", kind="channel") for key in entity_keys}
    kept = []
    for system in fl.systems:
        if system.id == aggregate:
            for department in system.departments:
                department.channels = [c for c in department.channels if c.id not in leaked]
            system.departments = [d for d in system.departments if d.channels]
            if not system.departments:
                continue
        kept.append(system)
    fl.systems = kept
    # A row the FAA still cites (a COM facility record) is re-cited below.
    fl.provenance = [p for p in fl.provenance if p.source_adapter != "faa_nasr"]


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
    faa_keys = [f.entity_key for f in facts if f.source_id == "faa_nasr" and f.freq_mhz is not None]

    for fl in base_catalog.favorites:
        recipe = recipes_by_slug.get(fl.slug)
        new_fl = copy.deepcopy(fl)
        if faa_keys and any(p.source_adapter == "faa_nasr" for p in new_fl.provenance):
            _drop_keyword_faa_rows(new_fl, faa_keys)
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
            # A live RadioReference system is the current record of its SID:
            # it replaces whatever earlier copy the row carried (a Sentinel
            # HPDB import, or the previous refresh) rather than sitting beside it.
            from wasds150.sources.radioreference_api import SYSTEM_ID_PREFIX as _RR_API_PREFIX

            live_sids = {s.sid for s in new_systems if s.id.startswith(_RR_API_PREFIX) and s.sid is not None}
            if live_sids:
                new_fl.systems = [s for s in new_fl.systems if s.sid not in live_sids]
            policy = systems_mod.rebuild_policy(new_fl)
            if new_systems:
                if policy.mode == systems_mod.REPLACE_SYSTEMS:
                    # Freshly built systems win by id; anything the row carries
                    # that the source did not produce (operator-published net
                    # channels, for instance) is preserved.
                    new_fl.systems = systems_mod.dedupe_systems(new_systems + new_fl.systems)
                else:
                    new_fl.systems = systems_mod.dedupe_systems(new_fl.systems + new_systems)
            if policy.mode == systems_mod.REPLACE_TRUNK_FREQUENCIES:
                _refresh_trunk_sites(new_fl, recipe, cov, facts)
        new_favorites.append(new_fl)

    # RadioReference conventional rows become their own licensed per-county
    # lists. They are rebuilt from scratch whenever the source ran, so a
    # refreshed export replaces the previous run's copy instead of merging
    # into it; when the source did not run, the previous copies survive.
    from wasds150.catalog.ames_lake import AMES_LAKE_LAT, AMES_LAKE_LON
    from wasds150.recipes.rr_county import build_rr_favorites

    rr_lists = build_rr_favorites(
        facts, home=(AMES_LAKE_LAT, AMES_LAKE_LON), enable_within_miles=RR_ENABLE_RADIUS_MILES
    )
    # Every other Washington trunked system the web service returned becomes
    # a per-county RRT-* list; the ones a catalog row names by SID already
    # live in that row (see above) and are not repeated.
    from wasds150.recipes.rr_county import build_rr_trunked_favorites

    rr_lists += build_rr_trunked_favorites(
        facts,
        home=(AMES_LAKE_LAT, AMES_LAKE_LON),
        enable_within_miles=RR_ENABLE_RADIUS_MILES,
        exclude_sids={sid for recipe in recipes for sid in recipe.match.configured_sids()},
    )
    # The regional DMR network layout (PNWDigital / SeattleDMR) is rebuilt
    # the same way from the Config Builder facts, with repeater positions
    # joined from the coordinator rows the catalog already holds.
    from wasds150.recipes.dmr_networks import build_network_favorites, coordinate_lookup_from_catalog

    network_lists = build_network_favorites(facts, coords=coordinate_lookup_from_catalog(base_catalog))
    # FCC-licensed digital voice systems (DMR/NXDN/P25 by emission
    # designator) become one public list, rebuilt the same way.
    from wasds150.recipes.fcc_digital import build_fcc_digital_favorite

    fcc_digital = build_fcc_digital_favorite(facts)
    # FAA NASR airport, approach, centre and weather frequencies become one
    # located public list, rebuilt the same way.
    from wasds150.recipes.faa_airband import build_faa_airband_favorite

    faa_airband = build_faa_airband_favorite(facts, home=(AMES_LAKE_LAT, AMES_LAKE_LON))
    rebuilt = rr_lists + network_lists + [fl for fl in (fcc_digital, faa_airband) if fl is not None]
    if rebuilt:
        replaced = {fl.slug for fl in rebuilt}
        previous_enabled = {fl.slug: fl.enabled for fl in base_catalog.favorites if fl.origin == "local"}
        new_favorites = [fl for fl in new_favorites if fl.slug not in replaced]
        for fl in rebuilt:
            if fl.slug in previous_enabled:
                fl.enabled = previous_enabled[fl.slug]
            new_favorites.append(fl)

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

