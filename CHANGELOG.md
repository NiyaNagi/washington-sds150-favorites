# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

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
  The focused editor offers all preset colors, generated in-between swatches,
  persistent recent-color memory, arbitrary text/background pickers, live
  contrast, reset controls, and synchronized or per-view application.
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
