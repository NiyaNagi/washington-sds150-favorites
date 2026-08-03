"""Update pipeline: run source adapters, collect facts/alerts, enrich the
current catalog into an ``upstream`` snapshot via :mod:`wasds150.recipes`,
then reuse :func:`wasds150.merge.three_way.three_way_merge` for the actual
diff/conflict logic (deliberately not reinvented here — see that module's
docstring for the merge policy this inherits unchanged).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from wasds150.merge.three_way import MergeResult, three_way_merge
from wasds150.models.catalog import Catalog
from wasds150.models.profile import Profile
from wasds150.recipes import RecipeCoverage, build_default_recipes, enrich_catalog
from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import ChangeAlert, NormalizedFact


@dataclass
class SourceRunOutcome:
    source_id: str
    ok: bool
    fact_count: int = 0
    alert_count: int = 0
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "ok": self.ok,
            "fact_count": self.fact_count,
            "alert_count": self.alert_count,
            "warnings": list(self.warnings),
            "error": self.error,
        }


@dataclass
class UpdateRunResult:
    facts: List[NormalizedFact] = field(default_factory=list)
    alerts: List[ChangeAlert] = field(default_factory=list)
    outcomes: List[SourceRunOutcome] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fact_count": len(self.facts),
            "alert_count": len(self.alerts),
            "outcomes": [o.to_dict() for o in self.outcomes],
        }


def run_sources(
    sources: List[OnlineSourceAdapter], *, http_client: Optional[Any] = None
) -> UpdateRunResult:
    """Fetch+normalize every adapter in ``sources``. One adapter raising
    never aborts the whole run — its failure is recorded as a
    :class:`SourceRunOutcome` with ``ok=False`` so a single flaky/offline
    endpoint doesn't block every other source (important for ``kind=facts``
    adapters that need real network, mixed in with ``kind=local`` ones that
    don't)."""
    result = UpdateRunResult()
    for source in sources:
        try:
            raw: RawDoc = source.fetch(http_client)
            normalized = source.normalize(raw)
            result.facts.extend(normalized.facts)
            result.alerts.extend(normalized.alerts)
            result.outcomes.append(
                SourceRunOutcome(
                    source_id=source.name,
                    ok=True,
                    fact_count=len(normalized.facts),
                    alert_count=len(normalized.alerts),
                    warnings=list(normalized.warnings),
                )
            )
        except Exception as exc:  # noqa: BLE001 - deliberately broad, see docstring
            result.outcomes.append(SourceRunOutcome(source_id=source.name, ok=False, error=str(exc)))
    return result


@dataclass
class UpdatePipelineResult:
    run: UpdateRunResult
    coverage: List[RecipeCoverage]
    merge: MergeResult

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run": self.run.to_dict(),
            "coverage": [c.to_dict() for c in self.coverage],
            "merge": self.merge.to_dict(),
        }


def build_and_merge(
    base_catalog: Catalog, profile: Profile, facts: List[NormalizedFact]
) -> Dict[str, Any]:
    """The recipe+merge half of the pipeline, split out from
    :func:`run_sources` so callers (tests, CLI ``sources update --offline``)
    can supply facts directly without a live network round-trip."""
    recipes = build_default_recipes(base_catalog)
    enrich_result = enrich_catalog(base_catalog, facts, recipes)
    merge_result = three_way_merge(base_catalog, enrich_result.catalog, profile)
    return {"coverage": enrich_result.coverage, "merge": merge_result}


def run_update_pipeline(
    base_catalog: Catalog,
    profile: Profile,
    sources: List[OnlineSourceAdapter],
    *,
    http_client: Optional[Any] = None,
) -> UpdatePipelineResult:
    """Full pipeline: fetch every source, enrich, merge. See
    :func:`run_sources` and :func:`build_and_merge`."""
    run = run_sources(sources, http_client=http_client)
    built = build_and_merge(base_catalog, profile, run.facts)
    return UpdatePipelineResult(run=run, coverage=built["coverage"], merge=built["merge"])
