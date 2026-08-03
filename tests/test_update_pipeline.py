"""Tests for the update pipeline: adapter fan-out (with per-adapter failure
isolation) + recipe-enrichment + three-way-merge composition. See
:mod:`wasds150.recipes` for why a no-facts run is guaranteed to be a safe
no-op, exercised again here at the pipeline level."""
from __future__ import annotations

from wasds150.catalog import baseline
from wasds150.models.profile import Profile
from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizedFact, NormalizeResult
from wasds150.update.pipeline import build_and_merge, run_sources


class _WorkingSource(OnlineSourceAdapter):
    name = "working_test_source"
    available = True
    kind = "local"

    def fetch(self, http_client=None) -> RawDoc:
        return RawDoc(source_adapter=self.name, payload=None, fetched_at="t")

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        return NormalizeResult(
            facts=[NormalizedFact(entity_key="x:1", fact_type="system", source_id=self.name)]
        )


class _BrokenSource(OnlineSourceAdapter):
    name = "broken_test_source"
    available = True
    kind = "local"

    def fetch(self, http_client=None) -> RawDoc:
        raise RuntimeError("simulated adapter failure")

    def normalize(self, raw: RawDoc) -> NormalizeResult:  # pragma: no cover - never reached
        raise AssertionError("should not be called")


def test_run_sources_isolates_one_adapter_failure():
    result = run_sources([_WorkingSource(), _BrokenSource()])
    assert len(result.outcomes) == 2
    ok_names = {o.source_id for o in result.outcomes if o.ok}
    failed_names = {o.source_id for o in result.outcomes if not o.ok}
    assert ok_names == {"working_test_source"}
    assert failed_names == {"broken_test_source"}
    assert "simulated adapter failure" in next(o.error for o in result.outcomes if not o.ok)
    assert len(result.facts) == 1


def test_run_sources_empty_list():
    result = run_sources([])
    assert result.facts == []
    assert result.outcomes == []


def test_build_and_merge_with_no_facts_is_safe_noop():
    catalog = baseline.load_baseline()
    profile = Profile(profile_id="p", based_on_catalog_hash=catalog.content_hash())
    built = build_and_merge(catalog, profile, [])
    assert built["merge"].changes == []
    assert built["merge"].conflicts == []
    assert built["merge"].merged_catalog.content_hash() == catalog.content_hash()
    assert len(built["coverage"]) == len(catalog.favorites)


def test_build_and_merge_returns_coverage_for_every_recipe():
    catalog = baseline.load_baseline()
    profile = Profile(profile_id="p", based_on_catalog_hash=catalog.content_hash())
    fact = NormalizedFact(entity_key="hpdb:TrunkId:7971", fact_type="system", source_id="sentinel_local", raw={"sid": 7971})
    built = build_and_merge(catalog, profile, [fact])
    fl04_coverage = next(c for c in built["coverage"] if c.favorite_key == "FL04")
    assert fl04_coverage.status == "full"
