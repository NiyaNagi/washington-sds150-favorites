"""Canonical update pipeline: source adapters -> facts -> recipe-driven
catalog enrichment -> three-way merge (reusing :mod:`wasds150.merge`
unchanged). See :mod:`wasds150.update.pipeline` for the implementation and
:mod:`wasds150.recipes` for the enrichment/coverage rules.
"""
from wasds150.update.pipeline import (
    SourceRunOutcome,
    UpdatePipelineResult,
    UpdateRunResult,
    build_and_merge,
    run_sources,
    run_update_pipeline,
)

__all__ = [
    "SourceRunOutcome",
    "UpdateRunResult",
    "UpdatePipelineResult",
    "build_and_merge",
    "run_sources",
    "run_update_pipeline",
]
