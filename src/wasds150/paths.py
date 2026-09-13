"""Where the fleet's files live: one root, one folder per radio.

::

    radio-data/
      <radio>/exports/      what the exporters write (archive/ keeps old ones)
      <radio>/backups/      reads taken off the radio before a write
      <radio>/readbacks/    reads taken after a write, to compare with the export
      <radio>/probes/       files built to decode a vendor format
      shared/checklists/    dated step-by-step programming sessions
      shared/contacts/      the radioid.net DMR/NXDN contact lists
      shared/licences/      licence documents (never tracked)
      shared/legacy-plans/  committed exports of the pre-fleet plans
      tools/                vendor programs used across radios

``<radio>`` is the radio id (``sds150``, ``td-h9``, ``th-d75``, ``ftx1``,
``at-d890uv``, ``id-52a``). Paths are relative to the repository root, like
every other default path in this project, so a command run from the
repository writes where the operator expects.
"""
from __future__ import annotations

from pathlib import Path

DATA_ROOT = Path("radio-data")

SHARED = DATA_ROOT / "shared"
CHECKLISTS = SHARED / "checklists"
CONTACTS = SHARED / "contacts"
LICENCES = SHARED / "licences"
LEGACY_PLANS = SHARED / "legacy-plans"
TOOLS = DATA_ROOT / "tools"


def radio_dir(radio_id: str) -> Path:
    return DATA_ROOT / radio_id


def exports_dir(radio_id: str) -> Path:
    return radio_dir(radio_id) / "exports"


def backups_dir(radio_id: str) -> Path:
    return radio_dir(radio_id) / "backups"


def readbacks_dir(radio_id: str) -> Path:
    return radio_dir(radio_id) / "readbacks"


def probes_dir(radio_id: str) -> Path:
    return radio_dir(radio_id) / "probes"


#: The structural FTX-1 template the exporter patches.
FTX1_TEMPLATES = radio_dir("ftx1") / "templates"
#: Files the operator saved from the FTX-1 programmer, read by the FTX-1 scripts.
FTX1_SOURCE_FILES = radio_dir("ftx1") / "source-files"
FTX1_RADIO_READ = FTX1_SOURCE_FILES / "ftx1-wa-radio-read-2026-08-19.FTX1"
#: Manuals, reference images and the operator's tracked current TH-D75 image.
TH_D75_REFERENCE = radio_dir("th-d75") / "reference"
#: The whole-catalog SDS150 bundle ``wasds150 generate`` writes.
SDS150_GENERATE = exports_dir("sds150") / "generate"
