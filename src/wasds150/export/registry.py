"""Registered export targets.

Adding a radio to this project is meant to be additive: write a capability
profile, write a writer, register it here.  Nothing in the existing SDS150
path needs to change, and no exporter can be reached by a plan built for a
different radio because the target declares which radio it serves.

Note that the SDS150 is deliberately *not* a target here.  Its ``.hpe`` output
is hierarchical - Favorites Lists containing systems, sites and departments -
and is produced from the catalog by :mod:`wasds150.bundle`.  Targets in this
registry consume a flat, ordered :class:`~wasds150.plan.resolve.ResolvedPlan`,
which is the right shape for a memory-list transceiver and the wrong shape for
a trunk-tracking scanner.  Forcing the two together would lose structure the
scanner needs.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List

from wasds150.export.chirp_csv import ChirpCsvResult, render_chirp_csv, write_chirp_csv
from wasds150.plan.resolve import ResolvedPlan


@dataclass(frozen=True)
class ExportTarget:
    id: str
    radio_id: str
    label: str
    extension: str
    description: str
    render: Callable[[ResolvedPlan], ChirpCsvResult]
    write: Callable[[ResolvedPlan, Path], ChirpCsvResult]
    available: bool = True

    def check_radio(self, resolved: ResolvedPlan) -> None:
        if resolved.profile.id != self.radio_id:
            raise ValueError(
                f"export target {self.id!r} serves {self.radio_id!r} but the plan "
                f"targets {resolved.profile.id!r}"
            )


CHIRP_CSV_TD_H9 = ExportTarget(
    id="chirp-csv",
    radio_id="td-h9",
    label="CHIRP Generic CSV",
    extension=".csv",
    description=(
        "21-column CHIRP Generic CSV. Import in CHIRP, then upload to the "
        "radio. Also readable by RT Systems and the TIDRADIO factory CPS."
    ),
    render=render_chirp_csv,
    write=write_chirp_csv,
)

#: Placeholder so the FTX-1 path is visible rather than silently absent.
#:
#: What is known so far, from the installed programmer at
#: ``C:\Program Files\RT Systems V5 - FTX1 Programming``:
#:
#: * The native memory file is ``*.FTX1`` - the file dialog filter string
#:   "Radio Data Files (*.FTX1)" is embedded in ``Yaesu\FTX1_V5\FTX1_V5.dll``.
#: * The install ships ``Sqlite3_V5.dll`` and ``Sqlite330_V5.dll``, so the
#:   container is very likely a SQLite database rather than an opaque blob.
#:   That has not been confirmed against an actual saved file yet.
#: * The programmer can import and export CSV, but RT Systems uses a different
#:   column set for every radio model and does not publish the FTX-1 layout.
#:
#: The way to finish this is to save one file from the programmer and read its
#: schema, rather than guessing a column order. CHIRP's ``RTCSVRadio`` driver
#: has a reverse-engineered column map that is a reasonable starting point.
RT_SYSTEMS_CSV_FTX1 = ExportTarget(
    id="rtsystems-csv",
    radio_id="ftx1",
    label="RT Systems CSV (Yaesu FTX-1)",
    extension=".csv",
    description=(
        "NOT IMPLEMENTED. Needs the column layout used by RT Systems YPS-FTX1, "
        "which is per-model and undocumented; derive it from a file saved by "
        "the installed programmer."
    ),
    render=render_chirp_csv,
    write=write_chirp_csv,
    available=False,
)

_REGISTRY: Dict[str, ExportTarget] = {
    CHIRP_CSV_TD_H9.id: CHIRP_CSV_TD_H9,
    RT_SYSTEMS_CSV_FTX1.id: RT_SYSTEMS_CSV_FTX1,
}


def list_targets() -> Dict[str, ExportTarget]:
    return dict(_REGISTRY)


def targets_for_radio(radio_id: str) -> List[ExportTarget]:
    key = str(radio_id).strip().lower()
    return [t for t in _REGISTRY.values() if t.radio_id == key]


def get_target(target_id: str) -> ExportTarget:
    key = str(target_id).strip().lower()
    try:
        target = _REGISTRY[key]
    except KeyError:
        raise KeyError(
            f"unknown export target {target_id!r}; known targets: "
            f"{', '.join(sorted(_REGISTRY))}"
        ) from None
    if not target.available:
        raise NotImplementedError(f"export target {key!r} is not implemented: {target.description}")
    return target
