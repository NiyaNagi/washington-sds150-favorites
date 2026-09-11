# Updating every radio

Five radios are programmed from one catalog: the Uniden SDS150 scanner, the
TIDRADIO TD-H9, the Kenwood TH-D75A, the Yaesu FTX-1 and the Anytone
AT-D890UV. This page is the procedure for bringing all of them up to date
after the catalog changes, and the per-radio checklists below are generated
from `src/wasds150/fleet/registry.py` (`wasds150 fleet docs`), so the wizard
and this page cannot drift apart.

## The one step

Double-click **`Update Radios.cmd`** in the repository folder.

It opens the web UI straight on the **Fleet** tab, working from the
repository's own home, `.wasds150-home`, which holds the refreshed catalog and
your RadioReference exports. Then:

1. **Radios.** Out-of-date radios are ticked for you; every radio shows as out
   of date until it has been synced once.
2. **Sources.** Tick the sources to refresh. The bulk download, FCC ULS, is
   unticked by default; tick it about once a month. FAA NASR refreshes on its
   own: it checks the FAA's small index page and downloads the ~250 MB cycle
   only when a new one is posted (every 28 days).
3. Tick **Write to the radios**. Without it the update is a dry run: every
   source is refreshed and every radio exported, but nothing is written.
4. Press **Update selected**. The radios run one after another. At each
   checklist step, plug in that radio or do what the step says in its vendor
   program, then press **Done**. **Skip** passes over a step and **Abort**
   stops the update.
5. When the job shows finished, close the command window.

Programming files are written to `wasds150-output\radios\`. Radio backups go
to `radio-backups\`.

### Before the first update

Each radio card has a **Settings** section; a required setting that is missing
is flagged there and blocks that radio until it is filled in.

| Setting | Current value | What to do |
|---|---|---|
| `sds150.sentinel_profile` | `Preset` | The only profile in the Sentinel workspace. Change it if the scanner's lists live in another profile. |
| `td-h9.com_port` | not set | Plug in the programming cable, find its port in Device Manager (a Prolific USB-to-Serial entry, for example COM7), and enter it. COM3 is an unrelated device. |
| `th-d75.backup_d75` | newest `radio-backups\th-d75\*.d75` | Read the radio into a fresh backup first; the checklist's first step says how. |
| `at-d890uv.rdt_base` | not set | Optional. After setting the Optional Settings in the CPS once, save the codeplug and point this at the `.rdt`, so later imports keep them. |

### The same from a terminal

From the repository folder:

```powershell
.venv\Scripts\wasds150.exe --home .wasds150-home fleet status             # which radios are out of date, and why
.venv\Scripts\wasds150.exe --home .wasds150-home fleet settings --set td-h9.com_port=COM7
.venv\Scripts\wasds150.exe --home .wasds150-home fleet update             # dry run: refresh stale sources, export every radio
.venv\Scripts\wasds150.exe --home .wasds150-home fleet update --execute   # the same, then load each radio (asks at every manual step)
.venv\Scripts\wasds150.exe --home .wasds150-home fleet export --all       # just the programming files + reports
.venv\Scripts\wasds150.exe --home .wasds150-home fleet describe at-d890uv # one radio's checklist with your settings filled in
```

Every command needs `--home .wasds150-home`. Without it wasds150 uses an
empty per-user home and starts again from the packaged baseline. To refresh
every source at once, including the bulk downloads, name them all:

```powershell
.venv\Scripts\wasds150.exe --home .wasds150-home fleet update --only-sources wwara,seattledmr,noaa_nwr,uscg_navcen,amsat,iacc,nifc,nwac,wa_dnr,wa_emd,faa_nasr,fcc_uls,radioreference_premium,radioreference_api,sentinel_local
```

What is still unfinished is listed in [Open items](open-items.md).

## In the car (SDS150)

The scanner is loaded with six **Near Me** lists at the top, on quick keys
1-6, and every other list below them, installed but not monitored. With GPS
connected, turn the scanner on and it is already scanning what is around the
car:

| Quick key | List | At startup |
|---|---|---|
| 1 | Near Me - Public Safety: police, fire and EMS dispatch, interop and emergency operations; the trunked systems' dispatch talkgroups | on |
| 2 | Near Me - Tactical: tactical, hospital and talk-around channels and talkgroups | off |
| 3 | Near Me - Air: towers, approach, Seattle Center, CTAF/UNICOM | on |
| 4 | Near Me - Ham: repeaters around you (one entry per DMR repeater) and the national calling channels | on |
| 5 | Near Me - Rail & Marine: railroads and marine working channels | off |
| 6 | Near Me - Business & GMRS: business, utilities, media, FCC-licensed digital, GMRS repeaters | off |
| 0 | every other list (the full catalog), for trips and browsing | off |

The Near Me lists are rebuilt from the full catalog on every install:

- **Fenced.** Every group carries a location and range (its county, its
  airport, or a cluster of repeaters) and each list is installed with
  location control on, so the scanner covers only what is within reach of
  the car. Trunked systems keep their fenced sites.
- **Once.** A frequency lives in one Near Me list, the first in the order
  public safety, air, ham, tactical, rail & marine, business.
- **Live.** Encrypted channels, data (APRS, packet, paging, telemetry) and
  broadcasts that never stop (ATIS, ASOS/AWOS, NOAA weather) are left out;
  NOAA alerts are the scanner's own weather feature.

At home the three default lists scan about 300 conventional channels and
the nearby trunked sites: a pass of a few seconds, where the full catalog
took minutes. Press a quick key to add a list for the drive; the next
install puts the defaults back. On the scanner, service-type buttons mute
a kind of traffic (every Near Me channel has a service type), and **Close
Call** with priority catches strong nearby transmitters the lists do not
hold.

The handheld plans follow the same idea: every block keeps its nearest
stations first (a county's rows by the county's fence, dispatch before
tactical), and once each block has its budget, spare slots go to the
next-nearest stations wherever they are. Those beyond 60 miles are
programmed but locked out of the scan, so a fuller radio does not scan
slower; ATIS and ASOS/AWOS are programmed but not scanned either.

## How an update runs

1. **Sources.** Every configured source whose cache is stale is refreshed; any
   of them can be skipped (`--skip-sources`, or untick it). One failing source
   never stops the update. What they found is merged into the catalog once, and
   the change is recorded in `state/updates/`. The bulk download, FCC ULS
   (hundreds of MB), is refreshed only when named (`--only-sources fcc_uls`,
   or tick it); narrow it first with
   `wasds150 sources configure --fcc-within-miles 60 --fcc-emissions DMR,NXDN,P25`.
   FAA NASR is checked on every update and rebuilds `FAAAIR`, the airband list
   behind each radio's **Airports Near Home** block (the TD-H9's **Airport
   Towers**).
2. **Each radio**, one after another: resolve its plan, compare with the last
   snapshot, export, load, verify, save a snapshot, and record the sync so the
   radio stops showing as out of date.
3. **Loading** is automatic for the SDS150 (the Sentinel workspace installer:
   backup, typed `IMPORT <profile>` confirmation, automatic rollback) and the
   TD-H9 (CHIRP: backup, typed `WRITE COMn` confirmation, read-back). The
   TH-D75, FTX-1 and AT-D890UV are prepared and guided: the wizard exports,
   opens the vendor program and waits at each step below.

Without `--execute` nothing touches a radio or the Sentinel workspace: every
radio is resolved and exported, and the SDS150 install is only planned.

An update runs as a background job (`state/jobs/`). `wasds150 jobs list`,
`jobs show`, `jobs tail --follow`, `jobs answer <job> <step> done` and
`jobs cancel` work on it from any terminal, including a job the browser
started. If one radio fails, the job stops as failed and
`wasds150 fleet update --resume <job>` picks up where it stopped, reusing every
export still on disk unchanged; a job the process was killed during is marked
interrupted the next time the web UI starts, and resumes the same way.

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
| GMRS and FRS | WRWH962 | GMRS 1-7, FRS 8-14, GMRS 15-22 and the hand-added open repeaters (each on its input and access tone), all at the radio's highest power, on radios whose hardware covers 462/467 MHz - today the TD-H9 at 10 W |
| MURS | licence-free | Low power, on radios whose hardware covers 151-154 MHz |

Part 95 requires certified GMRS and MURS equipment (95.1761, 95.2761) and
limits a GMRS station to 5 W ERP on channels 1-7 and 0.5 W ERP on 8-14
(95.1767). Transmitting from radios that are not certified, and at full power
on channels 1-14, is the operator's own, explicit choice; the template does
not cap it. MURS stays at low power, inside its 2 W limit (95.2767).

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
| `td-h9.copy_to` (Also copy the file to) | no |  | Where you keep CHIRP files, if not the export folder. |

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
| `th-d75.copy_to` (Also copy the file to) | no |  | The folder you open MCP-D75 files from, if not the export folder. |

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
| `at-d890uv.contacts_to` (Also keep the contact lists in) | no |  | A standing copy of the DMR/NXDN contact lists, for example radio-configs\contacts in the repository. |

1. **Export the CPS bundle** _(automatic)_ - Export at-d890uv-fleet with target atd890-cps.
2. **Start the CPS** _(automatic)_ - Start the D890UV CPS.
3. **Open the codeplug** - File > Open <rdt_base> to keep your Optional Settings, or File > New for a first build. Model > Model Information must match the radio's frequency range.
4. **Set the NXDN unit ID** - NX Setting > Unit ID(Own) = 16240, your radioid.net NXDN ID. It is a radio-wide setting, not in the import bundle; a codeplug opened from <rdt_base> already has it.
5. **Import the bundle** - Tool > Import > choose <lst> > Import All. A name the CPS cannot resolve means the export is stale: re-export rather than editing in place.
6. **Import the contact list** _(optional)_ - Tool > Import > Digital Contact List > choose <contacts>, then the NXDN contact list (NXDNContactList.CSV in the same folder). A worldwide list takes several minutes. The files' columns are not yet confirmed against this CPS, so check a few entries afterwards.
7. **Save and write** - Save the codeplug into radio-backups\at-d890uv\, then Write to radio (Other Data; Digital Contact List only if one was loaded).
8. **Read back** _(optional)_ - Read from radio, then Tool > Export > Export All into a new radio-backups\at-d890uv\<date>-readback\ folder.
9. **Compare the read-back** _(automatic, optional)_ - Compare the read-back folder with the generated bundle, table by table.
<!-- fleet:end at-d890uv -->
