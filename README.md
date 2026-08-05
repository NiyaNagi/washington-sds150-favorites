# Washington SDS150 Favorites

A curated statewide programming plan and generator for the Uniden SDS150,
organized for practical use with Sentinel, location control, GPS and quick
keys.

The catalog covers all 39 Washington counties and includes:

- Police, fire, EMS, SAR, emergency management, and interoperability
- Washington State Patrol, WSDOT, DNR, wildfire, USFS, and NPS
- Washington mountain regions and backcountry communications
- Civil and military aviation, medevac, marine, ferries, and rail
- Amateur radio, GMRS/FRS, MURS, CB, utilities, business, and events
- Encryption, digital-mode upgrade, and Discovery/Close Call guidance

## Files

- [Changelog](CHANGELOG.md) - release history and user-visible changes.
- [Master favorites guide](washington-sds150-favorites-master.md) - 75 numbered slots represented by 78 generated entries where encrypted/clear variants are split.
- [Programming inventory](washington-sds150-favorites.csv) - machine-readable 78-entry statewide/core inventory; 42 public local-area intent rows are appended deterministically by the package.
- [Sentinel checklist](washington-sds150-programming-checklist.md) - build order, quick keys, GPS/location control, updates, testing, and backups.
- [Sentinel HPDB completion plan](docs/sentinel-completion-plan.md) - exact ingestion, merge, curation, location, quick-key, and acceptance steps once an updated local HPDB is available.
- [Cross-machine Sentinel handoff](docs/sentinel-machine-handoff.md) - complete context and Windows workflow for resuming on a Sentinel-equipped machine.
- [Sentinel reactivation prompt](prompts/continue-sentinel-enrichment.md) - copy-paste prompt for a new agent session.
- [Sentinel refresh/import/dashboard runbook](docs/sentinel-refresh-runbook.md) - repeatable Windows HPDB refresh, validated HPE import, scanner-write, and local dashboard instructions.
- [SDS100/SDS150 display palettes](docs/display-customizer.md) - coordinated high-contrast palettes, semantic color groups, all-mode previews, XML export, and Sentinel import instructions.
- [Ames Lake, King County, and outdoor lists](docs/ames-lake-king-county.md) - all 39 King County municipalities with Census location tags, Ames Lake profiles, reviewed local service curation, and the comprehensive outdoor safety rollup.
- [Data-source architecture](docs/data-sources.md) - source provenance, caching, update and merge behavior.

## Current coverage

| Measure | Current baseline |
|---|---:|
| Curated Favorites List entries | 120 |
| Statewide/core entries | 78 |
| King County municipal entries | 39 |
| Lists generated with no private input | 58 |
| Lists generated after current local Sentinel enrichment | 118 |
| Structured conventional channels | 510 |
| Remaining local warnings | 2 |
| Washington counties represented | 39 |

The packaged no-private-input baseline leaves the trunked local rows pending.
After applying the current local Sentinel HPDB, all statewide trunk targets,
all 39 city lists, Ames Lake/Eastside profiles, FL30, and OUT01 are populated.
Only FL45/FL72 remain on-site Discovery scenarios with no stable published
channel set. No empty or guessed HPE is emitted.

## Install and run

`src/` contains a standard-library-only Python 3.9+ CLI and local browser UI
that turns the catalog above into a working, importable programming
profile — with no code required to use it. See
[`docs/data-sources.md`](docs/data-sources.md) for the full source/update
model; this is the short version.

```bash
git clone https://github.com/NiyaNagi/washington-sds150-favorites.git
cd washington-sds150-favorites
python3 -m venv .venv
.venv/bin/pip install .
.venv/bin/wasds150 init
.venv/bin/wasds150 preview
.venv/bin/wasds150 generate --out out/
.venv/bin/wasds150 ui
```

On Windows, launch the same local dashboard from the repository root with:

```powershell
.\.venv\Scripts\wasds150.exe --home .wasds150-home ui --port 8765
```

See the [Sentinel refresh/import/dashboard runbook](docs/sentinel-refresh-runbook.md)
for the complete updated-database and device-import workflow.

The dashboard's **Catalog** tab uses lightweight summary rows. Expand any
row to load every available non-sensitive field on demand, including profile state,
provenance, systems, sites, trunk frequencies, departments, conventional
channels, talkgroups, geolocation, service metadata, priority, and avoids.

The **Export** tab also supports a guarded **Bulk install selected lists into
Sentinel** operation. Sentinel has no native multi-list HPE container, so the
tool writes all selected lists directly into a chosen local Sentinel profile
in one preflighted operation. It performs a dry-run plan first, requires
Sentinel to be closed, takes and verifies a full workspace backup, preserves
unselected lists and profile settings, and automatically rolls back detected
write failures.

The **Display** tab compares twelve coordinated palettes across all seven
scanner display modes on one page. Every palette uses consistent semantic
colors, reports contrast ratios, and downloads as validated Sentinel display
customizer XML. A full editor supports semantic group colors, synchronized
matching items, per-item/per-view text and background colors, whole-view
coloring, saved browser palettes, and JSON import/export. Preview fields are
clickable: choose preset and blended swatches, recent colors, arbitrary custom
colors, and Sentinel-compatible displayed elements with synchronized or
per-view behavior.

The generated `out/sentinel-import-pack.zip` is the bulk download. Its
`hpe/` directory contains every currently available Favorites List with
clear, stable names such as `FL01.hpe` and `FL75.hpe`. Sentinel imports HPE
files individually, but after import it writes all selected Favorites
Lists to the SDS150 in one scanner-write operation.

## Generation and installation

**End-to-end workflow: profile → generated Favorites Lists → install.**
`generate` (CLI or the UI's Export tab) writes one importable `.hpe` file
per enabled Favorites List that has structured system data — decoded and
schema-validated before being written, never a silently-empty file. Two
independent ways a row gets that structured data, and both can apply to
the same catalog:

- **No private input needed, works out of the box**: national/public
  frequencies already spelled out in this repository's own catalog text —
  NOAA Weather Radio, national interoperability (NPSPAC ICALL/ITAC),
  FRS/GMRS/MURS/CB, marine VHF, common aviation/guard frequencies, and
  more — are parsed and populated automatically (see
  `wasds150.recipes.systems` / `wasds150.sources.static_channels` /
  `wasds150.sources.static_seeds`). Currently 58 of the 120 baseline rows
  are populated this way with zero configuration; the local city rows are
  deliberately HPDB-dependent. Static channels also
  receive conservative modulation, service-type, and distress/calling
  priority metadata; location and trunk-specific metadata are never guessed.
- **Local Sentinel HPDB or RadioReference Premium data**: for trunked
  systems (WSP, PSERN, SREC, ...), point `wasds150 sources configure` at
  your own already-updated Sentinel database (`--sentinel-mount`/
  `--sentinel-hpdb-cfg`) or a RadioReference Premium export
  (`--rr-export-path`), then run `wasds150 sources update --apply`. This
  data is read-only, strictly local, and never committed or
  redistributed by this project (see `NOTICE.md`) — only *your own*
  generated bundle ever sees it.

Once a Favorites List has structured systems, `wasds150 install write
--slug <FLnn> <card mount>` (or the UI's Advanced → SD Card Installer
panel) writes it straight to an SDS150 card: dry-run by default, a
mandatory full backup before any real write, an explicit typed
confirmation phrase, a strict write/delete allow-list, and `fsync`'d
writes. A row with no structured systems yet reports a clear, actionable
warning instead of an empty/fake file — build it the traditional way via
Sentinel's own "Append to Favorites List" workflow (see the
[Sentinel checklist](washington-sds150-programming-checklist.md)) in the
meantime, or pass `--systems <path-to-System-JSON>` as an advanced/debug
alternative to `--slug`.

Every generation path is fail-closed and uses the same validation gates:
catalog/profile integrity, channel and talkgroup semantics, SDS150
frequency coverage, mode/tone/service-type syntax, record hierarchy,
BCDx36HP dialect/signature, deterministic container round trips,
model-to-record parity, file/count limits, and ZIP manifest checksums.
CLI and web exports are built in a staging directory and published as a
rollback-capable transaction, so failed validation cannot leave a partial
or stale HPE set. Direct SD writes run the same document validation and
verify the mandatory backup before changing the card.

## Updating with Sentinel data

When an updated Sentinel database is available:

```bash
wasds150 sources configure \
  --sentinel-hpdb-cfg "/path/to/hpdb.cfg"
wasds150 sources update --apply
wasds150 preview
wasds150 generate --out out/
```

Use `--sentinel-mount "/path/to/card"` instead when pointing at an SDS150
card root. The two Sentinel path options are alternatives.

Follow the [Sentinel HPDB completion plan](docs/sentinel-completion-plan.md)
for the system-by-system priority order, merge rules, location-control
pass, encrypted-talkgroup handling and release gates.

## Development

The runtime has no third-party dependencies. Install the development extra
and run the suite with:

```bash
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```

## Important limitations

RadioReference is community-maintained, and radio systems change regularly. Update Sentinel's master database and verify system sites, talkgroups, modes, and encryption before each major trip.

Encrypted traffic cannot be decoded by the SDS150. Temporary incident assignments, ski-area operations, event channels, and some commercial systems may be unpublished and require lawful on-site Discovery or Close Call monitoring.

This scanner is receive-only and is not a substitute for a satellite messenger, personal locator beacon, or authorized two-way radio in the backcountry.

## Primary sources

- [RadioReference Washington database](https://www.radioreference.com/db/browse/stid/53)
- [Uniden SDS150](https://uniden.com/products/sds150)
- [Washington DNR radio operations](https://dnr.wa.gov/wildfire-resources/fighting-fire/fire-business-and-incident-management/dnr-radio-operations)
- [NOAA Weather Radio stations](https://www.weather.gov/nwr/stations?State=WA)
- [RepeaterBook Washington](https://www.repeaterbook.com/repeaters/index2.php?state_id=53)
