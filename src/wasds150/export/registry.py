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
from typing import Any, Callable, Dict, List

from wasds150.export.atd890_cps import render_atd890, write_atd890
from wasds150.export.chirp_csv import render_chirp_csv, write_chirp_csv
from wasds150.export.ftx1_target import render_ftx1, write_ftx1
from wasds150.export.id52_csv import render_id52, write_id52
from wasds150.export.thd75_target import render_thd75, write_thd75
from wasds150.plan.resolve import ResolvedPlan


@dataclass(frozen=True)
class ExportTarget:
    id: str
    radio_id: str
    label: str
    #: File suffix for single-file targets; empty for a directory bundle.
    extension: str
    description: str
    #: Both callables return a result exposing ``.rows`` and ``.warnings``;
    #: directory targets also expose ``.files`` (every path written).
    render: Callable[[ResolvedPlan], Any]
    write: Callable[[ResolvedPlan, Path], Any]
    available: bool = True
    #: ``"file"`` writes one file at the given path; ``"directory"`` writes a
    #: set of files into a directory of that name (vendor CPS import bundles).
    kind: str = "file"

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

#: Native Yaesu memory file. Produced by patching a blank structural template
#: that ships in the repository, so the bytes this project has not decoded
#: keep whatever the programmer wrote rather than being guessed at.
FTX1_FILE = ExportTarget(
    id="ftx1-file",
    radio_id="ftx1",
    label="Yaesu FTX-1 memory file",
    extension=".FTX1",
    description=(
        "Native .FTX1 memory file, openable directly in the RT Systems "
        "programmer. Writes up to 999 memories plus the 50 programmable "
        "scan-limit pairs."
    ),
    render=render_ftx1,
    write=write_ftx1,
)

THD75_FILE = ExportTarget(
    id="thd75-file",
    radio_id="th-d75",
    label="Kenwood MCP-D75 memory file",
    extension=".d75",
    description=(
        "Native MCP-D75 file based on the newest private radio backup. Only "
        "ordinary memories and group names are replaced; operator callsigns, "
        "APRS, Bluetooth, GPS and menu settings are preserved."
    ),
    render=render_thd75,
    write=write_thd75,
)

#: Anytone CPS import bundle: a directory of CSV tables plus the ``.LST``
#: manifest the CPS's "Import All" reads. Radio ID is a placeholder until the
#: operator registers a DMR ID.
ATD890_CPS = ExportTarget(
    id="atd890-cps",
    radio_id="at-d890uv",
    label="Anytone D890UV CPS bundle",
    extension="",
    kind="directory",
    description=(
        "Directory of Anytone CPS 1.05 CSV tables (channels, zones, scan "
        "lists, talkgroups, receive groups, AM air and FM lists) plus a .LST "
        "manifest. In the CPS: Tool > Import > choose the .LST > Import All."
    ),
    render=render_atd890,
    write=write_atd890,
)

#: Icom CS-52 (and the radio's own SD card) read plain CSV: one file per
#: memory group plus the D-STAR repeater list, in the folders the radio
#: expects on its card.
ID52_CSV = ExportTarget(
    id="id52-csv",
    radio_id="id-52a",
    label="Icom ID-52A CSV set",
    extension="",
    kind="directory",
    description=(
        "Directory holding Csv/MemoryCh/<group>.csv (one per memory group) "
        "and Csv/RptList/DSTAR_Near_Home.csv. Import each group in CS-52 "
        "(Memory CH > right-click a group > Import > Group), or copy the Csv "
        "folder into ID-52\\ on the radio's microSD card."
    ),
    render=render_id52,
    write=write_id52,
)

_REGISTRY: Dict[str, ExportTarget] = {
    CHIRP_CSV_TD_H9.id: CHIRP_CSV_TD_H9,
    ID52_CSV.id: ID52_CSV,
    RT_SYSTEMS_CSV_FTX1.id: RT_SYSTEMS_CSV_FTX1,
    FTX1_FILE.id: FTX1_FILE,
    THD75_FILE.id: THD75_FILE,
    ATD890_CPS.id: ATD890_CPS,
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
