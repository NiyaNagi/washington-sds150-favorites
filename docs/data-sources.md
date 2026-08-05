# Data sources and update policy

`wasds150` separates public authoritative facts from licensed, user-local
scanner data. Every imported fact retains its source, retrieval time, and
confidence so updates can be reviewed before they alter a profile.

## Source precedence

1. Operator-published federal or state data
2. FCC or FAA licensing and facility records
3. Amateur-radio coordinator records
4. A user-supplied Sentinel HPDB snapshot
5. Optional credentialed RadioReference programming data
6. Community references used only when no primary source exists

User presentation choices such as names, notes, quick keys and enabled
state are maintained as local overrides. Upstream facts such as frequencies,
talkgroups, sites, modes and encryption status can update without erasing
those choices.

## Automatically refreshable public sources

| Source | Adapter | Coverage | Typical refresh | Usage |
|---|---|---|---:|---|
| FCC ULS bulk files | `fcc_uls` | Non-federal licenses and frequencies (`HD`/`EN`/`LO`/`FR` bulk `.dat` tables) | Weekly | Business, public safety, GMRS, marine, aviation ground and amateur licensing |
| FAA NASR | `faa_nasr` | Airports and communications (`NAV_BASE.csv`, `COM.csv`) | 28 days | Airports, CTAF, NAVAIDs, RCO/FSS facility citations |
| NOAA Weather Radio | `noaa_nwr` | NWR transmitters and SAME county coverage | Annual/on change | Weather frequencies and county alert codes |
| USCG NAVCEN | `uscg_navcen` | Marine VHF channel plan + NOAA weather channels | On change | Marine calling, safety and operational channels |
| WA EMD/SIEC/SCIP | `wa_emd` | State interoperability plan documents (change detection only) | Irregular | Flags a new/changed SAR, mutual aid, CEMNET, OSCCR or SCIP document for manual review |
| WA DNR | `wa_dnr` | Wildfire radio guide documents (change detection only) | Fire season/annual | Flags a new/changed DNR repeater/command/air-ops guide for manual review |
| NIFC/NIICD | `nifc` | National incident radio cache guide documents (change detection only) | Annual | Flags a new/changed wildfire command/tactical/air-guard guide for manual review |
| WWARA | `wwara` | Western Washington repeater coordination database | Nightly | Coordinated amateur repeaters (frequency, tone, sponsor) |
| IACC | `iacc` | Inland Amateur Communications Council repeater table (WA + N. Idaho, filtered to WA) | On change | Coordinated amateur repeaters east of the Cascades |
| AMSAT/ARISS | `amsat` | Satellite and ISS operating status catalog | Volatile | Active amateur satellite modes |
| NWAC/SPART | `nwac` | Backcountry radio channel graphic (change detection only) | Seasonal | Flags when the published backcountry channel graphic changes, for manual re-review |

Government records (FCC, FAA, NOAA, USCG, WA state agencies, NIFC) are
ingested as factual data with source attribution. WWARA and IACC are
coordinator-compiled databases: this project derives per-repeater facts for
the user's own generated catalog from a locally cached copy, but never
commits or republishes either compiled database itself (see `NOTICE.md`).

**WA EMD/SIEC, WA DNR, and NIFC publish their data only as PDFs with no
pure-stdlib text-extraction library in scope for this project** — rather
than attempt fragile PDF parsing, those three adapters do link-discovery
and change-detection only (new/changed/unchanged document alerts), leaving
the actual fact extraction to a human reviewing the flagged document. NWAC
similarly publishes its backcountry radio channel plan only as an
infographic image with no parseable table or text on the page at all, so
it is change-detection-only for the same reason.

All fetches go through a shared sqlite-backed, content-addressed HTTP cache
(`wasds150.cache`) with TTL freshness, `ETag`/`Last-Modified` conditional
GET, a hard per-response size limit, and per-host rate limiting. Downloaded
source files/responses are cached locally under the config home directory
and are never committed. An explicit offline mode serves only what is
already cached (or fails clearly) so a run never silently blocks on the
network.

## Running an update

`wasds150 sources list` shows every known adapter (name, kind, available).
`wasds150 sources status` shows cache freshness per source.
`wasds150 sources fetch <name>` fetches+normalizes a single source without
merging. `wasds150 sources update [--only a,b] [--offline] [--apply]`
fetches every configured source, classifies each baseline Favorites List's
coverage (see "Default recipes and coverage" below), and runs the same
three-way merge used by `wasds150 merge` — preview by default, `--apply` to
persist. The equivalent routes/UI panel are under the web UI's Advanced tab.
After `--apply`, run `wasds150 generate` (or the UI's Export tab) to turn
the merged, now-more-populated catalog into CSV/Markdown/per-list `.hpe`
output — see "Structured systems and generated `.hpe` output" below for
exactly how a matched fact becomes a real system rather than only a
provenance citation.

## Default recipes and coverage

The existing catalog's per-row fields (`system_or_category`,
`sites_or_coverage`, `departments_or_channels`, notes, ...) are hand-authored
free-text summaries, not a machine-editable channel list — no adapter's
facts are complete enough to safely regenerate that *prose* automatically,
so `wasds150.recipes` never rewrites those 14 CSV columns. Instead, one
recipe per baseline row (derived automatically from that row's own
existing text — see `wasds150.recipes.default_recipes`) classifies
**coverage**, matching on SID/TrunkId, county, system name (a conservative
substring fallback for rows with no SID), and/or keyword-derived source
ids:

- **full** — either the row needs no local data and a matching public-source
  fact was found, or it needs local Sentinel HPDB/RadioReference Premium
  data and a matching local fact was found.
- **partial** — some public-source facts matched but full trunked
  site/talkgroup detail (if required) is still missing.
- **none** — nothing matched.

Matched facts are attached to the row as additional provenance entries
(source, URL, retrieval time, confidence) — additive and inert to the merge
engine (never a *fact-field*, i.e. CSV column, change) — so running an
update with **no** local HPDB/RadioReference input reproduces the shipped
78-row catalog's CSV fields and content hash exactly. Matched facts are
**also** converted into a real, populated `FavoritesList.systems` entry
(see the next section) — this is additive/structural, not a rewrite of the
free-text fields, and likewise never changes the content hash (`systems`
is deliberately excluded from `FavoritesList.content_hash()`). Supplying a
local HPDB export or RR Premium data lets the Sentinel-dependent trunked
rows report full coverage with `confidence="verified"` provenance and a
real per-list `.hpe` once matched by RadioReference system ID.

## Structured systems and generated `.hpe` output

`FavoritesList.systems` starts empty for every baseline row loaded from
raw CSV text (populating it from free-text prose directly would be lossy
and unverifiable — see `wasds150.models.catalog`'s module docstring). Three
independent, additive ways it gets populated (see
`wasds150.recipes.systems` for the full picture; a row can end up with
systems from more than one):

1. **Static free text + seed (Tier C — no setup, no network, no local
   input at all)**: `wasds150.sources.static_channels` parses each row's
   own already-checked-in `departments_or_channels` text for explicit,
   literal frequencies (never a guess — a hyphen-joined range like
   `"866.5125-868.0125"` is deliberately *not* expanded, since
   interpolating the channels in between would be fabrication).
   `wasds150.sources.static_seeds` adds small, hand-curated, cited fixed
   channel plans where prose alone is insufficient, including NPSPAC,
   FRS/GMRS, CB, marine VHF, Seattle Center/FSS and the shared mountain
   safety baseline. Every seed is gated by row-specific anchors so it
   cannot apply to an unrelated entry that reuses a key. This tier runs
   automatically on every
   `generate`/`preview`, and is baked into the packaged baseline snapshot
   too (see `wasds150.catalog.baseline`) — no configuration needed.
2. **Matched public-source facts (Tier B)**: once `wasds150 sources
   update --apply` is run, a matched NOAA/USCG/FCC ULS/FAA NASR fact (or a
   user-supplied RadioReference Premium import) — each already carrying
   its own explicit frequency — becomes a channel in the row's systems.
3. **Matched local Sentinel HPDB record tree (Tier A — richest)**: a
   matched `sentinel_local` fact carries its system's entire
   `Conventional`/`Trunk` record tree (site/department/channel/talkgroup
   detail, real RadioReference ids preserved as `System.id` etc. — see
   `wasds150.hpe.hpdb.system_slice_to_system`), losslessly converted
   rather than just cited.

`wasds150 generate` (CLI, UI Export tab, or the `sentinel-import-pack.zip`
bundle) then writes one importable `.hpe` per enabled Favorites List with
1+ populated systems — decoded and schema-validated before being
finalized, with a deterministic, sanitized filename
(`<favorite_key>.hpe`). A row with no systems yet reports a clear,
actionable warning (what it needs — usually a local HPDB/RR match) instead
of a silently-empty or missing file. `wasds150 install write --slug <key>`
(or the UI's SD Card Installer) then writes that Favorites List straight
to a card, preserving every existing safety control (dry-run, mandatory
backup, typed confirmation, write allow-list, `fsync`, rollback) — raw,
hand-authored Systems JSON via `--systems` remains available as an
advanced/debug path.

## User-local sources

### Sentinel HPDB

The scanner or Sentinel installation contains a licensed database under
`BCDx36HP/HPDB`. `wasds150.sources.sentinel_local` reads this database
locally (via `wasds150.hpe.hpdb`) to extract systems, sites, departments,
channels, talkgroups, locations, and stable RadioReference record IDs.
Raw HPDB files and extracted bulk database snapshots must not be committed
or redistributed; this adapter never touches the network.

Sentinel remains the easiest way to obtain a complete current database:

1. Update Sentinel's master database.
2. Write the updated database to the scanner or an SD card.
3. Run `wasds150 sources configure --sentinel-mount <card mount point>`
   (or `--sentinel-hpdb-cfg <path to hpdb.cfg>` if you only copied the
   `HPDB` folder).
4. Run `wasds150 sources update` to preview, then `--apply` to merge.

### RadioReference

Public RadioReference pages may be opened for manual verification and cited
by URL. The project does not bulk-scrape or mirror them, and does not call
RadioReference's SOAP "Premium/API" service without independently verifying
its request/response contract (not done in this project to date — see
`wasds150.sources.radioreference_premium`'s module docstring). Attempting to
configure that live API today raises a precise, actionable error rather
than guessing at an unverified contract.

What *is* supported: importing a CSV or XML export the user has already
lawfully downloaded from their own RadioReference Premium account, via
`wasds150 sources configure --rr-export-path <file>`. Column/element names
are matched by a best-effort alias table (not independently byte-verified
against a real export, since none was legally obtainable without an active
subscription) — every recognized fact is flagged for review before trusting
it in a generated bundle. Non-secret identifiers (username, app key) may
also be recorded via `--rr-username`/`--rr-app-key` for a future verified
SOAP client; a password is deliberately never persisted to disk by this
project. Credentials are never logged (see `wasds150.logging_setup`'s
redaction filter) and downloaded/imported data stays local, excluded from
any generated public/shareable artifact.

### RepeaterBook

RepeaterBook bulk exports are not mirrored (`wasds150.sources.repeaterbook`
remains an unimplemented placeholder — out of scope for this phase). The
application may retain links or import a file that the user has lawfully
exported for personal use in a future phase. Coordinator data such as WWARA
is preferred where available.


## Information that cannot be refreshed automatically

- Encrypted voice content
- Unpublished incident ICS-205 assignments
- Restricted DNR cooperators' plans
- NPS law-enforcement or tactical assignments not publicly released
- Ski patrol, venue and temporary event channels without a current public
  license or operator publication
- Discovery/Close Call observations that have not been confirmed

These remain review prompts or user-authored local entries rather than being
silently treated as authoritative.

## Conflict handling

When sources disagree, the updater:

1. Prefers the newest operator-issued document.
2. Prefers the licensee or coordinator over an aggregator.
3. Preserves the disagreement in provenance.
4. Requires review when two authoritative sources change the same fact
   differently.
5. Never removes a user-created list or channel solely because it disappears
   from an upstream source.
