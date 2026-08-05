# Sentinel Refresh, Import, and Dashboard Runbook

This runbook records the reusable procedure used to rebuild the personal
Washington SDS150 bundle from an updated local Uniden Sentinel HPDB. Licensed
HPDB records and generated HPE files remain local and are not committed.

## Latest verified local refresh

The August 2, 2026 Sentinel master database was read successfully on Windows:

- 14,939 normalized local HPDB facts, with no source alerts.
- All 17 intended SID-qualified trunked Favorites Lists matched exact
  TrunkId/SysId identities.
- 76 validated HPE files were generated.
- FL30 is composed fail-closed from complete deep copies of FL04, FL05,
  FL06, and FL01. It preserves each component's verified hierarchy and GPS
  metadata without inventing a geographic boundary or radio fact. It should
  be treated as a full-component location-controlled rollup; users wanting a
  smaller scan cycle should review and avoid distant sites in Sentinel.
- FL45 and FL72 remain the only intentional on-site Discovery lists.
- Every generated HPE decoded and passed schema and semantic validation.
- The import-pack manifest, file set, and SHA-256 checksums passed validation.
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
