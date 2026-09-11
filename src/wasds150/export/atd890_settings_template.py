"""Capture the Anytone CPS Optional Settings and hot keys from two Export Alls.

The CPS keeps the radio's menu settings in ``OptionalSetting.CSV`` and its
key assignments in ``HotKey_*.CSV`` - wide, mostly numeric tables whose
layout is not documented. Rather than guess it, the operator captures it
once:

1. CPS: File > New, then Tool > Export > Export All into
   ``radio-backups/at-d890uv/fixtures/fresh/``.
2. Apply the settings table from ``docs/at-d890uv-programming.md``, then
   Export All again into ``radio-backups/at-d890uv/fixtures/configured/``.
3. ``python scripts/radios/build_atd890_settings_template.py`` diffs the two
   and writes :data:`TEMPLATE_PATH`.

The template is the configured tables plus the list of cells that changed.
Cells that carry the operator's identity (Radio ID, call sign, power-on
text) are blanked, recorded, and filled in again at export, so the committed
template holds nothing personal. :mod:`wasds150.export.atd890_settings`
replays it into every bundle.
"""
from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SETTINGS_PATTERNS = (re.compile(r"^OptionalSetting.*\.CSV$", re.IGNORECASE), re.compile(r"^HotKey.*\.CSV$", re.IGNORECASE))

#: Lower-cased column name -> which identity value belongs there.
IDENTITY_COLUMNS = {
    "radio id": "radio_id",
    "callsign": "callsign",
    "call sign": "callsign",
    "power-on display char": "callsign",
    "power on display char": "callsign",
    "power-on char": "callsign",
}

TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "data" / "atd890_settings_template.json"


@dataclass
class SettingsFile:
    name: str
    header: List[str]
    rows: List[List[str]]
    #: ``[row, column, fresh value, configured value]`` for every cell the
    #: operator changed (identity cells excluded).
    changed: List[List[Any]] = field(default_factory=list)
    #: ``[row, column, "callsign" | "radio_id"]`` for blanked identity cells.
    identity: List[List[Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "header": self.header, "rows": self.rows, "changed": self.changed,
                "identity": self.identity}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SettingsFile":
        return cls(name=data["name"], header=list(data["header"]), rows=[list(r) for r in data["rows"]],
                   changed=[list(c) for c in data.get("changed", [])],
                   identity=[list(i) for i in data.get("identity", [])])


@dataclass
class SettingsTemplate:
    files: List[SettingsFile]
    source: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"source": self.source, "files": [f.to_dict() for f in self.files]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SettingsTemplate":
        return cls(files=[SettingsFile.from_dict(f) for f in data.get("files", [])], source=dict(data.get("source", {})))

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=1) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "SettingsTemplate":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def read_cps_csv(path: Path) -> Tuple[List[str], List[List[str]]]:
    rows = list(csv.reader(io.StringIO(Path(path).read_bytes().decode("utf-8-sig", errors="replace"))))
    return (rows[0] if rows else []), rows[1:]


def _settings_files(folder: Path) -> Dict[str, Path]:
    return {
        p.name: p for p in sorted(Path(folder).iterdir())
        if p.is_file() and any(pattern.match(p.name) for pattern in SETTINGS_PATTERNS)
    }


def diff_export_all(fresh: Path, configured: Path) -> SettingsTemplate:
    configured_files = _settings_files(configured)
    if not configured_files:
        raise ValueError(f"no OptionalSetting/HotKey CSV files in {configured}")
    fresh_files = _settings_files(fresh)
    files: List[SettingsFile] = []
    for name in sorted(configured_files, key=str.lower):
        header, rows = read_cps_csv(configured_files[name])
        _fresh_header, fresh_rows = read_cps_csv(fresh_files[name]) if name in fresh_files else ([], [])
        changed: List[List[Any]] = []
        identity: List[List[Any]] = []
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                column = header[c].strip().lower() if c < len(header) else ""
                if column in IDENTITY_COLUMNS:
                    identity.append([r, c, IDENTITY_COLUMNS[column]])
                    row[c] = ""
                    continue
                before = fresh_rows[r][c] if r < len(fresh_rows) and c < len(fresh_rows[r]) else ""
                if before != value:
                    changed.append([r, c, before, value])
        files.append(SettingsFile(name=name, header=header, rows=rows, changed=changed, identity=identity))
    return SettingsTemplate(files=files, source={"fresh": Path(fresh).name, "configured": Path(configured).name})


def load_packaged_template(path: Optional[Path] = None) -> Optional[SettingsTemplate]:
    """The captured template, or ``None`` until one has been captured."""
    path = Path(path) if path is not None else TEMPLATE_PATH
    return SettingsTemplate.load(path) if path.exists() else None
