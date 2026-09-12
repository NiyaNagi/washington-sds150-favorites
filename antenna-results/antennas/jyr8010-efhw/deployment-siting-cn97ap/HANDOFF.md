# Handoff — CN97ap EFHW siting study, 2026-09-12

For a fresh session picking up this study. Read this, then `AGENT_GUIDE.md`. Everything
below is either committed in this directory or stated here explicitly as not yet done.

---

## Where the study stands

Head of the study as of this handoff: commit `e3896ee` on `main`. **`main` is 22 commits
ahead of `origin/main`** — nothing from this study has been pushed. Don't push without
asking.

The antenna is a **JYR8010-150W, 39.6 m (130 ft) EFHW, 1:64 transformer** — an 80 m band
antenna. Feed/transformer point is fixed at the NE corner of the house,
47°38'02.61"N 121°59'47.73"W. **The operator currently has the feed at 10 ft.**

`tools/compare_options.py` scores 34 deployments across 5 bands and 25 DX regions and
ranks them on a 40+20+15 m aggregate. The live recommendations:

| Key | What | 3-band | Cells | Worst | Build effort |
|---|---|---|---|---|---|
| **RB-POST20** | Apex tree at 50 ft, then one 20 ft PVC post in the operator's staked garden strip, 90.9 ft @ 101°M | −0.71 dBi | 46–47/75 | −23.1 | **1 rope throw** + a post |
| F10-A | Bent flat-top, feed 10 ft, apex 50 ft, far support 50 ft, end 30 ft | −0.46 dBi | 47/75 | −26.2 | 1 throw + 2 more attachments |
| A | Same as F10-A with feed at 24 ft | −0.16 dBi | 49/75 | −25.4 | same |
| BASE | Operator's *original* plan: feed 10 ft, apex tree 35 ft (52.5 ft @ 82°T), end 10 ft toward 143°T | −2.84 dBi | 35/75 | −26.2 | 1 throw |

Two published artifacts (private, owned by the operator):

- Field plan — https://claude.ai/code/artifact/1128955c-5f0e-44c7-82a9-a08a9f9d2fa9
  (local source was in the prior session's scratchpad and is **gone**; to update it,
  `Artifact action:"read"` that URL first and edit what comes back)
- Deployment guide — https://claude.ai/code/artifact/0a8562b0-04ee-473f-9732-3a079305d96b
  (regenerate with `python tools/build_deployment_guide.py <out.html>`, then publish to
  that URL)

---

## The GPX task — DONE 2026-09-12 (kept below for the record)

Scored as **`CURRENT`**: rank **29 of 35**, −3.70 dBi, 24/75, worst −58.9 — below BASE
(35/75). The operator confirmed the walk started at the high end and the wire is straight.
Results in README.md → "What is up now", SESSION-LOG Phase 13. Two figures in the notes below
were wrong and are corrected there as **error 16**: the taut-wire end height is ~60 ft, not
43.6, and the 8-point start-dwell mean is 0.5 m *past* the south line. Canopy along the path is
4–5%, which exposed **error 15** ("no open-ground route exists" was a scan artefact).

The operator paced off **the antenna they actually have up right now** with a Garmin watch
and asked:

> the feedpoint is the same height i gave you previously and the end point is about 45 ft
> off the ground where the track stops. can you calculate where this fits into the rest of
> the options and tell me how it compares? compare it to my previous deployment

The track is committed-adjacent but **untracked**:
`antenna-results/antennas/jyr8010-efhw/50ft sloper antenna deployment.gpx`
(SHA-256 `0E4A0F4F…0A56`, identical to the chat upload). Do not commit it without asking.

### What the prior session already extracted (not yet in any tool or doc)

23 trackpoints, 2026-09-07 03:45–03:47 UTC. In ENU metres from the surveyed feed, using
`site_geometry.to_enu`:

| | ENU | From surveyed feed |
|---|---|---|
| Track **start** (pts 0–7, ~20 s dwell) | ≈ (+24.0, −27.3) | **36.3 m / 119 ft @ 138.6°T** |
| Track **end** (pts 16–22, ~40 s dwell) | ≈ (+5.3, +0.8) scattered, last (+7.5, +1.0) | **4–8 m @ 58–93°T** |
| Start → end | | 32.5 m (107 ft) @ 330°T |

### The ambiguity you must resolve with the operator before scoring

The operator said the **45 ft end is "where the track stops"**. But the track *stops* a few
metres from the house — essentially at the surveyed feed — and *starts* 36 m out to the
south-east. Read literally, the elevated end is next to the transformer, which cannot be
right for a 130 ft wire.

The reading that fits the physics is the **reverse**: the walk started at the far elevated
end and finished back at the transformer.

- 10 ft feed → 45 ft end is a 10.67 m rise; a 39.6 m wire then reaches at most 38.1 m of
  horizontal run. The start point is 36.3 m out — **fits with ~2–3% slack**, which is
  exactly what a real hung wire has.
- The end cluster sits 4–8 m from the surveyed feed, which is inside wrist-GPS error under
  canopy (commonly ±5–10 m). The operator also dwelt there ~40 s, consistent with standing
  at the transformer.

**Ask before you compute**, in one short question: did the walk start at the high end and
finish at the transformer? Also worth confirming in the same question: is the wire a
straight run between those two points, or does it pass over a support in between?

If confirmed, the current deployment is a **straight sloper, feed 10 ft → 45 ft end, ~36 m
run on ~138–139°T (≈123°M), ~16–17° slope**. Note how close that bearing is to T45 (143°T)
and the backyard-corner line (155°T), and that the south property line is the binding
constraint in that direction. Checked already: the GPX start point is **on the lot but
inside the 5 m setback** — `inside_parcel()` returns False, `inside_parcel(margin_m=0)`
returns True. With ±5–10 m GPS error it could plausibly be over the line; say so rather
than calling it either way. (T30's support on a similar heading was 39 ft off the lot.)

### How to score it

Add it to `compare_options.py` as a new keyed option (suggest `CURRENT`) built with the
existing `_sloper(key, label, feed_en, feed_ft, top_en, note)` helper, feed `(0,0)` at
10 ft, top at the GPX start point at 45 ft. Two cautions:

1. `_sloper` computes rise from `√(WIRE² − run²)` — it assumes a **taut** wire and will
   derive its own top height (~43.6 ft at 36.3 m) rather than use 45 ft. That is within the
   operator's estimate; say so, or build the `Option` directly with the measured 45 ft.
2. GPS error dominates. Report a **sensitivity band**: rotate the end ±10° and shift it
   ±5 m and show how much the 3-band score and region count move. A single number from a
   wrist GPS under conifer would overstate what is known.

Then compare against **BASE** (the operator's "previous deployment"), **F10-A** and
**RB-POST20**, per band and per region, and place it in the three-band ranking. Read
`AGENT_GUIDE.md` on tie bands before quoting a rank number.

After that, per the operator's standing preference: update README.md, AGENT_GUIDE.md,
SESSION-LOG.md, regenerate CSVs/KML, update both artifacts, and commit with a descriptive
message ending `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. Also run
`tools/canopy_from_ortho.py`-style sampling along the new path — the operator's current
wire runs through the woods south-east of the lawn and that canopy fraction is worth
stating.

---

## Things a fresh session will get wrong without being told

Full list in `AGENT_GUIDE.md`. The ones most likely to bite this task:

- **39.6 m wire, 80 m band.** Not a 40 m band antenna.
- **Both ends of an EFHW are current nulls.** End height and feed height matter far less
  than intuition says (`tools/endpoint_study.py`: 0.35 dB across 50 ft of end height).
- **The slant model (METHOD.md §9) is LOW confidence** and has already been wrong once. A
  16° sloper sits near the boundary where it switches in (`slope_deg > 0.5` uses the slant
  model). Say which model scored it.
- **62% of the recommended wire path is over canopy and no model has a tree-absorption
  term.** Every dB here is an optimistic ceiling.
- **Never rank on aggregate dBi alone**; primary key is workable cells, and rows inside a
  tie band are not ordered meaningfully.
- **Parcel status goes stale when bearings change.** Read the "SUPPORTS THAT ARE NOT ON
  THE PARCEL" block from the tool, not prose.
- **Tree heights were never measured.** Four canopy-height sources and shadow
  photogrammetry all failed; see `imagery/README.md`.

## Environment notes (Windows, PowerShell 5.1)

- Do **not** round-trip markdown through `Get-Content -Raw | Set-Content -Encoding utf8` —
  it mojibakes UTF-8 and adds a BOM. That happened once in this study. Use the Edit tool or
  .NET `WriteAllText` with `UTF8Encoding($false)`.
- Write commit messages to a file and `git commit -F`; heredocs don't exist in PS 5.1.
- Pillow and numpy are available; laspy/pdal are not.
- `compare_options.py` runs in ~10 s.
