"""Best-effort hierarchical grouping of a flat :class:`RecordDocument`, for
human-readable display (``wasds150 hpe inspect``) only — never used for
validation or round-trip, which are handled by the flat, lossless
:mod:`wasds150.hpe.record` layer.

The real format serializes a tree (system -> group/site -> channel/talkgroup)
as a flat, order-dependent sequence of tag lines with no explicit
indentation. This module reconstructs a *display* tree using a documented
parent-tag mapping and "most recent record of the parent tag" grouping —
a generic, order-based heuristic, not a guess at any undocumented byte
layout. If a record's tag isn't in the map, or no parent has been seen yet,
it is attached at the top level rather than dropped, so nothing is ever
lost from what `hpe inspect` shows.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from wasds150.hpe.record import Record, RecordDocument

#: child tag -> parent tag(s) it nests under, most-specific first.
_PARENT_OF: Dict[str, Tuple[str, ...]] = {
    "C-Group": ("Conventional",),
    "C-Freq": ("C-Group",),
    "Rectangle": ("C-Group", "T-Group"),
    "Site": ("Trunk",),
    "T-Group": ("Site",),
    "TGID": ("T-Group",),
    "T-Freq": ("Trunk",),
    "BandPlan_P25": ("Site",),
    "BandPlan_Mot": ("Site",),
}

#: tags considered top-level "systems" regardless of what precedes them.
_TOP_LEVEL_TAGS = ("Conventional", "Trunk")


@dataclass
class TreeNode:
    record: Record
    children: List["TreeNode"] = field(default_factory=list)


def build_tree(doc: RecordDocument) -> List[TreeNode]:
    """Group ``doc.records`` into a display forest. Returns the top-level
    nodes (headers like ``TargetModel`` plus each ``Conventional``/``Trunk``
    system, plus any record that couldn't be attached to a parent)."""
    top_level: List[TreeNode] = []
    nodes_by_tag: Dict[str, TreeNode] = {}

    for record in doc.records:
        node = TreeNode(record=record)
        parent_tags = () if record.tag in _TOP_LEVEL_TAGS else _PARENT_OF.get(record.tag, ())
        parent_node: Optional[TreeNode] = None
        for parent_tag in parent_tags:
            parent_node = nodes_by_tag.get(parent_tag)
            if parent_node is not None:
                break
        if parent_node is not None:
            parent_node.children.append(node)
        else:
            top_level.append(node)
        nodes_by_tag[record.tag] = node

    return top_level


def render_tree(nodes: List[TreeNode], indent: int = 0) -> str:
    lines = []
    for node in nodes:
        prefix = "  " * indent
        summary_field = node.record.get(2, "")  # 0-based fields-index 2 == column 3, "name" on most tags
        label = f"{node.record.tag}"
        if summary_field:
            label += f": {summary_field}"
        lines.append(f"{prefix}{label} (arity={node.record.arity})")
        if node.children:
            lines.append(render_tree(node.children, indent + 1))
    return "\n".join(line for line in lines if line)
