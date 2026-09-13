# radio-data

Everything a radio is programmed from, backed up to or read back into, in one
folder per radio. The code finds these folders through
[`src/wasds150/paths.py`](../src/wasds150/paths.py), and the step-by-step
guides in [`docs/guides/`](../docs/guides/README.md) use the same paths.

Most of this folder is **git-ignored**. Backups and read-backs carry settings
read from a specific radio, exports are regenerated from the catalog, and the
contact lists and licences are personal or licensed. Only these are tracked:
the READMEs, `ftx1/templates/`, `th-d75/reference/`, `shared/legacy-plans/` and
`at-d890uv/firmware/download.ps1`.

```
radio-data/
├── sds150/        Uniden SDS150 scanner
│   ├── exports/       hpe/ (one .hpe per Favorites List), favorites-overview.md,
│   │                  generate/ (the `wasds150 generate` output), archive/
│   └── backups/       sentinel-workspace/ (taken before every install), SD-card zips
├── td-h9/         TIDRADIO TD-H9
│   ├── exports/       td-h9-fleet.csv + report, archive/
│   └── backups/       radio-<label>-<timestamp>.img reads and -verify- read-backs
├── th-d75/        Kenwood TH-D75A
│   ├── exports/       th-d75-fleet.d75 + report, the MCP-saved and -final images, archive/
│   ├── backups/       MCP-D75 reads of the radio, dated
│   └── reference/     manuals/, dstar/ (repeater TSVs), images/ (sample .d75 files),
│                      current/ (the tracked operator image)
├── ftx1/          Yaesu FTX-1
│   ├── exports/       ftx1-fleet.FTX1 + report, archive/
│   ├── backups/       RT Systems reads of the radio, dated
│   ├── templates/     the factory-default and blank structural baselines
│   ├── source-files/  the original hand-built RT Systems files
│   └── probes/        field-decoding probe files (generated/ is what make_ftx1_probe writes)
├── at-d890uv/     Anytone AT-D890UV
│   ├── exports/       at-d890uv-fleet/ (the CPS import bundle) + report, archive/
│   ├── backups/       .rdt codeplugs: factory reads, saved imports, patched -full files
│   ├── readbacks/     CPS Export All folders, one per read-back
│   ├── probes/        scan-list probes and CPS import tests
│   └── firmware/      firmware 1.05, the NXDN overlay, the CPS and the options utility
├── id-52a/        Icom ID-52A
│   ├── exports/       id-52a-fleet/Csv/ (MemoryCh/ and RptList/) + report
│   └── backups/       CS-52 reads of the radio, dated
├── shared/
│   ├── checklists/    dated programming checklists (PROGRAM-YYYY-MM-DD.md)
│   ├── contacts/      radioid.net DMR and NXDN contact lists, for the Anytone
│   ├── licences/      FCC amateur and GMRS licence PDFs (never tracked)
│   └── legacy-plans/  the single-radio plans that came before the fleet plans
└── tools/
    └── nanovna-saver/ NanoVNA-Saver, for the antenna measurements in antenna-results/
```

## Naming

- New files are named `<radio>-<what>-<YYYY-MM-DD>[-HHMM].<ext>`, for example
  `at-d890uv-fleet-2026-09-12-1411-full.rdt` or
  `th-d75-with-channels-2026-09-11-1634.d75`.
- The current export always keeps the same name (`td-h9-fleet.csv`,
  `ftx1-fleet.FTX1`, and so on) and is overwritten by every export. Superseded
  exports that are worth keeping go in that radio's `exports/archive/`.
- The TD-H9 programmer names its own backups `<label>-<YYYYMMDD-HHMMSS>.img`.
  They are left as written.

## Where things used to be

This folder replaced several scattered folders on 2026-09-13:

| Was | Now |
|---|---|
| `wasds150-output/radios/` | `radio-data/<radio>/exports/` |
| `wasds150-output/` (the `generate` output) | `radio-data/sds150/exports/generate/` |
| `wasds150-output/PROGRAM-*.md` | `radio-data/shared/checklists/` |
| `radio-backups/` | `radio-data/<radio>/backups/` and `radio-data/at-d890uv/readbacks/` |
| `.wasds150-home/state/sdcard-backups/` | `radio-data/sds150/backups/` |
| `radio-configs/` | `radio-data/shared/legacy-plans/`, `radio-data/th-d75/reference/current/`, `radio-data/shared/contacts/`, `radio-data/ftx1/probes/generated/` |
| `radio-templates/` | `radio-data/ftx1/templates/` |
| `radio-tools/anytone-d890uv/` | `radio-data/at-d890uv/firmware/` |
| `thd75a programming details/` | `radio-data/th-d75/reference/` |
| `Z:\Texts\HAM\Radio Programming\` | copied into `ftx1/source-files/`, `ftx1/probes/`, `ftx1/exports/archive/` and `shared/licences/`; Z: itself is unchanged |
| `Z:\Texts\HAM\Antenna Analysis\` | already in `antenna-results/manual-testing/`; NanoVNA-Saver copied to `tools/` |

Exports are no longer copied to the Z: drive. Load every radio from its folder here.
