"""Merge conflict representation.

A conflict is only ever raised for a **fact** field (see
:mod:`wasds150.merge.keys`) where the local profile holds an explicit
override that disagrees with upstream's independently-changed value; see
:mod:`wasds150.merge.three_way` for how these are produced.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass
class MergeConflict:
    slug: str
    field: str
    base_value: Any
    upstream_value: Any
    local_value: Any
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
