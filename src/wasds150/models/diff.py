"""Change/diff records shared by :mod:`wasds150.diffing` and
:mod:`wasds150.merge`.

Kept separate from ``diffing.differ`` so the merge engine can reuse the same
``ChangeRecord`` shape without importing the (structural, local-only) diff
implementation.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

#: add: a new local Favorites List; remove: a baseline entry hidden by the
#: profile; edit: a field override; enable/disable: profile enabled state.
OPS = ("add", "remove", "edit", "enable", "disable")


@dataclass
class ChangeRecord:
    op: str
    slug: str
    field: Optional[str] = None
    before: Any = None
    after: Any = None
    label: str = ""

    def __post_init__(self) -> None:
        if self.op not in OPS:
            raise ValueError(f"op must be one of {OPS}, got {self.op!r}")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
