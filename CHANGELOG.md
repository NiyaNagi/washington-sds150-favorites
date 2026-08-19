# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- Added per-radio loadouts. Every supported radio now has an inspectable saved
  configuration reachable from one dropdown, each rendered in its own native
  shape: the SDS150 as Favorites Lists with systems, sites and departments;
  the TD-H9 and FTX-1 as ordered memory channels. Snapshots can be saved and
  compared, so a refresh shows exactly what changed.
- Added `ftx1-wa`, a 959-channel Washington plan for the Yaesu FTX-1 covering
  amateur repeaters and simplex, GMRS/FRS/MURS, marine, aviation, NOAA,
  public-safety interop, and Winlink/APRS data channels.
- Added a native `.FTX1` export target, so the FTX-1 memory file is generated
  from the catalog rather than hand-merged in the vendor programmer. Data
  channels are programmed but flagged skip-scan.
- Added `wasds150 loadout list|show|save|diff` for the same operations from
  the terminal.
- Added parametric 3D-printable hardware: SDS150 visor mounts in four latch
  variants, a Peak Design Capture bracket in three fastener styles, and an
  EFHW antenna enclosure. OpenSCAD sources ship with print-ready 3MF/STL and
  the automated geometry checks each model must pass.
- Added a factory-reset FTX-1 baseline in `radio-templates/`, so the blank
  export template can be regenerated from a known state rather than from
  whatever happened to be on a radio.

- Added a final GOWENIC-module 40m EFHW package with a fresh 1.8-148 MHz,
  40,001-point OSL calibration, full-span reconnect verification, final
  counterpoise-installed sweep, all incremental tuning runs, band scorecards,
  SWR/impedance/return-loss/Smith plots, build and tuning visuals, an offline
  interactive report, reproduction instructions, and an LLM handoff prompt.
- Added the installed Taurus triband vehicle antenna with a separate BNC-plane
  calibration baseline, three-pass averaged service zooms, raw complex S11
  measurements, context-aware comparisons, an all-antenna coverage matrix, and
  generated full-window gap analysis.
- Added a reproducible calibrated scanner-antenna report package covering 20
  configurations and 20 receive-service windows, with authoritative averaged
  zooms, per-family analysis, practical recommendations, machine-readable
  scorecards, and a self-contained offline comparison.
- Added multi-radio support. One unified catalog now drives the Uniden SDS150
  scanner, a TIDRADIO TD-H9 handheld, and a Yaesu FTX-1, through radio
  capability profiles (`wasds150.radios`) and ordered channel plans
  (`wasds150.plans`). Channels a radio cannot use are dropped with a stated
  reason rather than silently coerced.
- Added a **Radios** tab to the browser UI: capability profiles, the full
  resolved memory map with filtering and per-block breakdown, programming-file
  export, serial port detection, and guarded backup/dry-run/write against a
  connected radio. Writing requires typed confirmation, backs the radio up
  first, and verifies the result.
- Added JSON API endpoints `/api/v1/radios`, `/api/v1/plans`,
  `/api/v1/plans/{id}`, `/api/v1/plans/{id}/export`,
  `/api/v1/programmer/status` and `/api/v1/programmer/run`.
- Added `wasds150 radios list` and the `wasds150 plan list|show|export`
  command group.
- Added OZ01, a Lake Ozette / Olympic Coast profile with 141 cited channels
  across twelve departments; HAM01, the US amateur band plan with 88 calling
  and convention frequencies (reference only, never projected onto a radio);
  and FTX01, a 453-channel FTX-1 factory memory import.
- Added the US amateur band plan module: 14 bands, per-licence-class transmit
  privileges per 47 CFR 97.301, ARRL mode segments, and 47 programmable scan
  ranges.
- Added a CHIRP Generic CSV export target for the TD-H9, and full read/write
  support for the Yaesu `.FTX1` memory file format (round-trip byte-identical).
- Added `scripts/radios/program_tdh9.py`: reads and backs up the radio before
  any write, dry runs by default, requires `--execute`, verifies channel by
  channel afterwards, and supports `--restore` from a saved image.
- Added the [TD-H9 programming guide](docs/td-h9-programming.md) and
  [agent runbook](docs/agent-runbook.md), documenting verified radio facts,
  counterfeit-Prolific cable recovery, and the two failure modes that produce
  a silently mis-programmed radio.

- Added a calibrated JYR8010 EFHW antenna-results package with supported-band
  SWR zooms, impedance and return-loss plots, a Smith chart, usable-bandwidth
  thresholds, an offline interactive report, summary tables, point data, full
  Touchstone source, calibration metadata, and reproducible generation tooling.
- Added PSHAM01, a comprehensive Puget Sound amateur repeater/net monitor. It
  always includes ten operator-published net channels and expands locally from
  WWARA's current nightly coordination extract into region/band/mode departments.
- Added mode-aware WWARA normalization for FM/NFM, P25 NAC, DMR color code, and
  unsupported D-Star/Fusion-only carriers; unsupported digital departments are
  retained but avoided.
- Added sourced Puget repeater/net documentation covering PSRG, Seattle ACS,
  Mike & Key, Mason, Island, Snoqualmie Valley, Tacoma, Kitsap, Whatcom, Skagit,
  PNW VHF Society, WWARA, RepeaterBook and RadioReference research.

- Added twelve band-oriented Favorites Lists for civil air, military air,
  amateur VHF/UHF, marine, rail, personal/itinerant, public-safety interop,
  weather/SAR, federal wildland, medical, transportation/utility, and
  business/event listening.
- Added UL00-UL03 Upper Lena Lake profiles using the official Olympic National
  Park campsite coordinate. The compact static profile covers Olympic
  park/forest, Mason/Jefferson public safety, SAR, wildfire, NOAA Weather,
  aviation, Hood Canal marine, Mason amateur, national calling and FRS/GMRS;
  broader profiles add regional P25 and all verified outdoor components.
- Added a sourced band-scanning guide with SDS150 Custom Search ranges,
  modulation guidance, scan-cycle strategy, data-carrier avoidance, and
  recommendations for location/time-dependent discovery scenarios.
- Updated FL02 from obsolete pre-rebanding ICALL/ITAC/STATEOPS assignments to
  current NIFOG 2.02 VCALL/VTAC, UCALL/UTAC, 7CALL/7TAC, 8CALL/8TAC and WAFOG
  1.10 STATEOPS receive/output frequencies.

- Added a self-contained cross-machine Sentinel enrichment handoff and a
  copy-paste reactivation prompt for completing trunked Favorites Lists on
  a Sentinel-equipped Windows machine.
- Added repository ignore safeguards for user-local HPDB files and
  generated HPE/import bundles.
- Added a Windows Sentinel refresh, HPE import, scanner-write, and local
  dashboard runbook, including the exact repeatable preview/apply/generate
  workflow and fail-safe device verification steps.
- Added lazy, accessible expansion for every dashboard Catalog item. Full
  on-demand detail includes every serialized catalog field, profile state,
  provenance, systems, sites, trunk frequencies, departments, channels,
  talkgroups, geolocation, service metadata, priority, and avoids. Large
  collections render in bounded batches.
- Added fail-closed rollup composition for catalog rows that explicitly
  declare reusable component lists. FL30 now deep-copies complete
  FL04/FL05/FL06/FL01 systems without flattening records or inventing a
  geographic boundary.
- Added guarded bulk installation of selected generated Favorites Lists into
  a local BCDx36HP Sentinel profile. The dashboard discovers profiles, plans
  deterministic slots, preserves existing global/profile index entries,
  writes all selected plain HPD files in one backed-up operation, verifies
  every output, and automatically restores the full workspace after a
  detected transaction failure.
- Added validation against a real Sentinel-created Favorites List workspace:
  all generated HPEs match observed shared record widths and the direct HPD
  writer emits Sentinel's plain ASCII/CRLF form without the HPE-only trailing
  signature.
- Added a Display Customizer dashboard tab with all seven scanner modes shown
  on one preview page, four coordinated semantic palettes, per-color contrast
  ratios, and validated Sentinel XML downloads.
- Added twelve coordinated presets: Night Ops, Daylight High Contrast,
  Colorblind Dark, Low-Light Amber, Oceanic, Forest Watch, Cyber Neon, Solar
  Dark, Solar Light, Monochrome Ice, Purple Dusk, and Slate Professional.
  System, department/site, channel/TGID, metadata, status, alert, and
  active-icon colors keep the same meaning across every mode.
- Added full palette customization: semantic group pickers, synchronized
  matching-item colors across all views, per-item/per-view text and background
  pickers, whole-view color application, live effective contrast warnings,
  reset controls, browser-saved named palettes, and JSON import/export.
- Made every field in every visual preview clickable and keyboard-accessible.
  The focused editor offers Sentinel's exact 147 supported display swatches
  grouped by hue and ordered by brightness, name/family/hex search, persistent
  supported-color memory, compact text/background target cards, live contrast,
  reset controls, and synchronized or per-view application.
- Redesigned the display item editor as a bounded desktop dialog and full-height
  mobile sheet with sticky actions, selected-swatch feedback, touch-sized
  controls, reliable keyboard focus, and no horizontal overflow.
- Replaced approximate display previews with canonical per-screen layouts from
  the Sentinel export. All 40 Simple, 50 Detail, and 45 special-mode XML items
  render exactly once by index, duplicate item names remain distinct, and the
  erroneous preview-only `Func` text/background inversion was removed.
- Added six palette-independent layout starting points: Sentinel Export,
  Dispatch Essentials, Technical Diagnostics, Mobile & GPS, Unit
  Identification, and SDS150 Telemetry. Scenario templates fill every editable
  slot, survive theme changes, remain fully customizable, and reset to template
  defaults.
- Replaced inferred display-option allowlists with Sentinel's exact Huge,
  Large, Small, and Icon tables. This unlocks supported blank fields in Search,
  Weather, and Tone Out and adds SDS150 battery, temperature, USB, filter,
  location, unit-name, RF, and decoding data points.
- Made semantic colors follow selected data rather than fixed slot history, so
  template-selected frequency/TGID, system, site, diagnostics, status, alert,
  and active indicators inherit the matching group from any color theme.
- Added Discovery & Close Call, Trunk Network Analysis, Aviation & Marine, and
  Recording & Alerts layouts, expanding palette-independent starting points
  from six to ten.
- Added ten independent color grouping choices spanning basic semantic,
  hierarchy-focused, full-spectrum granular, colorful row bands, top/bottom
  contrast, alternating rows, technical heatmap, activity/alerts, scenario,
  and accessibility uses.
- Full Spectrum Granular assigns every visible field to a related functional
  color family, eliminating neutral white fields in colorful themes. Row-based
  groupings can color top, middle, detail, icon, and soft-key areas distinctly.
- Preserved layout and grouping through theme changes, preserved theme and
  layout through grouping changes, and included grouping selection in saved
  palettes, JSON portability, previews, validated XML, and reset behavior.
- Expanded colorful choices with Maximum Spectrum Rows and Rainbow Data Matrix.
  Full Spectrum Granular now uses 18 distinct, saturated, Sentinel-supported
  colors instead of reusing seven semantic colors; every generated spectrum
  maintains at least 4.5:1 contrast against its theme background.
- Added automatic per-screen deduplication for Huge/Large template data. When a
  hierarchy field already shows Frequency, TGID, Site Name, System ID, or
  another value, secondary slots receive a different supported data point.
- Extended deduplication to Small and Icon slots. All ten templates now contain
  zero repeated editable options within each of their seven screens; top-row
  Bluetooth/GPS/recording/priority states are no longer duplicated below.
- Added Stable Item Rainbow with a 30-color high-contrast theme spectrum.
  Meaning-based color slots keep Frequency, TGID, system/site identity, signal,
  power, controls, alerts, and other matching items consistent across every
  screen and layout while different meanings receive different colors.
- Fixed Sentinel silently retaining old colors because generated HPDB color
  tokens were uppercase. Display XML now uses Sentinel's required lowercase
  values and canonical `Name`/`Option`/`Text`/`Back` attribute order.
- Added a real x86 Sentinel parser roundtrip integration test that verifies all
  seven screens, options, and importable colors survive import/re-export.
- Restored authoritative reverse rendering for Func and Soft1/2/3 while making
  editor Text/Background controls visual: values are translated to XML fields
  automatically rather than appearing swapped after import.
- Identified Sentinel's duplicate-name parser limitation: only the first Avoid
  on Simple/Detail screens imports color. The eight affected department/channel
  Avoid fields are now marked with dashed borders and explanatory warnings.
- Added Sentinel-compatible displayed-item selection for editable option and
  icon fields. Selection choices are constrained by field type, can synchronize
  across matching fields in all modes, update previews immediately, and are
  validated before custom XML export.
- Added the original Sentinel display export as a checked-in structural
  reference plus a sourced display guide covering official item constraints,
  palette rationale, preview workflow, and Sentinel import steps.
- Added one location-controlled Favorites List for every incorporated King
  County city/town, plus Ames Lake Home and Eastside Regional profiles. Public
  Census Gazetteer centers/ranges drive department location tags; exact radio
  records remain user-local and are resolved by stable Sentinel identities.
- Added conservative municipal curation for city services, NORCOM/ValleyCom
  fire and EMS, King County emergency/interop, hospitals, transit, and reviewed
  sheriff/police references. Law groups are retained in clearly marked avoided
  encrypted departments; unmatched records are excluded.
- Added OUT01, a fail-closed comprehensive outdoor safety rollup spanning SAR,
  mutual aid, WSP/WSDOT, DNR/NIFC, mountain/park/forest profiles, aviation,
  marine/ferries/ports, amateur/ARES/simplex, personal radio, hospitals,
  roadside support, and NOAA Weather.

### Fixed

- Fixed the FTX-1 export zeroing the radio's settings. A `.FTX1` holds CW
  messages, GPS setup, display data and the HOME channels past the memory
  array; the format model divided the whole file by the record size, minting
  roughly 800 phantom records out of that area, which the template builder
  then cleared. The file still loaded with correct memories, so nothing
  looked wrong. Exports now leave every non-memory byte identical, asserted
  by a test.
- Fixed CHIRP power levels being silently downgraded to Low on upload. The
  driver maps power with `list.index()`, which compares by object identity, so
  a level parsed from CSV never matched and fell back to index 0. The exported
  file and the dry run both looked correct; only reading the radio back
  revealed it.
- Fixed GMRS channels being programmed out of order. GMRS main and interstitial
  frequencies interleave within the band, so sorting by frequency produced
  15, 1, 16, 2, 17, 3. Added digit-aware `SORT_NATURAL` ordering.
- Fixed a patched upload path that dropped CHIRP's per-block acknowledgement
  check, causing a write to report success while changing nothing.
- Clarified that `--sentinel-hpdb-cfg` and `--sentinel-mount` are
  alternative source configurations rather than options to pass together.
- Made generated ZIP, manifest, backup, rollback and installer paths use
  portable forward-slash names on Windows.
- Made local HPDB enrichment require exact, type-aware TrunkId/SysId
  matches, including multiple SIDs and SIDs present only in source URLs,
  instead of absorbing unrelated systems through county/name fallbacks.
- Added fail-closed guards for Discovery-only and aggregate rollup rows so
  a coincidental local match cannot incorrectly mark them complete.
- Correctly parsed Sentinel master-HPDB eight-field trunk-frequency records
  while retaining Favorites/HPE nine-field compatibility.
- Accepted Sentinel's valid `ALL`, DCS, and color-code metadata forms and
  valid multi-site systems with sites that do not repeat talkgroup trees.
- Curated the documented clear/encrypted split pairs from public intent
  categories; encrypted-side departments are clearly marked and avoided,
  and unmatched talkgroups are not assigned an invented encryption state.

### Verified

- Reconstructed the personal local catalog against Sentinel master database
  date August 2, 2026: 14,939 normalized HPDB facts, zero source alerts,
  exact identity coverage for all 17 intended trunked targets, initially 75
  generated HPE files, and FL30/FL45/FL72 initially unresolved.
- Decoded and semantically validated every generated HPE; validated the
  import-pack file set, manifest, and SHA-256 checksums; confirmed all
  clear/encrypted split pairs differ and every retained encrypted department
  is avoided.
- Compared stable record identities with the previous local snapshot. The
  refreshed source added or retired records in FL09a/b, FL10, FL21,
  FL25a, FL50a/b, and FL58 while preserving the expected system hierarchy.
- Revalidated FL30, all local city profiles, and OUT01 and generated 118 HPE
  files from 120 entries. FL45 and FL72 remain intentionally unfilled because
  no authoritative stable
  channel data exists outside lawful on-site Discovery.

### Security

- Added a bounded catalog-summary API for the dashboard while preserving the
  existing full catalog API contract. Complete metadata is fetched one item
  at a time, rendered with DOM `textContent` rather than catalog `innerHTML`,
  and excludes source credentials, private profile notes, raw HPDB records,
  cache data, and local paths.
- Added strict Sentinel workspace/profile path checks, symlink rejection,
  mandatory backups outside the modified workspace, typed confirmation,
  duplicate-selection/slot validation, post-write byte verification, and
  automatic rollback for detected bulk-install failures.
- Bound execution to a reviewed plan fingerprint covering both indexes,
  generated payloads, and every destination's pre-write state. Added one
  workspace-wide interprocess lock, explicit replacement approval, and
  preservation of unindexed/orphan HPD files.
- Validate every display download for exact Sentinel root/screen/item shape,
  RGB syntax, template parity, and a minimum 4.5:1 text/background contrast.

## 0.1.0 - 2026-08-03

### Added

- A curated Washington catalog with 78 generated Favorites List entries
  covering all 39 counties, statewide interoperability, public safety,
  SAR, wildfire, mountain travel, aviation, military, marine, rail,
  amateur radio, GMRS/FRS, MURS, CB, utilities, business and events.
- A dependency-free Python 3.9+ CLI and loopback-only browser UI for
  profile editing, previewing, generation, source updates, history,
  rollback, validation and scanner-card installation.
- Deterministic BCDx36HP HPE encoding and decoding, Sentinel HPDB parsing,
  per-list HPE export and a bulk Sentinel import ZIP with CSV, Markdown,
  instructions, checksums and a content manifest.
- Automatic no-private-input generation for 58 Favorites Lists containing
  510 structured conventional channels.
- Fixed public channel plans and locally curated data for NPSPAC/STATEOPS,
  DNR and NIFC wildfire, mountain safety, marine VHF, Seattle Center/FSS,
  all 40 CB channels, FRS/GMRS, itinerant business, utilities, recurring
  events, news aviation and 17 primary Washington-serving NOAA Weather
  Radio transmitters.
- Conservative automatic channel metadata for modulation mode, Sentinel
  service type, universal distress/calling priority and carrier-only
  APRS/Winlink avoids.
- Read-only source adapters and update workflows for local Sentinel HPDB,
  RadioReference Premium exports, NOAA, FAA NASR, FCC ULS, USCG, AMSAT,
  NWAC, Washington DNR/EMD, WWARA and other documented sources.
- Three-way profile merging that preserves local presentation choices,
  reports conflicts and supports snapshot history and rollback.
- An experimental guarded SD-card installer with dry-run defaults,
  mandatory verified backups, explicit confirmation and post-write
  verification.
- A Sentinel HPDB completion plan describing the remaining trunked-system,
  location-control, quick-key and encrypted-talkgroup curation work.
- A comprehensive automated suite covering CLI, UI, generation, HPE/HPDB,
  updates, merges, manifests and scanner-card safety.

### Changed

- Generation is transactional across CLI and browser workflows: requested
  artifacts are staged and validated before publication, stale HPE files
  are removed, unrelated files are preserved and failed publication rolls
  back previous outputs.
- Catalog/profile persistence now fails closed on structural problems while
  retaining reserved quick-key guidance as an advisory warning.
- Generated filenames are portable across Windows, macOS and Linux,
  including case-insensitive collision handling and Windows reserved-name
  protection.
- Discovery-only and Sentinel-dependent lists remain explicit warnings
  instead of producing empty or fabricated scanner files.
- The packaged catalog now excludes the explicitly unverified FL42
  Pomeroy frequency while retaining its verified statewide mountain safety
  channels.

### Fixed

- Corrected BCDx36HP tone serialization to emit CTCSS as `TONE=Cnnn.n`,
  DCS as `Dnnn` and supported NAC values in the expected Sentinel syntax.
- Removed the duplicate FL65 FRS/GMRS channel and completed the non-linear
  FCC CB channel ordering.
- Fixed generation behavior for oversized individual lists, the scanner
  list-count limit, web preview status codes and invalid source/catalog
  persistence.
- Prevented stale or partial output sets after validation or publication
  failures.

### Security

- Added semantic validation for scanner frequency coverage, modes, tones,
  service types, hierarchy, geolocation, names, file limits, deterministic
  container round trips and exact model-to-record parity.
- Added ZIP path traversal checks, complete manifest-set validation,
  SHA-256 verification and validation of every embedded HPE file.
- Hardened scanner-card writes with strict path allow-lists, symlink
  rejection, temporary-file replacement, `fsync`, mandatory backup
  verification and read-back checks for both HPE and `f_list.cfg` data.
- Protected mutating browser API calls with a per-run token and loopback
  binding.
