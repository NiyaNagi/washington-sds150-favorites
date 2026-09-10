# Updating every radio

Five radios are programmed from one catalog: the Uniden SDS150 scanner, the
TIDRADIO TD-H9, the Kenwood TH-D75A, the Yaesu FTX-1 and the Anytone
AT-D890UV. This page is the procedure for bringing all of them up to date
after the catalog changes, and the per-radio checklists below are generated
from `src/wasds150/fleet/registry.py` (`wasds150 fleet docs`), so the wizard
and this page cannot drift apart.

```powershell
wasds150 fleet status                     # which radios are out of date, and why
wasds150 fleet settings --set td-h9.com_port=COM7
wasds150 fleet export --all               # every radio's programming file + report
wasds150 fleet describe at-d890uv         # one radio's checklist with your settings filled in
```

## What each radio gets

Every memory-list radio is built from the same plan template
(`src/wasds150/plans/template.py`) as a `<radio>-fleet` plan. The template
writes the service taxonomy once - repeaters by band, DMR by talkgroup tier,
simplex, Seattle ACS, HF, air, SAR, wildfire, marine, rail, personal radio,
business, public safety, data, NOAA, broadcast, local packs and a catch-all -
and the radio's capability profile decides which of those blocks it can use.
Each radio's knobs cap every block so the ceilings add up to no more than the
radio holds, so a refresh that grows one service can never starve another.

Repeaters, DMR machines and the catch-all are chosen by distance from one home
point (60 miles). Marine, NOAA, GMRS/FRS/MURS and broadcast are chosen by
frequency. The RadioReference county lists (`RRC-*`) are chosen by service
type and pass the radius through their county geo-fence.

DMR channels are ordered by talkgroup tier and then distance
(`src/wasds150/catalog/dmr_talkgroup_tiers.py`): the first zone and scan list,
**DMR Core**, is the calling and local talkgroups on the nearest machines.

## Transmit

Transmit is enabled only where the operator is licensed and the radio's
hardware transmits; everything else is receive only.

| Service | Licence | Where it transmits |
|---|---|---|
| Amateur | General class, WA7DAM | Every amateur block, checked channel by channel against General privileges |
| GMRS | WRWH962 | GMRS 1-7 at 5 W and GMRS 15-22 (repeaters on their published input), on radios whose hardware covers 462/467 MHz - today the TD-H9 |
| FRS 8-14 | - | Receive only: GMRS may use these channels only at 0.5 W ERP from a handheld, below the TD-H9's lowest power step |
| MURS | licence-free | Low power, on radios whose hardware covers 151-154 MHz |

GMRS and MURS equipment is required to be certified under 47 CFR Part 95
(95.1761 and 95.2761); transmitting from radios that are not is the
operator's own, explicit choice. The power caps above are applied regardless.

## Radios

<!-- fleet:begin sds150 -->
### Uniden SDS150 (`sds150`)

- Built from every enabled, populated Favorites List in the catalog.
- Loaded **automatically**.
- Vendor program: Uniden BCDx36HP Sentinel.
- Verification: hash-compare.
- Receive only. Installs Favorites Lists, not a memory plan; trunked P25 lives here.

| Setting | Required | Default | Notes |
|---|---|---|---|
| `sds150.sentinel_workspace` (Sentinel workspace) | yes | `%USERPROFILE%\Documents\Uniden\BCDx36HP` | The folder holding Profile\ and FavoriteLists\. |
| `sds150.sentinel_profile` (Sentinel profile) | yes |  | One of the folders under <workspace>\Profile. |

1. **Close Sentinel** _(confirm)_ - Close Sentinel completely. The installer writes Favorites Lists straight into the workspace and will not run while Sentinel has it open.
2. **Install the Favorites Lists** _(automatic)_ - Dry-run, then install every enabled, populated list into profile <sentinel_profile>. The workspace is backed up and verified first, and any failure restores the backup.
3. **Reopen Sentinel and write the scanner** - Reopen Sentinel, open profile <sentinel_profile>, spot-check a few lists, then connect the SDS150 and write it from Sentinel.
<!-- fleet:end sds150 -->

<!-- fleet:begin td-h9 -->
### TIDRADIO TD-H9 (`td-h9`)

- Built from plan `td-h9-fleet`, exported as `chirp-csv`.
- Loaded **automatically**.
- Verification: readback.
- Programmed through CHIRP in .venv-chirp by scripts\radios\program_tdh9.py.

| Setting | Required | Default | Notes |
|---|---|---|---|
| `td-h9.com_port` (Programming cable port) | yes |  | For example COM7. |
| `td-h9.label` (Backup label) | no | `td-h9` | Prefix for the backup images in radio-backups\ (radio-a, radio-b, ...). |

1. **Connect the radio** _(confirm)_ - Plug the cable into the same USB socket as last time (the Prolific driver binds per socket), seat the two-pin plug fully - it seats about a millimetre after it looks seated - and turn the radio on.
2. **Back up and dry-run** _(automatic)_ - Read the radio on <com_port>, save a timestamped image to radio-backups\, and stage <export> into it. Nothing is written to the radio.
3. **Write the radio** _(automatic)_ - Write the staged image, then read the radio back and compare every channel with the file.
4. **Power-cycle the radio** - Turn the radio off and on: it stays in programming mode after a write, and the next handshake fails until it is power-cycled.
<!-- fleet:end td-h9 -->

<!-- fleet:begin th-d75 -->
### Kenwood TH-D75A (`th-d75`)

- Built from plan `th-d75-fleet`, exported as `thd75-file`.
- **Prepared and guided**: the wizard exports and opens the vendor program, then waits for you at each manual step.
- Vendor program: Kenwood MCP-D75.
- Verification: hash-compare.
- Hardware transfer is MCP-D75 only: CHIRP's TH-D75 clone path fails on this radio.

| Setting | Required | Default | Notes |
|---|---|---|---|
| `th-d75.backup_d75` (Pre-change radio backup) | no |  | Defaults to the newest radio-backups\th-d75\*.d75; the export is built on it. |
| `th-d75.mcp_app` (MCP-D75 program) | no | `C:\Program Files (x86)\Kenwood\MCP-D75\MCP-D75.exe` |  |

1. **Read the radio into a fresh backup** - In MCP-D75, read the radio and save it into radio-backups\th-d75\ with today's date. The export is patched onto this exact image and the finalize step restores its settings. Never use COM3 for this radio: it is an unrelated device.
2. **Export the memory file** _(automatic)_ - Export th-d75-fleet with target thd75-file, based on <backup_d75>.
3. **Open the file in MCP-D75** _(automatic)_ - Start MCP-D75 with <export>; if it opens empty, use File > Open on that file.
4. **Import the D-STAR repeater list** - In MCP-D75, import the filtered official repeater TSV under Repeater List for TH-D75A (K-type/U.S.A. and Canada).
5. **Save from MCP-D75** - Save the file from MCP-D75 (File > Save As) next to <export>; the next step needs it.
6. **Restore the preserved regions** _(automatic)_ - Run scripts\radios\finalize_thd75_image.py with <backup_d75> and the MCP-saved file. MCP normalises empty special-memory pages on save; this restores every byte outside ordinary memories, group names and the D-STAR region.
7. **Write the radio** - Open <final> in MCP-D75, check the memory count and the local DR list, then write it to the radio.
8. **Read back for comparison** _(optional)_ - Read the radio again in MCP-D75 and save it into radio-backups\th-d75\ as a read-back, so the written image can be compared byte for byte.
<!-- fleet:end th-d75 -->

<!-- fleet:begin ftx1 -->
### Yaesu FTX-1 (`ftx1`)

- Built from plan `ftx1-fleet`, exported as `ftx1-file`.
- **Prepared and guided**: the wizard exports and opens the vendor program, then waits for you at each manual step.
- Vendor program: RT Systems FTX-1 Programmer.
- Verification: none.
- The FTX-1 profile is unverified: check a few memories against the manual after the first load.

| Setting | Required | Default | Notes |
|---|---|---|---|
| `ftx1.rt_app` (RT Systems FTX-1 program) | no | `C:\Program Files\RT Systems V5 - FTX1 Programming\Yaesu\FTX1_V5\RadioEngine_V5.exe` |  |
| `ftx1.copy_to` (Also copy the file to) | no |  | The folder RT Systems opens files from, if not the export folder. |

1. **Export the memory file** _(automatic)_ - Export ftx1-fleet with target ftx1-file (patched onto radio-templates\ftx1-blank.FTX1).
2. **Open the file in RT Systems** _(automatic)_ - Open <export> in the RT Systems FTX-1 programmer.
3. **Send to the radio** - Connect the FTX-1 and send the file to the radio from RT Systems' communications menu.
4. **Check the radio** _(confirm)_ - On the radio, confirm the last used memory matches the export (<rows> channels) and that a repeater near home keys with its tone.
<!-- fleet:end ftx1 -->

<!-- fleet:begin at-d890uv -->
### Anytone AT-D890UV (`at-d890uv`)

- Built from plan `at-d890uv-fleet`, exported as `atd890-cps`.
- **Prepared and guided**: the wizard exports and opens the vendor program, then waits for you at each manual step.
- Vendor program: Anytone D890UV CPS 1.05.
- Verification: hash-compare.
- Profile unverified until a written bundle has been read back clean.

| Setting | Required | Default | Notes |
|---|---|---|---|
| `at-d890uv.cps_app` (D890UV CPS) | no | `C:\D890UV\D890UV.exe` |  |
| `at-d890uv.copy_to` (Also copy the bundle to) | no |  | A folder the CPS's import dialog opens easily. |
| `at-d890uv.rdt_base` (Saved codeplug (.rdt)) | no |  | The .rdt saved after setting the Optional Settings; the bundle is imported into it. |

1. **Export the CPS bundle** _(automatic)_ - Export at-d890uv-fleet with target atd890-cps.
2. **Start the CPS** _(automatic)_ - Start the D890UV CPS.
3. **Open the codeplug** - File > Open <rdt_base> to keep your Optional Settings, or File > New for a first build. Model > Model Information must match the radio's frequency range.
4. **Import the bundle** - Tool > Import > choose <lst> > Import All. A name the CPS cannot resolve means the export is stale: re-export rather than editing in place.
5. **Set the Radio ID** - Digital > Radio ID List: replace placeholder ID 1 with the DMR ID registered for WA7DAM.
6. **Save and write** - Save the codeplug into radio-backups\at-d890uv\, then Write to radio (Other Data; Digital Contact List only if one was loaded).
7. **Read back** _(optional)_ - Read from radio, then Tool > Export > Export All into a new radio-backups\at-d890uv\<date>-readback\ folder.
8. **Compare the read-back** _(automatic, optional)_ - Compare the read-back folder with the generated bundle, table by table.
<!-- fleet:end at-d890uv -->
