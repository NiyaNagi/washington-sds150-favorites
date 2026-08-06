# Sentinel Refresh, Import, and Dashboard Runbook

This runbook records the reusable procedure used to rebuild the personal
Washington SDS150 bundle from an updated local Uniden Sentinel HPDB. Licensed
HPDB records and generated HPE files remain local and are not committed.

## Latest verified local refresh

The August 2, 2026 Sentinel master database was read successfully on Windows:

- 14,939 normalized local HPDB facts, with no source alerts.
- All 17 intended SID-qualified trunked Favorites Lists matched exact
  TrunkId/SysId identities.
- 134 validated HPE files were generated from 136 catalog entries.
- All 39 King County municipal lists, the Ames Lake home profile, the
  Eastside regional profile, and the comprehensive outdoor rollup were
  populated and location-tagged.
- All twelve band-oriented packs and UL00-UL03 Upper Lena profiles were
  generated; Upper Lena components carry the official NPS campsite location.
- FL30 is composed fail-closed from complete deep copies of FL04, FL05,
  FL06, and FL01. It preserves each component's verified hierarchy and GPS
  metadata without inventing a geographic boundary or radio fact. It should
  be treated as a full-component location-controlled rollup; users wanting a
  smaller scan cycle should review and avoid distant sites in Sentinel.
- FL45 and FL72 remain the only intentional on-site Discovery lists.
- Every generated HPE decoded and passed schema and semantic validation.
- The import-pack manifest, file set, and SHA-256 checksums passed validation.
- Current import-pack SHA-256: `8B258DD0186582C91F2BE228F4C25126603D6B07D75ACC70CB2F924C1BAD6E4B`.
- Clear/encrypted split pairs were distinct; every retained encrypted
  department was clearly marked and avoided.

Aggregate changes observed against the previous local Sentinel snapshot:

- FL09a gained 13 stable talkgroup records and retired one.
- FL09b retired one retained talkgroup record.
- FL10 gained two talkgroup records.
- FL21 gained five talkgroup records.
- FL25a gained one talkgroup record.
- FL50a/FL50b gained eight sites and 43 trunk-frequency records; their
  curated retained talkgroup sets also increased.
- FL58 gained 14 stable talkgroup records and retired one.
- Other target lists were structurally unchanged or changed only in
  non-identity metadata.

These counts are diagnostics only. They do not redistribute system names,
frequencies, talkgroup IDs, or other licensed HPDB content.

## Refresh from Sentinel

From the repository root in Windows PowerShell:

```powershell
.\.venv\Scripts\wasds150.exe --home .wasds150-home sources configure `
  --sentinel-hpdb-cfg "C:\ProgramData\Uniden\BCDx36HP_Sentinel\Database\hpdb.cfg"

.\.venv\Scripts\wasds150.exe --home .wasds150-home sources fetch sentinel_local

.\.venv\Scripts\wasds150.exe --home .wasds150-home sources update `
  --only sentinel_local --json |
  Set-Content -Encoding utf8 "$env:TEMP\wasds150-sentinel-preview.json"

.\.venv\Scripts\wasds150.exe --home .wasds150-home sources update `
  --only sentinel_local --apply

.\.venv\Scripts\wasds150.exe --home .wasds150-home preview
.\.venv\Scripts\wasds150.exe --home .wasds150-home generate `
  --out wasds150-output
```

Always review preview coverage and conflicts before `--apply`. Do not use
`--force` merely to suppress a conflict.

## Import into Sentinel

### One-operation local profile installation

Sentinel does not define a single HPE file that creates multiple Favorites
Lists. The dashboard therefore offers a direct, guarded workspace operation:

1. Close Sentinel completely.
2. Open the dashboard's **Export** tab.
3. Select the populated Favorites Lists to install.
4. Under **Bulk install selected lists into Sentinel**, confirm the detected
  BCDx36HP workspace and choose the target profile.
5. Choose a backup directory outside the Sentinel workspace.
6. Select **Plan selected bulk install**. Review every assigned slot, target
  HPD filename, replacement flag, and planned index write.
7. If the plan contains any `replacing: true` entries, explicitly enable
  replacement approval after verifying each one. Unindexed/orphan HPD files
  are treated as occupied and are never silently overwritten.
8. Type the displayed `IMPORT <profile>` confirmation phrase.
9. Select **Back up + install selected**. Execution is bound to the reviewed
  index and target-file fingerprint; any change after planning requires a
  new plan. A workspace-wide interprocess lock prevents overlapping installs.
  The tool creates one verified full
  workspace backup, writes all selected HPD files and both global/profile
  indexes, verifies every byte, and automatically restores the backup on a
  detected failure.
10. Reopen Sentinel and inspect representative lists before writing to the
  scanner.

This uses the format verified from a real Sentinel-created test list:

- `FavoriteLists\f_NNNNNN.hpd`: plain ASCII/CRLF Favorites List records,
  without the HPE-only trailing `File` signature;
- `FavoriteLists\f_list.cfg`: global Favorites List index;
- `Profile\<profile>\f_list.cfg`: profile membership/settings index.

Existing unselected entries and HPD files are preserved. Existing generated
entries reuse their slots, and their quick/startup key fields are retained.
The operation is backed up and recoverable, but removable-media or power loss
cannot be physically atomic; retain the backup until Sentinel and the scanner
have both been checked.

### Standard per-HPE import

1. Close any scanner write operation and back up both the current Sentinel
   profile and the scanner microSD card.
2. Extract `wasds150-output\sentinel-import-pack.zip` to a temporary folder.
3. In Sentinel, create or open a disposable test profile.
4. For each file in the extracted `hpe` directory, use Sentinel's
   **File > Import from hpe file (Favorites List)** command. Sentinel imports
   HPE files individually; the ZIP is a transport and integrity bundle, not
   a one-click Sentinel import format.
5. When Sentinel asks for a Favorites List name, retain the generated FL key
   and descriptive name so clear/encrypted pairs remain distinguishable.
6. Open **Edit Favorites List** and inspect representative systems before
   writing anything to the scanner:
   - every trunked list has sites, control/voice frequencies, departments,
     and talkgroups;
   - FL09a/b, FL20a/b, FL25a/b, and FL50a/b are distinct;
   - departments prefixed `[E]-ENCRYPTED` are set to Avoid;
   - **Monitor** and **Download** are enabled only for lists wanted on the
     scanner;
   - location control and site ranges suit the intended travel profile.
7. Save and close Sentinel, reopen the profile, and repeat a spot check. This
   catches import or persistence problems before a scanner write.
8. Connect the SDS150 by USB and select **Mass Storage** mode.
9. Use **Scanner > Write to Scanner**. Select the correct drive. Do not choose
   an erase option unless intentionally replacing all existing Favorites
   Lists and a verified backup is available.
10. Safely eject the scanner, reboot it, and confirm the expected Favorites
    Lists are enabled. Time a complete scan cycle and disable distant sites
    if the active profile scans too slowly.

### Reference validation

The generated set was checked against a real Sentinel-created HPD example.
All 134 generated HPE files passed container, schema, semantic, CRLF, header,
and signature validation. Every record tag shared with the example matched
Sentinel's observed field width. Direct-workspace HPD output removes only the
HPE interchange signature and preserves the validated record hierarchy.

Encrypted traffic cannot be decoded. Avoided encrypted departments are kept
only for change detection and database-drift review.

## Run the local dashboard

### Existing development environment

From the repository root:

```powershell
.\.venv\Scripts\wasds150.exe --home .wasds150-home ui --port 8765
```

The dashboard opens automatically. If it does not, use the loopback URL and
per-run token printed in the terminal. Stop it with **Ctrl+C**.

The equivalent Python-module command is:

```powershell
.\.venv\Scripts\python.exe -m wasds150 --home .wasds150-home ui --port 8765
```

Use the same `.wasds150-home` path for CLI and dashboard operations so both
see the same profile, merged local catalog, source configuration, history,
and cache.

### Fresh Python installation

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\wasds150.exe --home .wasds150-home init
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\wasds150.exe --home .wasds150-home ui --port 8765
```

The server binds to loopback and protects mutating API requests with a
per-run token. It is not intended to be exposed directly to a LAN or the
public Internet.
