# Cross-Machine Sentinel Enrichment Handoff

> **Completed refresh:** This handoff was executed against Sentinel master
> database date August 2, 2026. The expanded verified result now produces
> 118 HPE files from 120 entries, including all 39 King County cities,
> Ames Lake/Eastside profiles, FL30, and OUT01; only FL45/FL72
> remain intentionally unresolved Discovery lists. See
> [Sentinel Refresh, Import, and Dashboard Runbook](sentinel-refresh-runbook.md)
> for the repeatable current workflow, validation record, device import, and
> dashboard instructions.

This document contains the context needed to resume the project on a
machine with Uniden Sentinel installed. The immediate goal is to read that
machine's current local Sentinel HomePatrol database, fill the remaining
trunked-system gaps, and produce a complete user-local set of validated HPE
files ready for Sentinel import.

The copy-paste agent prompt is in
`prompts/continue-sentinel-enrichment.md`.

Start from the latest `main` branch. The last completed release-documentation
commit before this handoff was `6bdc86e`.

## Original pre-expansion project state

| Measure | State before Sentinel enrichment |
|---|---:|
| Curated Favorites List entries | 78 |
| Locally generated HPE files | 58 |
| Structured conventional channels | 510 |
| Missing-input warnings | 20 |
| Automated tests | 562 passing |
| Package version | 0.1.0 |

The generator, CLI, browser UI, update pipeline, HPE codec, HPDB parser,
transactional publisher and guarded SD-card installer are implemented.
Generation is fail-closed and does not publish invalid or partial output.

The locally generated baseline already covers statewide interoperability,
DNR/NIFC wildfire, mountain safety, aviation, marine, rail, amateur,
GMRS/FRS, MURS/CB, business, utilities, events, news aviation and NOAA
Weather Radio. Do not replace those verified conventional channels with
flattened or guessed HPDB data.

## Remaining gaps

Seventeen Favorites Lists need authoritative trunked-system record trees
from Sentinel:

- FL04 — Washington State Patrol
- FL05 — WSDOT P25
- FL08 — Justice Integrated Wireless Network
- FL09a / FL09b — King County PSERN clear services / encrypted law
- FL10 — Snohomish County Sno911
- FL11 — Pierce County SS911/PSRS
- FL12 — Clark/Skamania CRESA
- FL15 — Boeing and Port of Seattle P25
- FL20a / FL20b — Spokane SREC clear dispatch / encrypted tactical
- FL21 — Benton/Franklin Tri-Cities
- FL25a / FL25b — Grant County clear fire/EMS / encrypted law
- FL50a / FL50b — JBLM support / command-security
- FL58 — Sound Transit/Link operations

In the original 78-entry handoff, the other three warnings were:

- FL30 is a rollup assembled only after FL01/FL04/FL05/FL06 are complete.
- FL45 ski-area operations remain on-site Discovery because stable public
  frequencies are unavailable.
- FL72 schools/malls/stadiums remains venue-specific Discovery.

That historical phase produced 75 files, then 76 after FL30. The current
expanded acceptance target is 118 generated HPE files from 120 entries:
the statewide/core lists, FL30, all 39 King County cities, Ames Lake and
Eastside profiles, and OUT01 must be populated, leaving only FL45/FL72 as
true Discovery warnings.

## Non-negotiable data rules

1. Sentinel HPDB and RadioReference data are licensed, user-local inputs.
2. Never commit `hpdb.cfg`, `s_*.hpd`, copied `BCDx36HP/HPDB` directories,
   raw source facts, merged local catalogs, or HPE files derived from the
   local HPDB.
3. Generated Sentinel bundles stay on the user's machine for personal use.
4. Only code, tests, synthetic fixtures and documentation may be pushed.
5. Preserve complete HPDB record trees. Never flatten trunked systems into
   conventional frequency lists.
6. Never invent a site, control frequency, TGID, LCN, NAC, color code,
   slot, location, range or encryption state.
7. Confirmed encrypted talkgroups remain present for change detection but
   belong in clearly named avoided departments.
8. Do not use `sources update --force` until every reported merge conflict
   has been reviewed.

The repository `.gitignore` contains additional safeguards, but always
inspect `git status` before committing.

## Recommended Windows setup

In PowerShell:

```powershell
git clone https://github.com/NiyaNagi/washington-sds150-favorites.git
cd washington-sds150-favorites
git pull --ff-only origin main

py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\wasds150.exe --home .wasds150-home init
.\.venv\Scripts\python.exe -m pytest -q
```

Using `--home .wasds150-home` keeps profile, merged catalog, cache, logs
and history together in a git-ignored directory. Use the same `--home`
argument for every command in this handoff.

## Obtain the updated Sentinel database

1. Open Sentinel.
2. Run **Update > Update Master HPDB**.
3. Record Sentinel's displayed database date.
4. Locate `hpdb.cfg` and its sibling `s_*.hpd` files.

A common Windows location is:

```text
C:\ProgramData\Uniden\BCDx36HP_Sentinel\Database\hpdb.cfg
```

Verify the actual path on that machine rather than assuming it. An equally
safe alternative is to write the updated database to an SDS150/spare card
and point the tool at the card root containing:

```text
<drive>\BCDx36HP\HPDB\hpdb.cfg
```

Do not copy either database into the repository.

## Configure exactly one Sentinel path

Direct `hpdb.cfg` path:

```powershell
.\.venv\Scripts\wasds150.exe --home .wasds150-home sources configure `
  --sentinel-hpdb-cfg "C:\ProgramData\Uniden\BCDx36HP_Sentinel\Database\hpdb.cfg"
```

Or scanner/card root:

```powershell
.\.venv\Scripts\wasds150.exe --home .wasds150-home sources configure `
  --sentinel-mount "E:\"
```

These are alternatives. Do not pass both.

## Read-only preflight

Confirm the local source can read systems without applying changes:

```powershell
.\.venv\Scripts\wasds150.exe --home .wasds150-home sources fetch sentinel_local
.\.venv\Scripts\wasds150.exe --home .wasds150-home sources update `
  --only sentinel_local --json |
  Out-File -Encoding utf8 "$env:TEMP\wasds150-sentinel-preview.json"
```

The preview JSON may contain licensed system names and metadata. Keep it
outside the repository and delete it after the work is complete.

Useful read-only diagnostics:

```powershell
.\.venv\Scripts\wasds150.exe hpe hpdb-inspect `
  "C:\ProgramData\Uniden\BCDx36HP_Sentinel\Database\hpdb.cfg" --json

.\.venv\Scripts\wasds150.exe hpe hpdb-inspect `
  "C:\ProgramData\Uniden\BCDx36HP_Sentinel\Database\s_000053.hpd" --json
```

Use `hpe hpdb-extract` only for temporary local diagnosis. Its output is
licensed user-local data and must not be committed.

## Enrichment workflow

1. Review the source outcome and fact count.
2. Review recipe coverage for each of the 17 target lists.
3. Diagnose unmatched systems using stable Sentinel/RadioReference IDs,
   exact system names and county coverage.
4. If matching code must change, add deterministic rules and synthetic
   regression tests. Do not hard-code licensed talkgroups or control
   channels into repository fixtures.
5. Preview again until the intended target list coverage is correct and
   merge conflicts are understood.
6. Apply without force:

```powershell
.\.venv\Scripts\wasds150.exe --home .wasds150-home sources update `
  --only sentinel_local --apply
```

7. Generate into the ignored output directory:

```powershell
.\.venv\Scripts\wasds150.exe --home .wasds150-home preview
.\.venv\Scripts\wasds150.exe --home .wasds150-home generate `
  --out wasds150-output
```

The final bulk artifact is:

```text
wasds150-output\sentinel-import-pack.zip
```

Its `hpe\` directory contains the individual Sentinel-importable files.

## Curation requirements

- Prefer exact HPDB identity matching over display-name matching.
- Keep only geographically relevant sites for each regional list so scan
  cycles remain practical.
- Split clear operational services from confirmed encrypted departments.
- Preserve existing local conventional systems when a Favorites List is a
  mixed trunked/conventional list, especially FL13 and FL14.
- Use HPDB-provided service types, modes, locations and ranges.
- Retain Sentinel names when they are operationally clear; shorten only
  when necessary for scanner display usability.
- Build FL30 only after its component statewide systems are complete.
- Defer FLQK/SQK/DQK assignment until system/site/department hierarchy is
  stable.

See `docs/sentinel-completion-plan.md` for detailed system priorities,
location ranges and acceptance rules.

## Acceptance and validation

Do not stop when the command merely succeeds. Confirm:

1. All intended target lists contain sites, trunk frequencies and TGIDs.
2. The warning count falls only for genuinely populated lists.
3. Clear/encrypted splits match the catalog intent.
4. Every generated HPE passes automatic semantic and parity validation.
5. The bundle manifest and all embedded checksums validate.
6. No stale HPE remains from an earlier run.
7. The complete test suite passes:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

8. A clean wheel reproduces the same generated file count.
9. `git status --short` contains no HPDB, HPE, merged catalog, preview JSON
   or other licensed/generated data.
10. Import the HPE files into a disposable Sentinel profile first. Save,
    reopen, inspect several representative systems, and only then write to
    a backed-up scanner card.

## Key implementation files

- `src/wasds150/sources/sentinel_local.py` — read-only HPDB adapter
- `src/wasds150/hpe/hpdb.py` — HPDB parsing and system slicing
- `src/wasds150/recipes/default_recipes.py` — target matching rules
- `src/wasds150/recipes/engine.py` — coverage and enrichment
- `src/wasds150/recipes/systems.py` — HPDB fact-to-model conversion
- `src/wasds150/update/pipeline.py` — source, enrichment and merge pipeline
- `src/wasds150/merge/three_way.py` — local override preservation
- `src/wasds150/hpe/validation.py` — semantic validation
- `src/wasds150/bundle/generate_outputs.py` — transactional publication
- `tests/test_hpe_hpdb.py` — HPDB parser/conversion tests
- `tests/test_recipes.py` — recipe matching tests
- `tests/test_generation_validation.py` — exhaustive artifact validation

## Repository changes allowed during the Sentinel session

If real HPDB data exposes matching or conversion bugs, fix the generic
implementation and add synthetic regression tests. Update this handoff and
the changelog when behavior changes. Commit and push only those reusable
changes. Keep the completed personal Sentinel bundle local.
