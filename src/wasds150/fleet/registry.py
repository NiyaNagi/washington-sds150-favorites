"""Every radio in the fleet and the road its memory is loaded by.

Registration is an explicit dict, like :mod:`wasds150.radios.registry`. Step
instructions are the checklists the per-radio docs used to carry by hand;
``wasds150 fleet docs`` writes them into ``docs/fleet-updates.md`` so the
wizard and the documentation read the same text.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from wasds150.fleet.model import (
    LOAD_AUTOMATED,
    LOAD_GUIDED,
    STEP_AUTO,
    STEP_CONFIRM,
    STEP_MANUAL,
    VERIFY_HASH,
    VERIFY_NONE,
    VERIFY_READBACK,
    FleetRadio,
    InputSpec,
    StepSpec,
    VendorApp,
)
from wasds150.plans.template import fleet_plan_id

FLEET_DOC = "docs/fleet-updates.md"

#: ``Path.home() / Documents / Uniden / BCDx36HP``, as the installer resolves
#: it (see :func:`wasds150.installer.sentinel_workspace.default_workspace_path`).
_SENTINEL_WORKSPACE_DEFAULT = r"%USERPROFILE%\Documents\Uniden\BCDx36HP"

SENTINEL = VendorApp(
    id="sentinel",
    label="Uniden BCDx36HP Sentinel",
    exe_candidates=(r"C:\Program Files (x86)\Uniden\BCDx36HP Sentinel\BCDx36HP_Sentinel.exe",),
)
MCP_D75 = VendorApp(
    id="mcp-d75",
    label="Kenwood MCP-D75",
    exe_candidates=(
        r"C:\Program Files (x86)\Kenwood\MCP-D75\MCP-D75.exe",
        r"C:\Program Files\Kenwood\MCP-D75\MCP-D75.exe",
    ),
    open_with_file=True,
)
RT_FTX1 = VendorApp(
    id="rt-ftx1",
    label="RT Systems FTX-1 Programmer",
    exe_candidates=(r"C:\Program Files\RT Systems V5 - FTX1 Programming\Yaesu\FTX1_V5\RadioEngine_V5.exe",),
    open_with_file=True,
)
D890_CPS = VendorApp(
    id="d890-cps",
    label="Anytone D890UV CPS 1.05",
    exe_candidates=(r"C:\D890UV\D890UV.exe",),
)

SDS150 = FleetRadio(
    radio_id="sds150",
    plan_id="",
    target_id="",
    load_path=LOAD_AUTOMATED,
    inputs=(
        InputSpec(
            "sentinel_workspace", "dir", "Sentinel workspace",
            default=_SENTINEL_WORKSPACE_DEFAULT,
            help="The folder holding Profile\\ and FavoriteLists\\.",
        ),
        InputSpec(
            "sentinel_profile", "text", "Sentinel profile",
            help="One of the folders under <workspace>\\Profile.",
        ),
    ),
    steps=(
        StepSpec(
            "close-sentinel", "Close Sentinel",
            "Close Sentinel completely. The installer writes Favorites Lists straight into the "
            "workspace and will not run while Sentinel has it open.",
            kind=STEP_CONFIRM,
        ),
        StepSpec(
            "install", "Install the Favorites Lists",
            "Dry-run, then install every enabled, populated list into profile {sentinel_profile}. "
            "The workspace is backed up and verified first, and any failure restores the backup.",
            kind=STEP_AUTO, artifacts=("backup",), verify=True,
        ),
        StepSpec(
            "reopen-sentinel", "Reopen Sentinel and write the scanner",
            "Reopen Sentinel, open profile {sentinel_profile}, spot-check a few lists, then connect "
            "the SDS150 and write it from Sentinel.",
        ),
    ),
    verify=VERIFY_HASH,
    vendor_app=SENTINEL,
    doc=FLEET_DOC,
    notes="Receive only. Installs Favorites Lists, not a memory plan; trunked P25 lives here.",
)

TD_H9 = FleetRadio(
    radio_id="td-h9",
    plan_id=fleet_plan_id("td-h9"),
    target_id="chirp-csv",
    load_path=LOAD_AUTOMATED,
    inputs=(
        InputSpec("com_port", "com_port", "Programming cable port", help="For example COM7."),
        InputSpec(
            "label", "text", "Backup label", required=False, default="td-h9",
            help="Prefix for the backup images in radio-backups\\ (radio-a, radio-b, ...).",
        ),
    ),
    steps=(
        StepSpec(
            "connect", "Connect the radio",
            "Plug the cable into the same USB socket as last time (the Prolific driver binds per "
            "socket), seat the two-pin plug fully - it seats about a millimetre after it looks "
            "seated - and turn the radio on.",
            kind=STEP_CONFIRM,
        ),
        StepSpec(
            "backup", "Back up and dry-run",
            "Read the radio on {com_port}, save a timestamped image to radio-backups\\, and stage "
            "{export} into it. Nothing is written to the radio.",
            kind=STEP_AUTO, artifacts=("backup", "export"),
        ),
        StepSpec(
            "flash", "Write the radio",
            "Write the staged image, then read the radio back and compare every channel "
            "with the file.",
            kind=STEP_AUTO, verify=True,
        ),
        StepSpec(
            "power-cycle", "Power-cycle the radio",
            "Turn the radio off and on: it stays in programming mode after a write, and the next "
            "handshake fails until it is power-cycled.",
        ),
    ),
    verify=VERIFY_READBACK,
    doc=FLEET_DOC,
    notes="Programmed through CHIRP in .venv-chirp by scripts\\radios\\program_tdh9.py.",
)

TH_D75 = FleetRadio(
    radio_id="th-d75",
    plan_id=fleet_plan_id("th-d75"),
    target_id="thd75-file",
    load_path=LOAD_GUIDED,
    inputs=(
        InputSpec(
            "backup_d75", "file", "Pre-change radio backup", required=False,
            help="Defaults to the newest radio-backups\\th-d75\\*.d75; the export is built on it.",
        ),
        InputSpec(
            "mcp_app", "app_path", "MCP-D75 program", required=False,
            default=MCP_D75.exe_candidates[0],
        ),
    ),
    steps=(
        StepSpec(
            "read-radio", "Read the radio into a fresh backup",
            "In MCP-D75, read the radio and save it into radio-backups\\th-d75\\ with today's date. "
            "The export is patched onto this exact image and the finalize step restores its "
            "settings. Never use COM3 for this radio: it is an unrelated device.",
        ),
        StepSpec(
            "export", "Export the memory file",
            "Export {plan_id} with target thd75-file, based on {backup_d75}.",
            kind=STEP_AUTO, artifacts=("export",),
        ),
        StepSpec(
            "open-mcp", "Open the file in MCP-D75",
            "Start MCP-D75 with {export}; if it opens empty, use File > Open on that file.",
            kind=STEP_AUTO,
        ),
        StepSpec(
            "import-dstar-tsv", "Import the D-STAR repeater list",
            "In MCP-D75, import the filtered official repeater TSV under Repeater List for "
            "TH-D75A (K-type/U.S.A. and Canada).",
        ),
        StepSpec(
            "save", "Save from MCP-D75",
            "Save the file from MCP-D75 (File > Save As) next to {export}; the next step needs it.",
            artifacts=("mcp_saved",),
        ),
        StepSpec(
            "finalize", "Restore the preserved regions",
            "Run scripts\\radios\\finalize_thd75_image.py with {backup_d75} and the MCP-saved file. "
            "MCP normalises empty special-memory pages on save; this restores every byte outside "
            "ordinary memories, group names and the D-STAR region.",
            kind=STEP_AUTO, artifacts=("final",),
        ),
        StepSpec(
            "write-radio", "Write the radio",
            "Open {final} in MCP-D75, check the memory count and the local DR list, then write "
            "it to the radio.",
        ),
        StepSpec(
            "readback-save", "Read back for comparison",
            "Read the radio again in MCP-D75 and save it into radio-backups\\th-d75\\ as a "
            "read-back, so the written image can be compared byte for byte.",
            optional=True, verify=True,
        ),
    ),
    verify=VERIFY_HASH,
    vendor_app=MCP_D75,
    doc=FLEET_DOC,
    notes="Hardware transfer is MCP-D75 only: CHIRP's TH-D75 clone path fails on this radio.",
)

FTX1 = FleetRadio(
    radio_id="ftx1",
    plan_id=fleet_plan_id("ftx1"),
    target_id="ftx1-file",
    load_path=LOAD_GUIDED,
    inputs=(
        InputSpec(
            "rt_app", "app_path", "RT Systems FTX-1 program", required=False,
            default=RT_FTX1.exe_candidates[0],
        ),
        InputSpec(
            "copy_to", "dir", "Also copy the file to", required=False,
            help="The folder RT Systems opens files from, if not the export folder.",
        ),
    ),
    steps=(
        StepSpec(
            "export", "Export the memory file",
            "Export {plan_id} with target ftx1-file (patched onto radio-templates\\ftx1-blank.FTX1).",
            kind=STEP_AUTO, artifacts=("export",),
        ),
        StepSpec(
            "open-rt", "Open the file in RT Systems",
            "Open {export} in the RT Systems FTX-1 programmer.",
            kind=STEP_AUTO,
        ),
        StepSpec(
            "send-to-radio", "Send to the radio",
            "Connect the FTX-1 and send the file to the radio from RT Systems' communications menu.",
        ),
        StepSpec(
            "confirm-count", "Check the radio",
            "On the radio, confirm the last used memory matches the export ({rows} channels) and "
            "that a repeater near home keys with its tone.",
            kind=STEP_CONFIRM, verify=True,
        ),
    ),
    verify=VERIFY_NONE,
    vendor_app=RT_FTX1,
    doc=FLEET_DOC,
    notes="The FTX-1 profile is unverified: check a few memories against the manual after the first load.",
)

AT_D890UV = FleetRadio(
    radio_id="at-d890uv",
    plan_id=fleet_plan_id("at-d890uv"),
    target_id="atd890-cps",
    load_path=LOAD_GUIDED,
    inputs=(
        InputSpec(
            "cps_app", "app_path", "D890UV CPS", required=False, default=D890_CPS.exe_candidates[0],
        ),
        InputSpec(
            "copy_to", "dir", "Also copy the bundle to", required=False,
            help="A folder the CPS's import dialog opens easily.",
        ),
        InputSpec(
            "rdt_base", "file", "Saved codeplug (.rdt)", required=False,
            help="The .rdt saved after setting the Optional Settings; the bundle is imported into it.",
        ),
    ),
    steps=(
        StepSpec(
            "export", "Export the CPS bundle",
            "Export {plan_id} with target atd890-cps.",
            kind=STEP_AUTO, artifacts=("export", "lst"),
        ),
        StepSpec(
            "open-cps", "Start the CPS",
            "Start the D890UV CPS.",
            kind=STEP_AUTO,
        ),
        StepSpec(
            "new-or-open-rdt", "Open the codeplug",
            "File > Open {rdt_base} to keep your Optional Settings, or File > New for a first build. "
            "Model > Model Information must match the radio's frequency range.",
        ),
        StepSpec(
            "import-all", "Import the bundle",
            "Tool > Import > choose {lst} > Import All. A name the CPS cannot resolve means the "
            "export is stale: re-export rather than editing in place.",
            artifacts=("lst",),
        ),
        StepSpec(
            "import-contacts", "Import the contact list",
            "Tool > Import > Digital Contact List > choose {contacts}. A worldwide list takes several "
            "minutes. The file's columns are not yet confirmed against this CPS, so check a few "
            "entries afterwards.",
            optional=True, artifacts=("contacts",),
        ),
        StepSpec(
            "write-radio", "Save and write",
            "Save the codeplug into radio-backups\\at-d890uv\\, then Write to radio (Other Data; "
            "Digital Contact List only if one was loaded).",
        ),
        StepSpec(
            "export-all-readback", "Read back",
            "Read from radio, then Tool > Export > Export All into a new "
            "radio-backups\\at-d890uv\\<date>-readback\\ folder.",
            optional=True, verify=True,
        ),
        StepSpec(
            "diff-readback", "Compare the read-back",
            "Compare the read-back folder with the generated bundle, table by table.",
            kind=STEP_AUTO, optional=True, verify=True,
        ),
    ),
    verify=VERIFY_HASH,
    vendor_app=D890_CPS,
    doc=FLEET_DOC,
    notes="Profile unverified until a written bundle has been read back clean.",
)

FLEET: Dict[str, FleetRadio] = {
    radio.radio_id: radio for radio in (SDS150, TD_H9, TH_D75, FTX1, AT_D890UV)
}


def fleet_ids() -> List[str]:
    return list(FLEET)


def list_fleet() -> Dict[str, FleetRadio]:
    return dict(FLEET)


def fleet_info(radio_id: str) -> Optional[Dict[str, Any]]:
    """How a radio is loaded, for pages that decide what to offer (the Radios
    tab enables direct programming only for automatically loaded radios)."""
    radio = FLEET.get(str(radio_id).strip().lower())
    if radio is None:
        return None
    return {
        "radio_id": radio.radio_id,
        "plan_id": radio.plan_id,
        "target_id": radio.target_id,
        "load_path": radio.load_path,
        "inputs": [spec.to_dict() for spec in radio.inputs],
    }


def get_fleet_radio(radio_id: str) -> FleetRadio:
    key = str(radio_id).strip().lower()
    try:
        return FLEET[key]
    except KeyError:
        raise KeyError(f"unknown fleet radio {radio_id!r}; known: {', '.join(FLEET)}") from None
