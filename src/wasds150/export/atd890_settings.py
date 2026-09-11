"""Replay the captured Optional Settings and hot keys into a CPS bundle.

The template (:mod:`wasds150.export.atd890_settings_template`) is the
operator's own configured Export All. Replaying it means every generated
bundle carries the settings from ``docs/at-d890uv-programming.md`` - Digital
Monitor on both slots, promiscuous receive, dual watch, AM air on the B
receiver, the key assignments - instead of the operator re-entering them
after each import.

Two things cannot simply be replayed: the operator's identity, which the
template deliberately does not store (filled from :class:`Atd890Settings`),
and zone names, which change with the plan. A changed cell in a column whose
name mentions a zone must name a zone this bundle has; if it does not, the
first zone is used and a warning says so.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple

from wasds150 import station
from wasds150.export.atd890_settings_template import SettingsTemplate


@dataclass
class Atd890Settings:
    callsign: str = station.CALLSIGN
    #: The operator's DMR ID (see :mod:`wasds150.station`).
    radio_id: int = station.DMR_ID
    #: Column name -> value, applied to every row of every settings file that
    #: has that column (for example ``{"TOT": "180"}``).
    overrides: Dict[str, str] = field(default_factory=dict)


def _csv(rows: List[List[str]]) -> str:
    buffer = io.StringIO()
    csv.writer(buffer, quoting=csv.QUOTE_ALL, lineterminator="\r\n").writerows(rows)
    return buffer.getvalue()


def render_settings_files(
    template: SettingsTemplate, *, zone_names: Iterable[str], settings: Atd890Settings = None
) -> Tuple[Dict[str, str], List[str]]:
    settings = settings or Atd890Settings()
    zones = list(zone_names)
    files: Dict[str, str] = {}
    warnings: List[str] = []
    for entry in template.files:
        rows = [list(row) for row in entry.rows]
        headers = [h.strip() for h in entry.header]
        for r, c, kind in entry.identity:
            if r < len(rows) and c < len(rows[r]):
                rows[r][c] = settings.callsign if kind == "callsign" else str(settings.radio_id)
        for name, value in settings.overrides.items():
            if name in headers:
                column = headers.index(name)
                for row in rows:
                    if column < len(row):
                        row[column] = value
        for r, c, _before, after in entry.changed:
            column_name = headers[c] if c < len(headers) else ""
            if "zone" not in column_name.lower() or not after or after.lower() == "none" or after in zones:
                continue
            replacement = zones[0] if zones else after
            warnings.append(
                f"{entry.name}: {column_name} named zone {after!r}, which this bundle does not have; "
                f"using {replacement!r}"
            )
            rows[r][c] = replacement
        files[entry.name] = _csv([list(entry.header)] + rows)
    return files, warnings
