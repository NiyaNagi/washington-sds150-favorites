"""Compare a generated AT-D890UV bundle with what the radio holds.

After a write, the operator reads the radio back in the CPS and runs
Tool > Export > Export All into a fresh folder. :func:`compare_bundle` then
checks that folder against the generated bundle table by table: rows are
matched by their key column (channel name, zone name, talkgroup ID, ...),
never by position, and each cell is compared. A clean comparison is the
evidence that flips the radio profile to ``verified=True``.

* ``No.`` is always ignored (the CPS renumbers).
* Frequencies compare numerically, so ``144.85000`` equals ``144.85``.
* ``|``-joined member lists (zone and scan-list members) compare as a set
  first; the same members in another order are reported separately and do
  not make the comparison dirty.
* :data:`CPS_NORMALIZED_COLUMNS` lists columns the CPS rewrites on its own.
  It is empty until the first real read-back shows which ones they are; any
  column added there must be explained next to it.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

KEY_COLUMNS: Dict[str, Tuple[str, ...]] = {
    "Channel.CSV": ("Channel Name",),
    "RadioIDList.CSV": ("Name",),
    "DMRZone.CSV": ("Zone Name",),
    "ScanList.CSV": ("Scan List Name",),
    "DMRTalkGroups.CSV": ("Radio ID",),
    "FM.CSV": ("Frequency[MHz]",),
    "DMRReceiveGroupCallList.CSV": ("Group Name",),
    "AMAir.CSV": ("Name",),
    "AMZone.CSV": ("Zone Name",),
}
ALWAYS_IGNORED = frozenset({"No."})
CPS_NORMALIZED_COLUMNS: Dict[str, Tuple[str, ...]] = {}
#: Nothing is ignored by default: the bundle carries the operator's real DMR
#: ID, so a different one in the read-back is a real difference.
DEFAULT_IGNORES: Set[Tuple[str, str]] = set()


@dataclass
class CellDiff:
    file: str
    key: str
    column: str
    generated: str
    readback: str
    order_only: bool = False

    def __str__(self) -> str:
        kind = "member order" if self.order_only else "value"
        return f"{self.file} [{self.key}] {self.column}: {self.generated!r} -> {self.readback!r} ({kind})"


@dataclass
class FileDiff:
    name: str
    missing_file: bool = False
    missing_rows: List[str] = field(default_factory=list)
    extra_rows: List[str] = field(default_factory=list)
    cells: List[CellDiff] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not (self.missing_file or self.missing_rows or self.extra_rows
                    or any(not c.order_only for c in self.cells))


@dataclass
class BundleDiff:
    files: List[FileDiff] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return all(f.clean for f in self.files)

    def summary(self) -> str:
        lines = []
        for f in self.files:
            if f.missing_file:
                lines.append(f"{f.name}: missing from the read-back")
                continue
            for key in f.missing_rows:
                lines.append(f"{f.name}: row {key!r} missing from the read-back")
            for key in f.extra_rows:
                lines.append(f"{f.name}: row {key!r} only in the read-back")
            lines.extend(str(cell) for cell in f.cells)
        if not lines:
            return "clean: the read-back matches the bundle"
        head = "clean apart from member order" if self.clean else "DIFFERENT"
        return "\n".join([head] + lines)

    def to_dict(self) -> Dict[str, object]:
        return {
            "clean": self.clean,
            "files": [
                {
                    "name": f.name,
                    "clean": f.clean,
                    "missing_file": f.missing_file,
                    "missing_rows": f.missing_rows,
                    "extra_rows": f.extra_rows,
                    "cells": [c.__dict__ for c in f.cells],
                }
                for f in self.files
            ],
        }


def _read(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    rows = list(csv.reader(io.StringIO(path.read_bytes().decode("utf-8-sig", errors="replace"))))
    if not rows:
        return [], []
    header = [h.strip() for h in rows[0]]
    return header, [dict(zip(header, row)) for row in rows[1:]]


def _find(folder: Path, name: str) -> Optional[Path]:
    for candidate in folder.iterdir():
        if candidate.is_file() and candidate.name.lower() == name.lower():
            return candidate
    return None


def _keyed(rows: List[Dict[str, str]], keys: Sequence[str]) -> Dict[str, Dict[str, str]]:
    keyed: Dict[str, Dict[str, str]] = {}
    for row in rows:
        base = " / ".join(row.get(k, "").strip() for k in keys)
        key, n = base, 2
        while key in keyed:
            key, n = f"{base} #{n}", n + 1
        keyed[key] = row
    return keyed


def _same(a: str, b: str) -> bool:
    a, b = (a or "").strip(), (b or "").strip()
    if a == b:
        return True
    try:
        return abs(float(a) - float(b)) < 1e-6
    except ValueError:
        return False


def _same_members(a: str, b: str) -> bool:
    left, right = a.split("|"), b.split("|")
    if len(left) != len(right):
        return False
    return all(_same(x, y) for x, y in zip(sorted(left), sorted(right)))


def compare_bundle(
    generated_dir: Path, readback_dir: Path, *, ignore: Iterable[Tuple[str, str]] = ()
) -> BundleDiff:
    generated_dir, readback_dir = Path(generated_dir), Path(readback_dir)
    ignored = set(DEFAULT_IGNORES) | {(f, c) for f, c in ignore}
    result = BundleDiff()
    for name, keys in KEY_COLUMNS.items():
        generated = _find(generated_dir, name)
        if generated is None:
            continue
        diff = FileDiff(name=name)
        result.files.append(diff)
        readback = _find(readback_dir, name)
        if readback is None:
            diff.missing_file = True
            continue
        header, generated_rows = _read(generated)
        readback_header, readback_rows = _read(readback)
        ours, theirs = _keyed(generated_rows, keys), _keyed(readback_rows, keys)
        diff.missing_rows = [key for key in ours if key not in theirs]
        diff.extra_rows = [key for key in theirs if key not in ours]
        skipped = set(CPS_NORMALIZED_COLUMNS.get(name, ())) | ALWAYS_IGNORED
        for key, row in ours.items():
            other = theirs.get(key)
            if other is None:
                continue
            for column in header:
                if column in skipped or (name, column) in ignored:
                    continue
                mine = row.get(column, "")
                if column not in readback_header:
                    diff.cells.append(CellDiff(name, key, column, mine, "<column missing>"))
                    continue
                theirs_value = other.get(column, "")
                if _same(mine, theirs_value):
                    continue
                if "|" in mine or "|" in theirs_value:
                    if _same_members(mine, theirs_value):
                        diff.cells.append(CellDiff(name, key, column, mine, theirs_value, order_only=True))
                        continue
                diff.cells.append(CellDiff(name, key, column, mine, theirs_value))
    return result
