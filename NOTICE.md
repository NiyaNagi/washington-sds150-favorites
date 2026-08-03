# Third-Party Research & Fixture Attribution (HPE/HPD engine)

This file documents the external sources consulted while implementing
`wasds150.hpe` (the Uniden `.hpe`/`.hpd` container/record engine, including
the HPDB on-card RadioReference database parser in `wasds150.hpe.hpdb`),
the three-way merge engine, and the experimental SD-card installer, per the
project's "facts-only" sourcing discipline: **no code was copied from any
GPL-licensed or unlicensed project below.** Every module in `src/wasds150`
is an original Python 3.9 implementation written from the documented facts
cited here (byte offsets, field meanings, safety rules), independently
re-derived rather than translated or adapted line-by-line from any
reference implementation.

## Ground truth

- Uniden **File Specification V1.03/V2.00** and **Remote Command
  Specification V2.00** PDFs (manufacturer-published, `info.uniden.com`).

## Facts-only references (no code reused)

| Source | License | What was learned from it (facts only) |
|---|---|---|
| `sq5bpf/hpe_open` | GPL-2.0 | Confirms `.hpe` = `gzip(text)` XORed byte-for-byte with the constant `0x0C` (self-inverse). This specific fact (a single constant and a standard algorithm) is treated as a discovered, documented fact about a file format, not as copyrightable expression; `wasds150.hpe.codec` is an independent ~100-line implementation written from this fact, not a translation of `hpe_open.c`. |
| `TheKayThatWasOrange/uniden-hpe-util` | WTFPL (public domain-equivalent) | Independent confirmation of the XOR/gzip mechanism. |
| `FuzzyGophers/platypus` | GPL-2.0-only | Hardware-validated field/arity tables (`Conventional`, `C-Group`, `C-Freq`, `Trunk`, `Site`, `T-Group`, `TGID`, `T-Freq`, `DQKs_Status`, `BandPlan_P25/Mot`, `Rectangle`, `F-List`), on-card layout (`BCDx36HP/favorites_lists/`, `HPDB/`, `profile.cfg`, `app_data.cfg`, `discvery.cfg`), and SD-card write-safety rules (delete `app_data.cfg` after writes, `fsync` before eject, preserve unrelated `f_list.cfg` fields, omit `BandPlan_P25` unless needed, preserve `T-Freq` LCN rather than zeroing it). Also the HPDB dialect: `hpdb.cfg`'s `StateInfo`/`CountyInfo`/`LM` schema, the `s_<state>.hpd` system-segmentation algorithm, the identity-column (`Key=Value` id/parent-id) convention, the `AreaState`/`AreaCounty` area-tagging rule (including the "owner id is not always a county id" quirk), and the HPDB->Favorites dialect conversion rules (blank id columns, drop area tags, synthesize only `DQKs_Status`). Consulted as documentation only, per platypus's own "facts, not expression" sourcing discipline (its `CREDITS.md`); no Rust source was copied or transliterated. |
| `swannman/sds100` | No LICENSE file found (treated as all-rights-reserved; facts only) | Independent cross-check of the same field/arity tables and the `T-Freq` 8-vs-9-field version quirk; general design pattern of "generic record tree, preserve what you don't understand" (a well-known, unoriginal architectural idea, not copied code). |
| `achard/rr-uniden` | No LICENSE file found (facts only) | Cross-check of the 37-code service-type table. |

## Test fixtures

Four fixtures are referenced by `wasds150.hpe`'s optional, network-gated
tests. **None are vendored into this repository or version control.**
`scripts/fetch_hpe_fixtures.py` downloads them on demand into
`.fixture-cache/` (git-ignored); the corresponding tests
(`tests/test_hpe_external_fixtures.py`, `tests/test_hpe_hpdb_external_fixtures.py`)
skip cleanly if the cache is empty and network access is unavailable. This
project's own, fully-original synthetic fixtures
(`tests/fixtures/wasds150_synthetic_bcdx36hp.hpd`,
`tests/fixtures/wasds150_synthetic_hpdb.cfg`,
`tests/fixtures/wasds150_synthetic_s_000053.hpd` — all written from scratch
against the documented arity tables above, no external content) are the
primary, always-available golden fixtures for CI.

| Fixture | Source | License | Why it's useful | Why not vendored |
|---|---|---|---|---|
| `f_example.hpd` / `f_list.cfg` (synthetic) | `FuzzyGophers/platypus`, commit `5abb42b54595186ea217ecdf904a19a081be7b08`, `samples/synthetic/` | GPL-2.0-only | Structurally faithful to the real `BCDx36HP`/`1.00` SDS150 dialect (correct field widths/offsets), entirely fictional data ("Example State" StateId 90) — useful as an independent cross-check of this project's own schema table. | GPL-2.0 is copyleft; to keep `wasds150` independently licensed, external GPL-2.0 files are fetched on demand for optional validation rather than committed to this repository. |
| `hpdb.cfg` / `s_000090.hpd` (synthetic) | `FuzzyGophers/platypus`, commit `5abb42b54595186ea217ecdf904a19a081be7b08`, `samples/synthetic/` | GPL-2.0-only | Structurally faithful synthetic HPDB state master + county index (`hpdb.cfg`) and a 4-system state file (`s_000090.hpd`) exercising conventional/trunked systems, multi-county coverage, and the `AgencyId`-is-not-a-`CountyId` quirk on purpose — used to independently validate `wasds150.hpe.hpdb`'s schema, segmentation, and dialect-conversion logic. | Same reason as above. |
| `2026_Nascar_Season.hpe` | `jim-edwards/NascarScanner`, commit `f5ae6c5854cdfa1b04fe076fbf748f16ad0cdd6a`, `Uniden HomePatrol Sentinel/` | GPL-2.0 (repo-wide) | Real (non-synthetic), real-world `.hpe` container bytes — validates the XOR/gzip *framing* independently of this project's own fixtures. Note: legacy `HomePatrol-1`/`2.04` dialect, not `BCDx36HP`/`1.00` — used for container/round-trip checks only, not SDS150 column-offset validation. | Same reason as above. |

Run `python scripts/fetch_hpe_fixtures.py` to populate `.fixture-cache/`
before running the optional external-fixture tests; see that script's
docstring for details and attribution recorded alongside each download.

## Online source adapters (`wasds150.sources`) — data licensing notes

Every online adapter's module docstring documents exactly which live
endpoint was inspected while implementing it and any facts that differed
from the original research brief once independently verified. Summary of
sourcing/redistribution posture per source:

| Source | Data ownership | Redistribution posture |
|---|---|---|
| FCC ULS, FAA NASR, NOAA NWR | US federal government work (public domain) | Freely ingestible/redistributable; cached locally only, never committed to this repository. |
| USCG NAVCEN, AMSAT, WA EMD/SIEC, WA DNR, NIFC | Government/nonprofit publication | Cited by source URL; cached locally only, never committed. |
| WWARA | Coordinator-compiled database; `copyright.txt` restricts wholesale redistribution of the compiled file but its own `readme` explicitly endorses use "for programming radios" | This project derives only per-repeater facts for the user's own generated catalog from a locally cached copy; the compiled database itself is never committed or republished. |
| IACC | Coordinator-published repeater table; no bulk-export terms published, same posture applied as WWARA out of caution | Same as WWARA: per-repeater facts only, compiled table never committed/republished. |
| Sentinel HPDB (`sentinel_local`) | RadioReference's own licensed, on-card compiled database | Read-only, user-local only (see `wasds150.sources.sentinel_local`); never bundled, cached-to-share, or committed by this project under any circumstance. |
| RadioReference Premium (`radioreference_premium`) | RadioReference Premium subscription data | Only ever reads a file the *user* has already exported from their own account under their own subscription's terms; this project never scrapes RR's public pages or implements/calls RR's SOAP API without independently verified documentation (see that module's docstring). |

`tests/fixtures/sources/*` contain only small, hand-trimmed samples (a
handful of rows/records) built to match each source's real, independently
verified field layout — never a full compiled database — used solely to
exercise this project's own parsing code offline; none are redistributions
of any coordinator's or agency's actual production dataset.

