# Washington SDS150 Favorites

A curated statewide radio programming catalog and generator. One unified,
source-cited database drives every radio: a Uniden SDS150 scanner (organized
for Sentinel, location control, GPS and quick keys), a TIDRADIO TD-H9
handheld, a Kenwood TH-D75A, and a Yaesu FTX-1.

The catalog covers all 39 Washington counties and includes:

- Police, fire, EMS, SAR, emergency management, and interoperability
- Washington State Patrol, WSDOT, DNR, wildfire, USFS, and NPS
- Washington mountain regions and backcountry communications
- Civil and military aviation, medevac, marine, ferries, and rail
- Amateur radio, GMRS/FRS, MURS, CB, utilities, business, and events
- The US amateur band plan, licence-class privileges, and scan ranges
- Encryption, digital-mode upgrade, and Discovery/Close Call guidance

**One database, many radios.** A *channel plan* selects rows from the catalog,
orders them into memory slots, and writes a programming file for one specific
radio — dropping anything that radio cannot use, with a stated reason, rather
than silently coercing it. Refresh a list at any time by re-exporting: the
catalog is the source of truth. See
[Radios and channel plans](#radios-and-channel-plans).

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
- [Band-oriented scanning](docs/band-scanning.md) - twelve ready-to-scan listening packs, matching Custom Search ranges, noise/data avoidance, and additional scenario guidance.
- [Antenna measurement results](antenna-results/README.md) - calibrated handheld and installed-vehicle comparisons, family/service coverage matrix, explicit gap analysis, recommendations, scorecards, offline interactive analysis, raw Touchstone data, and the preserved JYR8010 EFHW report.
- [Upper Lena Lake profile](docs/upper-lena-lake.md) - compact and comprehensive Hood Canal/Olympic wilderness, SAR, weather, public-safety, aviation, marine, amateur, and personal-radio profiles.
- [Puget Sound ham repeaters and nets](docs/puget-sound-ham.md) - current WWARA-coordinated repeaters, operator-published net channels/schedules, mode grouping, source hierarchy, and update workflow.
- [Radius-based lists and HF](docs/local-radius-lists.md) - building a list by distance from home rather than by county, why RepeaterBook could not be used, what the WWARA expiry date can and cannot tell you, and the HF nets and beacons worth tuning.
- [Data-source architecture](docs/data-sources.md) - source provenance, caching, update and merge behavior.
- [TD-H9 programming guide](docs/td-h9-programming.md) - complete hardware procedure, verified radio facts, cable troubleshooting, and the two failure modes that produce a silently wrong radio.
- [TH-D75A Ames Lake loadout](docs/th-d75-ames-lake.md) - verified capabilities, 50-mile analog/D-STAR and wideband-receive plan, native-image safety, installed software, hashes, hardware write, and read-back results.
- [Agent runbook](docs/agent-runbook.md) - copy-paste procedures for automating this repository, environment layout, API reference, and project invariants.
- [Lake Ozette profile](docs/ozette-lake.md) - Olympic Peninsula coastal trip profile: Clallam County, SAR/interop, tribal, marine, aviation, and amateur coverage.
- [Printable mounts and brackets](models/README.md) - parametric OpenSCAD visor mounts, Peak Design Capture bracket, and EFHW antenna enclosure, with print-ready 3MF/STL and the latch/fit reasoning behind each variant.
- [Parametric modelling method](docs/modelling-method.md) - measurement-first workflow, tolerance and clearance conventions, and the automated geometry checks each model must pass.
- [Peak Design capture bracket](docs/pd-capture-bracket.md) - the SDS150 bracket's dimensions, fastener options, and fit verification.
- [EFHW antenna enclosure](docs/efhw-enclosure.md) - a 128mm screw-lid cylinder for an end-fed half-wave transformer: how it sheds rain without a gasket, the open-topped cable exits, and why the thread is deliberately coarse.

## Radios and channel plans

| Radio | Role | Memories | Loaded now | Status |
|---|---|---:|---:|---|
| Uniden SDS150 | Trunk-tracking scanner, receive only | unlimited | 141 Favorites Lists | Verified |
| TIDRADIO TD-H9 | Analog handheld transceiver | 199 | 185 memories | Verified against hardware |
| Kenwood TH-D75A | Tri-band analog/D-STAR and wideband receiver | 1,000 + 1,500 DR | 538 memories + 21 DR repeaters | Verified, written and read back |
| Yaesu FTX-1 | HF/VHF/UHF transceiver | 999 | 960 statewide **or** 351 local memories | Profile from documentation, **unverified** |

The FTX-1 has two loadouts, chosen from the same dropdown. `ftx1-wa` is the
statewide inventory. `ftx1-local` is the working list: amateur repeaters within
60 miles of home whose coordination is current — 163 of Washington's 433 — plus
HF nets, calling frequencies, beacons and utility stations from 160 m to 6 m.
The radius is applied to each repeater's own coordinates, so the list follows
the home location rather than county lines.

Each radio's current configuration is inspectable in its **own shape**, because
they genuinely differ. The SDS150's configuration is hierarchical - Favorites
Lists containing systems, sites, departments and talkgroups - and is written as
one `.hpe` per list. The transceivers take a flat, ordered memory list where the
slot number is meaningful, because it is the order the radio scans in.
Flattening the scanner into a memory list would silently discard every trunked
talkgroup, so the tool does not offer to.

```bash
wasds150 loadout list              # one entry per radio
wasds150 loadout show sds150       # Favorites Lists, systems, talkgroups
wasds150 loadout show ftx1-wa      # numbered memory map
wasds150 loadout save h9-ozette    # snapshot the current configuration
wasds150 loadout diff h9-ozette    # what changed since that snapshot

wasds150 radios list               # capability profiles
wasds150 plan list                 # registered channel plans
wasds150 plan show h9-ozette       # resolved memory map, drops, warnings
wasds150 plan show thd75-ames-lake # 50-mile + wideband memory map
wasds150 plan export ftx1-wa --target ftx1-file --out radio-configs
wasds150 plan export ftx1-local --target ftx1-file --out radio-configs
wasds150 plan export thd75-ames-lake --target thd75-file --out radio-configs
```

The same thing is in the **Radios** tab of `wasds150 ui`: pick a radio from the
dropdown to see what is loaded, save a snapshot, ask what changed since the last
one, export a programming file, or program a connected TD-H9.

Redistributable ready-made outputs and the TH-D75 report are committed in
[`radio-configs/`](radio-configs/). Native `.d75` files are deliberately
ignored because they preserve operator settings from the attached radio.
Exporting writes the private working file there; pass `--copy-to` to also drop
it in the folder the programmer loads from.

**Only intended radio regions are written.** A radio file holds far more than
frequencies. FTX-1 exports start from a factory-reset structural baseline and
patch memory slots. TH-D75 exports start from an exact private read of that
radio and replace only ordinary memories, group names and, when imported by
MCP-D75, the native D-STAR region. APRS/MYCALL, GPS, Bluetooth, display, audio,
special memories and menu settings remain byte-identical to the backup.

**Per-channel settings are decoded, not guessed.** Operating mode, tone mode,
CTCSS, repeater shift and scan-skip are each written from the catalog, and each
was established by writing a probe file with one memory per setting, changing
that single column in the vendor programmer, and diffing the result. The field
map and the method are in [`radio-templates/`](radio-templates/README.md); the
probe tooling is `scripts/radios/make_ftx1_probe.py`. Columns the radio derives
rather than stores — Width, AGC, IPO, the Narrow flags — are inherited from the
vendor's own per-band defaults instead of invented.

TD-H9 hardware programming needs CHIRP, which is GPL-3 and therefore never
vendored. The TH-D75 uses Kenwood's official VCP driver and MCP-D75 for the
hardware transfer; a pinned GPL-2.0-or-later Rust library independently
validates the image offline. Full procedures are in the radio-specific guides.

Writing to a radio always backs it up first, always requires an explicit
`--execute`, and always reads the radio back to verify afterwards.

## Current coverage

| Measure | Current baseline |
|---|---:|
| Curated Favorites List entries | 141 |
| Statewide/core entries | 78 |
| King County municipal entries | 39 |
| Lists generated with no private input | 73 |
| Lists generated after current local Sentinel enrichment | 135 |
| Unique structured channel records after enrichment | 1,855 |
| Remaining local warnings | 2 |
| Washington counties represented | 39 |
| Registered radio profiles | 3 |
| Registered channel plans | 3 |

Four of the 141 entries are transceiver-oriented and carry fully cited
channel lists rather than scanner metadata: **OZ01** (Olympic Coast / Lake
Ozette, 141 channels), **HAM01** (US amateur band plan, 88 calling and
convention frequencies, reference only), **FTX01** (FTX-1 factory memory
import, 453 channels) and **HFNET01** (HF nets, beacons and utility stations,
54 channels, reference only).

`HAM01` and `HFNET01` are marked reference-only because most of their content
lies below the SDS150's 25 MHz floor. They are carried in the catalog anyway,
because the transceiver plans draw from them; generation projects away what the
scanner cannot hear and says how many channels it dropped.

The packaged no-private-input baseline leaves the trunked local rows pending.
After applying the current local Sentinel HPDB, all statewide trunk targets,
all 39 city lists, Ames Lake/Eastside profiles, twelve band packs, all four
Upper Lena profiles, FL30, and OUT01 are populated.
Only FL45/FL72 remain on-site Discovery scenarios with no stable published
channel set. No empty or guessed HPE is emitted.

## Repository privacy and local data

This repository is maintained as a **private GitHub repository**. Private
visibility is an access-control layer, not permission to redistribute licensed
Sentinel/RadioReference content. Local HPDB files, merged catalogs, generated
HPE files, scanner-card data, previews, backups, and import bundles remain
git-ignored and must stay on the authorized user's machine.

Commit only reusable source code, public intent/location metadata, synthetic
fixtures, tests, and documentation. Before every push, verify that `git status`
contains no `hpdb.cfg`, `s_*.hpd`, local catalog, generated HPE/HPD, Sentinel
workspace, scanner backup, or preview JSON artifacts.

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

The **Radios** tab shows every supported radio's capability profile and, for
the radio chosen in the dropdown, exactly what is loaded for it — in that
radio's own shape. The SDS150 appears as Favorites Lists with system,
department, channel and talkgroup counts; the TD-H9 and FTX-1 appear as
numbered memory maps with transmit setting, mode, power, tone and source
block, filterable and broken down per block. **Save snapshot** writes the
current configuration to disk and **What changed?** compares against the last
one, so a catalog refresh can be reviewed before it reaches a radio. The tab
also exports programming files, detects attached serial ports, and can back
up, dry run, or write a connected TD-H9. Writing requires typed confirmation,
backs the radio up first, and verifies the result afterwards. When the CHIRP
interpreter is absent the tab explains how to create it and still shows the
equivalent command line.

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
clickable. Ten palette-independent scenario layouts cover Sentinel Export,
dispatch, technical, mobile/GPS, unit identification, SDS150 telemetry,
discovery, trunk analysis, aviation/marine, and recording/alerts. Thirteen separate
color groupings range from basic and accessibility-focused to scenario-based,
row-banded, and fully granular colorful displays. Maximum-spectrum modes use
up to 30 distinct high-contrast Sentinel swatches per theme. Stable Item
Rainbow keeps the same meaning the same color across screens and templates.
Layout, theme, and grouping can each change without replacing the other two,
and templates avoid repeating any editable option within a screen.
Search Sentinel's exact 147 supported swatches grouped by hue and
brightness, reuse recent supported colors, and choose Sentinel-compatible
displayed elements with synchronized or per-view behavior.

Display XML uses Sentinel's required lowercase color tokens and is roundtrip
tested against the installed Sentinel importer. Reverse-rendered Func/soft-key
colors are translated to visual editor semantics automatically; duplicate-name
Avoid fields that Sentinel cannot independently import are clearly marked.

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
  NOAA Weather Radio, current NIFOG/WAFOG interoperability,
  FRS/GMRS/MURS/CB, marine VHF, common aviation/guard frequencies, and
  more — are parsed and populated automatically (see
  `wasds150.recipes.systems` / `wasds150.sources.static_channels` /
  `wasds150.sources.static_seeds`). Currently 73 of the 137 catalog rows
  are populated this way with zero configuration; most local city rows are
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

Hardware programming is the one exception, and it is deliberately kept outside
the package. CHIRP is GPL-3.0 and needs Python 3.10+, so it lives in a separate
interpreter that only `scripts/radios/` imports:

```bash
python -m venv .venv-chirp
.venv-chirp/bin/pip install git+https://github.com/kk7ds/chirp.git
python scripts/radios/fetch_chirp_tdh9_module.py
```

Neither `.venv-chirp/` nor the fetched driver module is committed.

The 3D models are a third, equally separate environment. They need OpenSCAD
plus a scientific stack for the geometry checks, none of which the package
uses:

```bash
python -m venv .venv-cad
.venv-cad/bin/pip install -r scripts/cad/requirements.txt
.venv-cad/bin/python scripts/cad/export_models.py    # regenerate every 3MF/STL
.venv-cad/bin/python scripts/cad/build_all.py        # verify everything, then export
```

`build_all.py` runs all 21 geometry checks in order and stops at the first
hard failure, so a broken model cannot overwrite good STLs. It goes quiet
for minutes at a time while CGAL works.

Project invariants that must not be broken — zero runtime dependencies, the
MIT/GPL boundary, never committing licensed data, reporting dropped channels
rather than coercing them — are listed in the
[agent runbook](docs/agent-runbook.md#invariants--do-not-break-these).

## Important limitations

RadioReference is community-maintained, and radio systems change regularly. Update Sentinel's master database and verify system sites, talkgroups, modes, and encryption before each major trip.

Encrypted traffic cannot be decoded by the SDS150. Temporary incident assignments, ski-area operations, event channels, and some commercial systems may be unpublished and require lawful on-site Discovery or Close Call monitoring.

This scanner is receive-only and is not a substitute for a satellite messenger, personal locator beacon, or authorized two-way radio in the backcountry.

**Transmitting is your responsibility.** Channel plans mark most blocks receive
only, and encode the power limits in 47 CFR Part 95 for GMRS and MURS. That is
a convenience, not legal advice or a compliance guarantee. Transmitting on
amateur frequencies requires an FCC licence with the relevant privileges; GMRS
requires a separate licence; public-safety, marine, aviation and business
channels require authorization you almost certainly do not have. Verify before
you key up.

The **Yaesu FTX-1 profile is unverified** — built from documentation, not
tested against hardware. The UI and `radios list` both flag it.

## Primary sources

- [RadioReference Washington database](https://www.radioreference.com/db/browse/stid/53)
- [Uniden SDS150](https://uniden.com/products/sds150)
- [Washington DNR radio operations](https://dnr.wa.gov/wildfire-resources/fighting-fire/fire-business-and-incident-management/dnr-radio-operations)
- [NOAA Weather Radio stations](https://www.weather.gov/nwr/stations?State=WA)
- [RepeaterBook Washington](https://www.repeaterbook.com/repeaters/index2.php?state_id=53)
