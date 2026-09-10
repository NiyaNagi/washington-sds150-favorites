"""Named channel plans shipped with the project.

A plan is checked in as code rather than authored as a data file because the
selectors are the interesting part: they say *what belongs in this radio* in
terms that survive a database refresh, and they carry the transmit policy that
keeps a licensed operator inside their privileges.
"""
from __future__ import annotations

from typing import Dict, List

from wasds150.models.plan import ChannelPlan
from wasds150.plans.atd890_scan import ATD890_SCAN
from wasds150.plans.ftx1_local import FTX1_LOCAL
from wasds150.plans.ftx1_scan import FTX1_SCAN
from wasds150.plans.ftx1_wa import FTX1_WA
from wasds150.plans.h9_ozette import H9_OZETTE
from wasds150.plans.thd75_ames_lake import THD75_AMES_LAKE
from wasds150.plans.thd75_scan import THD75_SCAN

_REGISTRY: Dict[str, ChannelPlan] = {
    H9_OZETTE.id: H9_OZETTE,
    FTX1_WA.id: FTX1_WA,
    FTX1_LOCAL.id: FTX1_LOCAL,
    FTX1_SCAN.id: FTX1_SCAN,
    THD75_AMES_LAKE.id: THD75_AMES_LAKE,
    THD75_SCAN.id: THD75_SCAN,
    ATD890_SCAN.id: ATD890_SCAN,
}


def list_plans() -> Dict[str, ChannelPlan]:
    return dict(_REGISTRY)


def plan_ids() -> List[str]:
    return sorted(_REGISTRY)


def get_plan(plan_id: str) -> ChannelPlan:
    key = str(plan_id).strip().lower()
    try:
        return _REGISTRY[key]
    except KeyError:
        raise KeyError(
            f"unknown plan {plan_id!r}; known plans: {', '.join(plan_ids())}"
        ) from None


__all__ = [
    "ATD890_SCAN",
    "FTX1_LOCAL",
    "FTX1_SCAN",
    "FTX1_WA",
    "H9_OZETTE",
    "THD75_AMES_LAKE",
    "THD75_SCAN",
    "get_plan",
    "list_plans",
    "plan_ids",
]
