# Sentinel HPDB Completion Plan

This plan completes the Washington Favorites Lists after an updated local
Sentinel HomePatrol database is available. Until then, generation remains
fail-closed: locally verified conventional channels are emitted, while
lists that require authoritative trunked records are skipped with explicit
warnings rather than filled with guessed sites or talkgroups.

## Local baseline status

- 78 curated Favorites Lists are defined.
- 58 lists currently produce validated HPE files with no private input.
- 510 conventional channels are structured with explicit mode and service
  type metadata.
- Universal distress/calling channels receive conservative priority flags.
- Explicit carrier-only APRS/Winlink packet channels are retained for
  reference but avoided.
- FL42's explicitly unverified Pomeroy frequency is not emitted; its
  statewide mountain safety baseline remains available.
- The remaining 20 warnings comprise trunked-system dependencies,
  intentional Discovery lists, and the FL30 cross-list rollup.

## Before importing the HPDB

1. Update Sentinel's master database and confirm the SDS150 firmware and
   paid DMR/NXDN upgrades installed on the scanner.
2. Back up the Sentinel profile and scanner microSD card.
3. Record the Sentinel database date so generated manifests can identify
   their source snapshot.
4. Keep the generated conventional baseline. It now includes expanded
   statewide interop, DNR/NIFC wildfire, mountain safety, marine, Seattle
   Center/FSS, CB, utilities, event, news-air and NOAA channel sets.

## Configure and ingest

```bash
wasds150 sources configure \
  --sentinel-hpdb-cfg "/path/to/hpdb.cfg"
wasds150 sources update --apply
wasds150 preview
wasds150 generate --out out/
```

Use `--sentinel-mount "/path/to/card"` instead when pointing at a mounted
or copied SDS150 card. Configure exactly one of the two Sentinel paths.

Use the browser UI's **Advanced > Sources** workflow if preferred. Never
copy private RadioReference credentials into the repository.

## Systems to resolve first

| Priority | Favorites Lists | Required HPDB detail |
|---|---|---|
| P0 | FL04, FL05 | Complete WSP and WSDOT sites, control frequencies, regional talkgroups and service types |
| P0 | FL09a/b, FL10, FL11, FL12 | Metro public-safety sites and talkgroups; separate clear fire/EMS/interop from encrypted law groups |
| P0 | FL20a/b, FL21, FL25a/b | Eastern Washington trunked fire/EMS/law dispatch and encrypted tactical buckets |
| P1 | FL13, FL14 | Merge TCERN/Kitsap trunked data with the existing Mason/Jefferson conventional channels |
| P1 | FL15, FL50a/b, FL58 | Port/Boeing, JBLM and Sound Transit systems, including encrypted security groups |
| P2 | FL08 | JIWN reference-only system, permanently avoiding encrypted operational groups |

FL30 is a rollup, not an independent source system. Build it only after
FL01, FL04, FL05 and FL06 are complete. FL45, FL72 and most of FL74a are
intentional on-site Discovery scenarios and should not be treated as HPDB
failures.

## Merge and curation rules

1. Preserve HPDB record trees losslessly; do not flatten trunked systems.
2. Match systems by RadioReference/Sentinel identity, not display name.
3. Retain only sites useful to each list's travel region. Avoid distant
   sites to keep scan cycles short.
4. Put confirmed encrypted talkgroups in an `[E]-ENCRYPTED` department,
   set that department to Avoid, and retain it for change detection.
5. Separate dispatch, tactical, interoperability, transportation and
   public-works departments with accurate Sentinel service types.
6. Prefer HPDB modes, NACs, color codes, slots, LCNs and location data over
   static defaults. Never synthesize a missing control channel or TGID.
7. Review duplicate conventional channels introduced by regional rollups;
   duplication is acceptable only when it serves an intentional travel
   profile.

## Location and quick-key pass

After HPDB enrichment, apply location control from authoritative site and
department coordinates:

- No location gating: statewide SAR, NIFC/DNR, national interoperability,
  aviation guard, marine distress and NOAA.
- 35-60 mile range: county systems, forests, parks and regional WSDOT/WSP
  site groups.
- 15-25 mile range: municipal, venue, utility and local repeater groups.

Assign FLQKs using the ranges documented in
`washington-sds150-favorites-master.md`. Then assign system and department
quick keys only after the imported hierarchy is stable; HPDB updates can
otherwise invalidate hand-assigned positions.

## Acceptance gates

The HPDB completion is ready to publish only when:

- all intended trunked lists contain at least one site, control frequency
  and talkgroup;
- every encrypted group is clearly named and avoided;
- site coordinates and ranges pass semantic validation;
- no list exceeds scanner file/count limits;
- every HPE round-trips byte-for-byte and matches its source model;
- the Sentinel ZIP manifest contains all expected files and valid hashes;
- the missing-input warning count is reduced only for genuinely completed
  lists;
- a Sentinel import and scanner write are tested from a backup copy before
  replacing the active profile.

## Ongoing refresh

Repeat the update, preview, generate and validation workflow before major
trips and after significant Sentinel database changes. Review diffs for
new sites, changed control channels, renamed talkgroups and encryption
changes instead of accepting updates blindly.
