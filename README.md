# Washington SDS150 Favorites

A curated statewide programming plan for the Uniden SDS150, organized for practical use with Sentinel, location control, GPS, and quick keys.

The catalog covers all 39 Washington counties and includes:

- Police, fire, EMS, SAR, emergency management, and interoperability
- Washington State Patrol, WSDOT, DNR, wildfire, USFS, and NPS
- Washington mountain regions and backcountry communications
- Civil and military aviation, medevac, marine, ferries, and rail
- Amateur radio, GMRS/FRS, MURS, CB, utilities, business, and events
- Encryption, digital-mode upgrade, and Discovery/Close Call guidance

## Files

- [Master favorites guide](washington-sds150-favorites-master.md) - 75 Favorites Lists with regions, systems, sites, categories, modes, monitorability, and sources.
- [Programming inventory](washington-sds150-favorites.csv) - machine-readable inventory for filtering, review, and future tooling.
- [Sentinel checklist](washington-sds150-programming-checklist.md) - build order, quick keys, GPS/location control, updates, testing, and backups.

## The `wasds150` tool

`src/` contains a standard-library-only Python 3.9+ CLI and local browser UI
that turns the catalog above into a working, importable programming
profile — with no code required to use it. See
[`docs/data-sources.md`](docs/data-sources.md) for the full source/update
model; this is the short version.

```bash
pip install -e .            # editable install; wasds150 = console entry point
wasds150 init                # seed a profile from the packaged baseline (78 Favorites Lists)
wasds150 preview              # what would be generated, with no files written
wasds150 generate --out out/ # csv + markdown + a Sentinel import .zip (hpe/ inside) + loose hpe/
wasds150 ui                   # the same workflow in a local browser tab
```

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
  `wasds150.sources.static_seeds`). Roughly 56 of the 78 baseline rows are
  populated this way with zero configuration.
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
