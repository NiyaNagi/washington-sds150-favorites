# Session log — 2026-09-05

Chronological record of the siting session, including every operator input, every
external query, and every correction. Kept because **sixteen** corrections were made and
retracted across the session — two of them reversed a headline conclusion outright — and a
future agent needs to know which conclusions are stale.

---

## Phase 1 — Repo review and first (wrong) answer

**Operator asked:** read the antenna test results, calculate ideal height for a sloper
and inverted-V for the "jy8010" EFHW, optimising 40 m and 20 m resonance.

**Data read from the repo:**

- `../README.md` and `../data/measurement_metadata.json` — JYR8010 band scorecard
- `../../gowenic-efhw/README.md` — build history and band scorecard
- `../../gowenic-efhw/measurements/history/2026-08-17_2319_efhw_harmonics_25ft_sloper/summary.json`
  — the only real sloper data in the repo

### ⚠️ ERROR 1 — wire length

Read `radiating_element_length_m: 40` and the phrase "40-meter end-fed half-wave design"
as meaning a **40 m band** EFHW (~20 m of wire). Produced half-wave lengths of 20.0 m
flat-top / 19.8 m sloper / 19.6 m inverted-V, and height recommendations of 12–15 m.

**All of that was wrong and is retracted.** It means 40 **metres of wire** — an 80 m band
EFHW. Corrected in Phase 2. See `data/antenna-spec.json` → `THE_CORRECTION`.

### ⚠️ ERROR 2 — lobe angle formula

Used the *travelling-wave* long-wire formula `cos θ ≈ 1 − 0.371/n`, giving 20 m lobes at
35.5° from the wire axis. That formula is for **terminated** wires. The correct
standing-wave result is **57.5°**. Corrected in Phase 3.

---

## Phase 2 — Site geometry, and the length correction

**Operator supplied** (model switched to Opus here):

| Point | Coordinate |
|---|---|
| start (feed, fixed, 10 ft) | 47°38'2.61"N 121°59'47.73"W |
| apex (tree, 35 ft) | 47°38'2.68"N 121°59'46.97"W |
| end | 47°38'2.41"N 121°59'46.67"W |

Plus: apex is ~66% of the wire from the start; end is rotated ~30° clockwise off the
start–apex line; goal is Europe, most of the US, and Australia. First screenshot attached
(oblique/rotated).

**Computed:** start→apex 16.01 m @ 82.2°T; apex→end 10.43 m @ 143.1°T; bend **60.9°**
clockwise, not the ~30° estimated; total path 26.4 m horizontal.

**Two discrepancies raised with the operator:**

1. Bend 60.9° vs the stated ~30°
2. The screenshot showed a north–south run; the coordinates describe east–southeast

**Web search** confirmed the JYR8010-150W is **39.6 m / 130 ft**, 1:64 transformer,
2.5 mm² copper, 150 W SSB / 100 W FT8. Error 1 corrected.

→ **The 39.6 m wire does not fit the 26.4 m path.** This became the central structural
finding.

**Operator answers:** measurements are approximate, extend the end in a line as needed;
feed fully fixed at 10 ft; coordinates are right, the image was rotated; wants options
across fixed / raised / relocated-within-10-ft feed positions.

---

## Phase 3 — Terrain discovery

**Operator supplied:** north-up screenshot with 5 pins, plus front yard corner
(47°38'2.80"N 121°59'47.92"W) and backyard corner (47°38'2.25"N 121°59'47.48"W). Asked
for GIS-based placement avoiding the house.

**External queries made:**

| Service | Result |
|---|---|
| King County `KingCo_Parcels` MapServer | ✅ PIN 1117200390, 2.373 acres, 28-vertex ring |
| USDA FS `R06_lidar_R_CanopyHeight` ImageServer identify | ❌ HTTP 500 — do not retry blindly |
| USGS 3DEP `epqs.nationalmap.gov` | ✅ 18 point queries, all successful |

**The finding that reordered everything:** the site is flat (0.6 m relief) but sits on a
**southwest shoulder**. Ground rises 59 m in 500 m toward Europe (30°) and falls 59 m in
500 m toward Australia (250°).

- Europe horizon **blocked to +5.7°**
- Australia horizon **open, −7.9° foreground drop**
- Later: East Asia (310°) also **−4.8°, open**

**Consequence:** Australia and Asia are the achievable DX; Europe is terrain-limited and
no antenna geometry fixes it.

Error 2 corrected here — lobe angle 35.5° → 57.5°, which changed the orientation
analysis.

**Operator answers:** go with the start point; 50 ft+ reachable at both supports; accept
the Florida/Caribbean 20 m hole; feed truly fixed (no new coax).

---

## Phase 4 — Alternate-site comparison

**Operator supplied:** third screenshot, plus front yard driveway corner
(47°38'2.46"N 121°59'48.61"W). Asked whether the front yard beats the fixed spot, and for
full country-by-country coverage.

**Image georeferenced** at 11.73 px/m; all five pins agreed with the coordinates within
0.5 m. Confirmed `start` = NE corner of the house, run entirely over lawn.

**27 great-circle bearings computed** and three options scored.

**Decisive result:** leg 1's fixed 82° bearing puts a 20 m lobe at **319°** — covering
Beijing 318°, Alaska 321°, Vladivostok 311°, Shanghai/HK 310°. A driveway run at ~320°
puts that entire cluster in its **axial null** (−22 to −60 dB) and nulls 13 of 24 target
areas versus 3 for the fixed spot.

→ **Start point wins decisively.** Front yard and driveway corners rejected.

Final design fixed at 50 ft on both supports, making the apex→far-support span level.
Artifact published.

---

## Phase 5 — This documentation

Directory created, all data extracted to `data/`, `tools/site_geometry.py` written and
**run to verify** it reproduces the published figures. It does, within ~1 dB on pattern
gain and ~0.01 m on geometry. Divergences reconciled in-file rather than hidden.

---

## Phase 6 — Topology comparison (same day, after documentation)

**Operator asked:** where a PVC-mast sloper would go and how it compares; how an
inverted-V off a single point compares; a per-region table with aggregate power; and a KML
overlay of all options.

`tools/compare_options.py` written to score ten topologies against 25 regions. Two bugs
were caught by running it rather than trusting the first output:

### ⚠️ ERROR 6 — optimiser had no geometric constraint

The first bearing scan selected **178°** for every sloper. That support point is **17 m
outside the parcel**. Fixed by adding `inside_parcel()`, which tests the south and east
boundary edges with a 5 m margin.

### ⚠️ ERROR 7 — optimising on aggregate power alone

The scan maximised `aggregate_dB` (mean linear power), which rewards *concentrating*
radiation rather than spreading it. It happily selected bearings that put −87 dB nulls on
Perth. Fixed by ranking on `n_workable` first, `aggregate_dB` second, and by reporting
median and hole-count alongside the aggregate everywhere.

**This flaw survives in the numbers and must be read carefully:** sloper S3 scores −5.98 dB
against the recommendation's −5.51, apparently within half a dB, while covering 14 regions
instead of 20 with 8 holes instead of 2.

### Results

| Key | Config | Avg ht | Aggregate | Workable | vs A |
|---|---|---|---|---|---|
| A | Bent flat-top, 2 tree supports | 41.6 ft | −5.51 dB | 20/25 | — |
| S3 | Sloper → 50 ft tree, due north | 37.0 ft | −5.98 dB | 14/25 | −0.5 |
| V1 | Inverted-V, one tree support | 33.2 ft | −6.57 dB | 18/25 | −1.1 |
| BASE | Original three-point plan | 22.5 ft | −9.04 dB | 12/25 | −3.5 |
| S5 | Sloper → 24 ft PVC over the lawn | 24.0 ft | −9.69 dB | 10/25 | −4.2 |
| V3 | Inverted-V on 24 ft PVC | 17.0 ft | −12.96 dB | 3/25 | −7.5 |

Headline: **a 39.6 m wire cannot form a steep sloper at these heights** — 6.2° from a 24 ft
mast, 11.6° from a 50 ft tree, versus the 65 ft of drop a real 30° sloper needs. Every
"sloper" here is a tilted flat-top governed by average height, which is why PVC collapses.

Also produced `data/deployment-options.kml`: 67 placemarks in 12 folders — all ten
deployments, six operator reference points, and a 2 km great-circle ray per region.
Validated as well-formed XML.

Artifact updated with the comparison, the PVC verdict and the one-support verdict.

## Phase 7 — Tall sloper class and insulator research

**Operator clarified:** support height was never the constraint — **150 ft trees are
available.** Asked for an unconstrained-height sloper class, not constrained to the parcel
(showing where options fall outside it), added *alongside* the existing options rather
than replacing them. Also asked for ceramic insulator product research.

### The regime change

With height unconstrained, a 39.6 m wire can slope steeply. At 66° it is **83% vertically
polarised** (`sin²θ = 0.83`) — effectively an end-fed half-wave vertical: omnidirectional
in azimuth, current maxima far higher than any flat-top reaches. Sections 3–4 of METHOD.md
stop applying, so a separate slant model was added as §9.

Mean height of the four 20 m current maxima — pure arithmetic, HIGH confidence — added as
a metric for every option. Flat-top: **41 ft**. T-APEX: **83 ft**.

### Results

| Key | Slope | Top | Support dist | Aggregate | Workable | Holes |
|---|---|---|---|---|---|---|
| T75 | 75° | 149 ft | 33.6 ft | −4.30 dB | 25/25 | 0 |
| **T‑APEX** | 66° | 143 ft | 52.5 ft | −4.57 dB | 25/25 | 0 |
| T60 | 60° | 137 ft | 65.0 ft | −4.64 dB | 25/25 | 0 |
| T45 | 45° | 116 ft | 91.9 ft | −5.29 dB | 25/25 | 0 |
| T30 | 30° | 89 ft | 112.5 ft | −5.36 dB | 25/25 | 0 |

**T‑APEX requires no new support** — the existing apex tree is 52 ft 6 in away, and
√(39.6² − 16.01²) = 36.2 m of rise gives 66.2° automatically at a 143 ft attachment.

**Answering the out-of-parcel request: none of them go outside.** Height and footprint
trade off — at 75° the support is 34 ft from the feed. The tall sloper is both the
highest-scoring and the most compact class. Only the short slopers, needing a ~130 ft
ground run, ever threatened the boundary.

The T class trades 1–5 dB off the flat-top's peak lobes to fill every hole: Caribbean
+11.6 dB, Florida +10.8, India +10.7, Novosibirsk +7.8; against Alaska −4.6, US Northeast
−1.4, VK2 −0.9.

### Confidence caveat, recorded prominently

The T-class dB figures rest on `VERT_RESPONSE_dB`, a stylized curve traced from published
charts rather than computed from soil constants, and the model ignores **ground loss** on
a forested hillside without radials and **tree absorption** along a 140 ft near-vertical
wire. Either could cost several dB. This is flagged in METHOD.md §9, AGENT_GUIDE.md, the
README and the artifact.

### ⚠️ ERROR 8 — end voltage overstated

Earlier revisions quoted **2–4 kV** at the wire ends. Correct working: 150 W into the 1:64
transformer's ~3,200 Ω primary is √(150 × 3200) = **693 V RMS** at the feed; the far end
runs on the order of **1 kV RMS / 1.4 kV peak**. Roughly half the earlier figure. Design
basis is now ~2 kV peak. Corrected in [`INSULATORS.md`](INSULATORS.md) and the artifact.

New [`INSULATORS.md`](INSULATORS.md) covers the wet-tracking failure mode (creepage, not
dielectric breakdown), specific products (MFJ-16A01 6-pack with 7/16 in holes as the
primary pick), and placement — **two eggs in series at the apex**, because it sits at
17.86 m of wire, beside the 19.8 m voltage maximum on 40 m and 20 m.

KML regenerated: 82 placemarks in 17 folders, T class in bright orange.

## Phase 8 — all bands, and the T class reverses

The operator asked to extend every option across every band the antenna supports, aggregate
40 m + 20 m + the next most popular band, and rank on linear power to regions.

**Five bands, not "80–10 continuous".** A 39.6 m EFHW is resonant only where the wire is an
integer number of half-waves: 80/40/20/15/10. The odd harmonics land near 10.65, 17.75 and
24.85 MHz, so **30 m, 17 m and 12 m do not exist on this antenna** without a tuner. That
settles which band joins 40 and 20 in the aggregate: 17 m would be the natural third DX
band by popularity, and it is unavailable, so **15 m** it is. Recorded in METHOD.md §8.

**A second dB scale was needed.** `pattern_dB()` normalises each wire to its own peak lobe,
which quietly discards the ~5 dB more peak directivity a 4 λ wire has over a half-wave one.
Fine within a band, invalid across bands. Added `net_dBi = net_dB + band peak directivity`
and computed every cross-band figure on it, leaving the normalised columns untouched so
every previously published 20 m and 15 m number still reproduces.

**Then the slant model had to be rewritten, and it reversed its own conclusion.** Extending
the T class across bands exposed that the section 9 model could not vary with frequency in
the way the physics demands. See corrections 10 and 11.

**Result.** The recommended flat-top (A) leads the three-band ranking at 49/75 workable
cells and −0.16 dBi, with the best worst-case of anything near it (−25.4 dBi against T30's
−45.4). The flat-top turns out to be a **15 m and 10 m antenna first** (+2.06 / +2.26 dBi),
a competent 20 m one, and regional-only on 80 m, where at 41 ft it is 0.15 λ up and has no
lobe at all. Florida and the Caribbean — the accepted 20 m hole — return on 15 m and 10 m.

New outputs: `option-comparison-multiband.csv` (5 bands × 25 regions × 15 options),
`option-band-aggregate.csv` (75 rows), `mb3_*` columns on `option-aggregate.csv`, and a KML
whose folders are ordered by three-band rank and carry a per-band table each.

### ⚠️ ERROR 10 — the slant model was wrong, and it had been driving the headline

The Phase 7 T-class result rested on a polarisation decomposition: `sin²θ` of the power
went to a **band-independent, omnidirectional** vertical curve, `cos²θ` to the long-wire
pattern of the wire's ground projection. Two failures:

1. **The azimuth pattern was evaluated at an azimuth difference, not at the true 3-D angle
   from the wire axis.** For a wire tilted 66° those are barely related. This is what made
   the T class look omnidirectional with no nulls — the most-quoted claim of Phase 7.
2. **It could not vary with frequency in the way that matters.** At 66° a 39.6 m wire has a
   **1.7 λ vertical extent on 20 m and 3.4 λ on 10 m.** A radiator that long in the vertical
   plane breaks into lobes and loses low-angle response — the same effect that makes a
   vertical longer than ~0.64 λ a poor DX antenna. A band-independent curve cannot express
   it, so the old model gave the T class credit on the high bands that it does not have.

Rewritten to use the exact free-space long-wire pattern at the true 3-D axis angle, the
band's own current-maxima height, and separate reflection phases for the two polarisations
(horizontal inverts, vertical does not). Ground loss is now loss only.

**This reversed the Phase 7 headline.** T-APEX went from **−4.57 dB and first place** to
**−10.19 dB on 20 m and 8th of 15** on the three-band ranking. The T class is now strongest
on 80 m and 40 m, where the wire is short in wavelengths and height dominates, and weakest
on 15 m and 10 m. T-APEX is the study's **best 80 m option** (−5.10 dBi, 14/25 regions
against the flat-top's 3/25) and not the right answer for anything else.

The direction of that reversal is physically sound. The magnitude is not — §9 remains the
lowest-confidence model here, and it has now been wrong once. **Every T-class dB figure
published before 2026-09-05 is stale.**

### ⚠️ ERROR 11 — the new ranking repeated error 7 on a new axis

The first three-band ranking sorted on `n_regions_covered` first. That put T45 above the
recommended flat-top on the strength of one extra marginal region, while A beat it on mean
power, workable cells, holes and worst case simultaneously. Exactly the trap METHOD.md §7
already documents, re-introduced on a different metric. Re-sorted on workable band×region
cells first, regions second, mean power last.

## Phase 9 — the end-point question, and two corrections

**Operator asked:** would re-siting the far end help — for example off the house roof as a
sloper? New `tools/endpoint_study.py` splits that into four separately-scored questions.

**End height: 0.35 dB across 50 ft.** Both ends of an EFHW are voltage maxima, i.e. current
nulls, and support 3 already sits at the 29.7 m current maximum precisely so the end would
not have to matter. Nearly model-independent.

**End azimuth: at most +0.5 dB, and the wrong trade.** Best honestly-scorable azimuth (35°T)
buys US Southeast +5.0, Caribbean +4.7, Denver +2.9 and pays Hawaii −7.8, South Africa −6.2,
VK2 −2.9. Every loser is in the 210–270° sector — the only bearing with a −7.9° foreground
downslope. Every winner already returns on 15 m and 10 m for free.

**Roof as the high support: 2.6–4.1 dB worse.** The ridge is ~24 ft from the feed against
the tree's 52.5 ft, so 81% of the wire slopes away from a low point and average height
collapses from 41.6 ft to 16–27 ft.

**Roof as the FEED, sloping up: 0.02 dB at matched slope.** See correction 13.

A scan trap was recorded: the raw top-ranked azimuth was 215°T, a **133° bend**. §3 scores a
bent wire as the union of two lobe sets and ignores relative phase, so it overstates sharp
bends where near-antiparallel legs cancel. `endpoint_study.py` marks anything past ~110° as
NOT VALID. The pattern is also front/back symmetric, so 35°T and 215°T score identically
while being completely different physical wires.

### ⚠️ ERROR 12 — a parcel claim outlived the bearings it was true of

Phase 8 re-scanned the T-class bearings on the three-band metric. T30 moved to 176°T and T45
to 143°T. The sentence "**None of the T options leave the parcel**", written in Phase 7 and
true of the old bearings, was carried into the same commit unchanged — and is now false:

| Key | Bearing | Support | Status |
|---|---|---|---|
| T30 | 176°T | 112.5 ft | **39 ft off the lot** |
| T45 | 143°T | 91.9 ft | on the lot, 10 ft inside the south line, fails the 5 m setback |

`compare_options.py` had it right in its per-support output the whole time; only the prose
was stale. It now prints a dedicated **SUPPORTS THAT ARE NOT ON THE PARCEL** block that
separates "off the lot" from "inside the setback". This matters: **T30 is the second-ranked
option** and it cannot be built where the scan puts it.

### ⚠️ ERROR 13 — scored the roof upside down

`endpoint_study.py` §3 put the roof at the **high** end with the wire sloping down. The
operator meant the opposite: transformer **on** the roof, wire sloping **up** to a tree.
Both are worth scoring and they are different antennas, so §4 was added rather than
replacing §3.

The answer to the question actually asked is **0.02 dB at matched slope**. The feed is the
other voltage maximum, so its height buys as little as the end's — raising the roof feed
20 → 30 ft moves the 3-band figure by 0.06 dB, slightly the wrong way. The only real effect
of the move is that the apex tree goes from 16.0 m to 19.3 m away, softening the forced
slope from 66.2° to 60.8° for +0.67 dB, which a further support buys for nothing.

Worth recording for future agents: **an upward sloper off the fixed feed is the T class.**
T‑APEX is literally "feed 24 ft, up 66.2° to the apex tree at 143 ft". With a fixed 39.6 m
wire `rise = √(39.6² − run²)`, so support distance chooses the slope and there is no third
variable.

## Phase 10 — one-support slopers, and the deployment premise inverted

**Operator asked:** add the roof-feed variants to the main table; show sloper variants
constrained by the front and back yard corners; "figure out how to mathematically discover
the best options to compare with option A **because option A will be much harder to
deploy**."

**Clarifications given:** the anchor stays the current start pin, only rotation is
constrained; **150 ft trees exist at both yard corners**; score the roof feed as a real
candidate, not a side-question.

Eight new options in three sub-classes — K (supports known to exist), C (rotation locked to
a corner bearing), G (best found by unconstrained search, parcel and 150 ft cap enforced) —
plus RF‑APEX. Total is now 23.

### The premise was backwards

Nothing in the scoring knew about deployment effort, so `Option.n_anchors`,
`.max_anchor_ft` and `.throw_class` were added. They invert the operator's assumption.

A straight sloper has **no free parameters**: `rise = √(39.6² − run²)`. Choosing the support
distance chooses everything else, so slope, attachment height and performance ride one
curve — and "shallower" always means "further away", never "lower".

| Run | Slope | Attachment | Throw | Cells |
|---|---|---|---|---|
| 23 ft (front-yard tree) | 79.7° | 152 ft | climb | 11/75 |
| 40 ft (backyard tree) | 71.9° | 148 ft | climb | 26/75 |
| 52 ft (apex tree) | 66.2° | 143 ft | climb | 37/75 |
| 87 ft (G‑FEED) | 47.8° | 120 ft | very hard | 49/75 |
| 127 ft | 11.6° | 50 ft | easy | 38/75 |

**Every one-support sloper that matches option A needs a 116–120 ft anchor.** Option A needs
three attachments but its highest is **50 ft** — a routine throw. The bend is what buys
height in the middle of the wire, where the current maxima are, without any single support
being high. Option A is the *easiest* option that performs, not the hardest.

The honest low-effort alternative is **V1** — one 50 ft support, −0.72 dB and 5 cells behind
A. Every sloper that beats V1 needs an anchor more than twice as high.

### Corner constraints

- **K‑BACK / K‑FRONT** (support *at* the corner trees): 40.3 ft and 23.2 ft from the feed
  force 71.9° and 79.7°. K‑FRONT needs a **152 ft** attachment, over the cap, and scores
  11/75 — second worst in the study. **The corner trees are too close to be useful.**
- **C‑FRONT** (326°T, distance free): reaches 88.9 ft inside the lot, 46.8°, 44/75.
- **C‑BACK** (155°T): boundary-limited to 66.9 ft → 59° → 39/75. Lifting the parcel
  constraint (**C‑BACK‑X**) moves the support to 97.8 ft, **8 ft past the south line**, and
  gives 48/75 with +2.5 dB. Eight feet of boundary is worth nine cells on that heading.
- T30 rotated onto the backyard bearing would land ~20 ft past the line.

### Roof feed, scored properly

**G‑ROOF −2.41 dBi / 49-75 against G‑FEED −2.45 / 49-75.** With azimuth *and* distance
re-optimised around the new feed position it is still a **0.04 dB** wash, consistent with
the 0.02 dB found at matched slope in Phase 9. Scored as a real candidate as instructed;
the answer did not change.

### Ranking presentation

The top tie band now holds five options at 49/75, and the tiebreaks below the primary key
cannot separate them at this model's precision. Rather than change the sort a third time
(see corrections 7 and 11), the ranking now **prints a rule between tie bands** and says
explicitly that ordering within a band is not meaningful. KML: 106 placemarks in 25 folders,
one-support slopers in white.

## Phase 11 — the 10 ft feed category

**Operator asked:** the transformer has to stay at 10 ft for now; score that as its own
category across all the options and give the best one.

New `F10-*` family, eight options, in `build_feed10_class()`. Kept separate rather than
mixed in, because every other class assumes the feed can be lifted to 24 ft.

**The 10 ft feed costs option A 0.30 dB and 2 cells.** That is the whole penalty. The feed
is a voltage maximum — a current null — so its own height barely matters; what costs is
that it drags the first part of the wire down with it, and on a flat-top that is where two
of the four 20 m current maxima live.

| Key | 3-band dBi | Cells | Worst | anch | highest | vs A |
|---|---|---|---|---|---|---|
| F10‑G | −3.05 | **49/75** | −44.9 | 1 | 105 ft | −2.89 |
| **F10‑A** | **−0.46** | 47/75 | **−26.2** | 3 | **50 ft** | **−0.30** |
| F10‑CF | −3.24 | 42/75 | −48.7 | 1 | 106 ft | −3.08 |
| F10‑V | −1.31 | 40/75 | −27.9 | 1 | 50 ft | −1.15 |
| F10‑CB | −4.51 | 39/75 | −56.8 | 1 | 122 ft | −4.35 |
| F10‑APEX | −4.49 | 37/75 | −59.5 | 1 | 129 ft | −4.34 |
| F10‑BACK | −5.67 | 27/75 | −89.3 | 1 | 134 ft | −5.51 |
| F10‑FRONT | −7.63 | 14/75 | −73.0 | 1 | 138 ft | −7.47 |

**Recommendation: F10‑A**, not F10‑G. F10‑G edges the primary key 49 to 47 and loses on
everything else — 2.6 dB of aggregate, an 18 dB worse worst-case, and a 105 ft rope throw
against 50 ft. Two cells do not buy that. The tie-band rule from Phase 10 applies: read the
whole row.

Per band, F10‑A against A at 24 ft: 80 m −0.85, 40 m −0.67, 20 m −0.46, 15 m −0.13, 10 m
**+0.21**. The higher the band the less feed height matters, and on 10 m dropping the feed
is marginally *better* because the lower average height puts the ground-reflection lobe
closer to the angles that band wants.

**Only one support moves** versus the 24 ft plan. Leg 1 lengthens 17.86 → 20.12 m as the
feed drops, so the 29.7 m current maximum arrives sooner along leg 2: support 3 goes from
83 ft 9 in at 102°T to **77 ft 2 in at 100°T**. Apex and end tie-off are unchanged.

KML: 133 placemarks in 33 folders, the F10 family in spring green.

## Phase 12 — chasing tree heights, and the garden posts

**Operator asked:** try both remaining tree-height routes, and score deployments using PVC
on the pre-staked garden posts inside a strip they marked on the plan view.

### Tree heights: both routes closed

**Point clouds — closed by tooling.** `king_county_east_2021` covers the site in the WA DNR
LiDAR portal, but the portal's download endpoint returns 403 without its API contract, and
this environment has **numpy but no `laspy` and no `pdal`**, so LAZ cannot be decoded anyway.

**Shadow photogrammetry — closed by the scene.** New `tools/shadow_heights.py` measures the
solar azimuth by cross-correlating a sunlit-roof mask against a deep-shadow mask, then
brackets the elevation from the leaf-on flight window using
`sin(dec) = sin(lat)sin(h) + cos(lat)cos(h)cos(az)`.

It does not converge here, and **the tool says so rather than producing a number.** First run
reported a sun azimuth of 341° — impossible at 47.6°N, caught because the elevation solver
returned no solution. Constraining the search to the physically possible arc (55–305°) only
made it pin to the boundary: it is locking onto dark tree canopy, not roof shadow.

The direction is settleable by elimination: the driveway north-east of the reference house is
lit while the strip north-west of it is dark, so **shadows fall north-west and the sun is in
the south-east — a morning capture.** But that throws the house's shadow onto dark asphalt and
into the treeline. The lawn, the one good projection screen on the property, is on the sunlit
side. There is nothing for a length measurement to bite on.

**What would fix it, cheapest first:** measure one height on the ground and pair it with its
shadow; or skip photogrammetry entirely and use a phone clinometer, which is more accurate
than anything derivable from this image and also answers the question that matters — whether
a usable limb exists at 50 ft — which no overhead view can show.

**The 62% canopy finding does not depend on any of this.**

### The garden posts

The operator's marked strip, georeferenced against the four support markers by similarity
fit — **6 cm worst residual on the ground**: 11–13 ft wide, 55–59 ft long, long axis 139°T,
centroid 100 ft from the feed at 100°M, entirely inside the parcel.

New `RB-*` class in `build_redbox_class()`, feed held at 10 ft throughout.

**RB‑1TREE is the best buildable option in the study.** Apex tree at 50 ft, then one post:
−0.40 dBi, 48/75 cells, and **worst region −22.5, the best worst case anywhere here.** It
beats F10‑A on aggregate, cells and worst case while needing **one fewer rope throw** — two
anchors, one of which you walk to. Costs one region (23 vs 24). Its 15 m figure, +2.12 dBi
across 22 of 25 regions, is the best 15 m number in the study.

Post height matters gently: **0.83 dB across 10→36 ft**, about 0.32 dB per 10 ft, and the
position moves only 10 ft. **A 20 ft post already matches F10‑A's 47 cells and beats its
worst case.** Recommended rather than the optimiser's 30 ft, because the difference is
0.31 dB and the build difficulty is not.

**RB‑NOTREE** — single span to a 30 ft post at the strip's far corner, zero rope throws —
scores −6.05 dBi, 11/75, 8 of 25 regions. Recorded as the floor.

RB‑2POST found no solution: two posts both inside a 3.5 m-wide strip cannot satisfy the exact
wire-length constraints. Not a failure worth chasing; RB‑1TREE dominates it anyway.

KML: 140 placemarks in 35 folders, garden-post options in red.

## Phase 13 — 2026-09-12: scoring what is actually up

**Operator supplied:** a Garmin watch track of the antenna currently hung
(`../50ft sloper antenna deployment.gpx`, 23 points, 2026-09-07 03:45–03:47 UTC; not
committed), with the feed "the same height as before" (10 ft) and the end "about 45 ft off the
ground where the track stops". Asked where it fits among the options and how it compares to the
previous deployment.

**Direction question, asked before scoring.** Read literally, the high end is where the track
*stops* — 4–8 m from the transformer, impossible for a 130 ft wire. The track *starts* 36.6 m out
to the south-east, which a 10 ft → 45 ft wire reaches with ~4% slack. **The operator confirmed
the walk started at the high end and that the wire is one straight run.**

**Geometry.** End = mean of the 8-point start dwell: **36.58 m / 120.0 ft at 138.9°T / 123.6°M**.
Slope 16.3°, 38.10 m straight span, 1.50 m (3.9%) slack. The feed stays the surveyed point. New
`CURRENT` option in `compare_options.py`, built with the stated 45 ft rather than `_sloper()`.

**Result.** Slant model: **−3.70 dBi, 24/75 cells, 17/25 regions, median −8.8, worst −58.9 —
rank 29 of 35**, alone in its tie band. The original plan (BASE) is −2.84 / 35/75 at rank 23;
RB‑POST20 −0.71 / 47/75; F10‑A −0.46 / 47/75. The wire axis (139/319°T) puts end-fire nulls on
South America (−26.7 dB against BASE) and the Beijing/Shanghai/Vladivostok cluster (−4.5 to
−5.7). It does better than BASE toward Novosibirsk, India, US Northeast, Hawaii and VK2 (+2 to
+4). Horizontal-model cross-check: −5.15 / 17/75.

**GPS sensitivity.** ±10° and up to −5 m of run: −3.93 to −2.56 dBi, 24–32 cells. Longer runs are
impossible at 45 ft. No perturbation reaches BASE. End at 50 ft: −3.20, 30/75.

**Canopy.** 4% (corridor) / 5% (close capture) — it runs down the open lawn beside the house.
Checked against the photo with the track overlaid before quoting. This exposed correction 15.

**Parcel.** The dwell mean is 0.5 m **past** the south line. Inside GPS error; not called.

New output `data/current-deployment-sensitivity.csv`; KML gains a pink CURRENT folder. The
deployment guide gained a "what's up now" section, and its RB‑POST20 figures — hard-coded at
−0.75 / 46 cells and stale against the tool's −0.71 / 47 — are now computed.

### ⚠️ ERROR 15 — "no open-ground route exists" was a scan artefact

Phase 12's radial scan reported the longest clear run from the feed as ~24 ft and concluded no
layout could avoid canopy. The scan stops at the first textured pixel; beds, the house edge and
the patio trip it within a few metres on almost every bearing (at 140°T: 0.2 m on the close
capture, 5.0 m on the corridor). Sampled as a fraction along the path, the as-built wire at
139°T is 4–5% canopy over 36.6 m, and the photo shows open lawn. The **62% for F10‑A stands**;
the generalisation does not.

### ⚠️ ERROR 16 — two figures in HANDOFF.md

The handoff said `_sloper()` would derive an end height of ~43.6 ft at a 36.3 m run. A taut
39.6 m wire at that run rises 15.2 m, putting the end at **~60 ft**. It also said the GPX start
was on the lot inside the setback; that used a single trackpoint, and the 8-point dwell mean is
0.5 m past the line. Both are within GPS error, and neither changed the scoring, which used 45 ft.

## Phase 14 — 2026-09-12: the lineup, and a 40 + 20 m search

**Operator asked:** overlay what's up now, BASE, RB‑POST20, F10‑A, the top three slopers and the top
three inverted‑V or L deployments on the property and compare them in the style of the deployment
guide; then compute the best options for 40 m and 20 m alone.

**Clarified before building:** slopers with a 10 ft feed, parcel not enforced; search new V and L
shapes (on the lot); one 40 + 20 m ranking with every family re-searched; a new page.

New `tools/topology_search.py`. **The inverted‑L needed a model the study did not have** — nothing
could score a vertical section. Both legs go on the §9 slant model and are combined as a §3 union.
New, unvalidated, and at a 90° bend that `endpoint_study.py` classes as OVERSTATED.

**Two search artefacts were caught on the first run, before anything was published:**

1. An "L" with **1 ft** hanging down took first place. It was a 30° sloper whose rising leg had been
   scored on the horizontal model — so it won on a model choice, not a geometry. Fixed: the rising
   leg uses the slant model (as every sloper does) and at least 10 m must hang vertically.
2. The top inverted‑V had its apex **13 ft** from the feed — a near-vertical first leg at the
   high-voltage end, scored as horizontal. Fixed: V legs capped at 40° (V1/V2 sit at 26–34°), and
   the three picks must be distinct designs rather than one V slid along its leg.

The page build caught a third: the 40 + 20 m "top five" were two Ls each drawn twice. The page
now drops near-duplicates.

**Result, 3-band.** Sloper search re-found **F10‑G** exactly — a useful check. Slopers 1 and 3 are
new: 50/75 at 107 ft (15 ft past the south line) and 49/75 at 87 ft (−1.41 dBi, best aggregate of
any 10 ft feed sloper). **All three V‑or‑L picks are Ls, at 56–58/75 — the highest cell counts in
the study**, with 52–56 ft attachments. The best V is 50/75. Given the model behind the Ls, they
are a reason to run NEC, not a recommendation.

**Result, 40 + 20 m.** Ls again lead (42 and 40/50); best sloper 37/50 at 98 ft, 17 ft past the
line; the best non‑L built only from 50 ft throws is F10‑A with leg 2 re-aimed to 20°M (33/50, and
54/75 on 3 bands). RB‑POST20 and F10‑A drop to 25 and 27/50 — 15 m was their strongest band.

Map colours: validated categorical slots 1–3 all-pairs (`validate_palette.js`), orange taken at its
dark step because the light step sat 0.001 outside the dark lightness band.

## Phase 15 — 2026-09-12: feeding from the roof

**Operator asked:** with the feed at a red dot they marked on the roof in the lineup map, sloping
down off the house — or up from it — would it be better? Add those to the list, map the top three
slopers and top three V‑or‑L shapes from that point, and regenerate the lineup graphic.

**Where the dot is.** Read from the annotated screenshot of the page's own map: 13.6 px/m, checked
against CURRENT's far end and RB‑POST20's post, both within a pixel. ENU (−10.7, −10.5) — 15.0 m /
49 ft at 225.6°T / 210°M, on the roof. **Height not given; 25 ft assumed** (`ROOF_FEED_FT`), with
20 and 30 ft re-run on the page.

`topology_search.py` now takes any feed point and searches **downward** slopers whenever the feed is
15 ft or higher. A downward wire is scored end for end from its low end — the standing-wave pattern
and current maxima are symmetric. Transformer results are unchanged (a 10 ft feed cannot slope
down to an 8 ft end).

**Result.** Downward from 25 ft is geometrically boxed in: 17 ft of drop over 130 ft of wire is
at most 7.5°, so the best "down" wire is near-flat at 21–25 ft and scores **34/75**. Upward from the
roof: slopers 50/75 (same as from the transformer, but the best supports land 67–78 ft past the
south line); **inverted‑V 54/75, −0.02 dBi, against 50/75 from the transformer** — the only roof
gain on a model the study trusts; inverted‑L 59/75 on the unvalidated hybrid. The lineup page is
now "Sixteen Wires on One Lot" (same URL), with a roof section, and `imagery/lineup_roof.jpg`.

This does not contradict the Phase 10 roof-feed "wash" (G‑ROOF vs G‑FEED, 0.04 dB): that compared
slopers at matched geometry, and slopers are again a wash here. What the roof point changes is
where a *V* can put its apex.

## Phase 16 — 2026-09-12: NEC-2 validation, and the rankings reverse

**Operator asked:** validate the model completely; add three more roof variations of each type
(sloper, L, V); keep everything and re-rank all of it. **Clarified:** install PyNEC (real NEC-2;
operator approved the download); re-run the search on NEC itself; roof adds = 3 more slopers, 3
more Ls, 3 Vs; list every scored wire.

**PyNEC 2.3.4** installed from PyPI (built from its 1.5 MB source). New `tools/nec_engine.py`,
`tools/nec_validate.py`, `tools/nec_search.py`, `tools/build_nec_page.py`.

**Engine checks passed:** half-wave dipole 0.486 λ / 72.3 Ω / 2.17 dBi; take-off over perfect
ground within 0.2° of §4 at four heights; with a 1 m counterpoise the modelled wire's 80 m
resonance is 3.648 MHz against 3.6056 MHz measured on the real antenna.

**Two resonance-search errors were caught before any scoring used them:** peak |Z| runs away to
low frequency on an end-fed wire (gave "resonance ~6% low"), and a ±20% window landed on the odd
harmonics below 20/15/10 m. Now: peak R, harmonic n searched near n × the fundamental.

### ⚠️ ERROR 17 — the long-wire pattern formula was the centre-fed one

`site_geometry.longwire_field` is `|[cos(nπ/2·cos θ) − cos(nπ/2)]/sin θ|`, the pattern of a
**centre-fed** wire. This antenna is **end-fed**; for even n the pattern is
`|sin(nπ/2·cos θ)/sin θ|`. NEC lobes 53° / 36° / 29° / 25° on 40/20/15/10 m match that form
(pattern correlation 0.99) and ARRL's published angles; the study used 89° / 57° / 46° / 39°
(correlation 0.18–0.25). **Correction 2 was itself this error**: it rejected ~35° for 57.5°. The
AGENT_GUIDE trap that enforced 57.5° has been reversed.

### ⚠️ ERROR 18 — every analytic ranking in the study is superseded

NEC re-scored all 103 distinct wires. Old vs NEC rank correlation: **ρ = −0.07** (40/20/15) and
−0.14 (40/20). Cell agreement r = 0.24 bent-wire, 0.29 slant, 0.07 hybrid L. RB‑POST20 goes from
#46 to **#74** (20/75), F10‑A #45 → #66 (23/75), what is up now #96 → **#39** (30/75). The
yesterday-leading inverted-Ls drop to #13 and below. NEC's own choices barely move its ranking
(ground model ρ 0.96, segmentation 0.99, counterpoise 0.99, band vs resonant frequency 0.90);
the workable threshold does (±2 dB → 0.82–0.87).

**NEC re-search** (same families and limits, ~20k geometries, 113 s on 32 cores): #1 is a roof
sloper to a 69 ft support 81 ft past the south line (52/75); best on the lot a roof sloper to
62 ft at 60°M (49/75); best from the 10 ft transformer on the lot a sloper to 60 ft at 250°M
(39/75); best with no throw above 55 ft, 10 ft feed, on the lot: a sloper to 47 ft at 270°M
(38/75) and F10‑A with leg 2 at 60°M (37/75). Roof adds came from this search: roof slopers
4–6, Ls 4–6 and Vs 1–3.

Search labelling fix: S1–S5 were tagged "bent / flat-top" because they carry no slope angle;
now "sloper".

## Phase 17 — 2026-09-12: every roof sloper, exhaustively

**Operator asked:** run more NEC simulations of slopers off the roof and find the best one,
efficiently but completely.

A straight sloper from a fixed feed has two free parameters (bearing, run), so the space was
covered rather than sampled: `tools/nec_roof_sloper_scan.py` — 43,560 wires at 1° × 0.25 m up and
down from the 25 ft roof point, 5,842 refinements at 0.25° × 0.05 m around the best seeds of seven
categories on both rankings, a neighbourhood robustness score (mean and minimum over ±2°, ±0.5 m),
a stress test of the winners against 45 rivals under Sommerfeld ground, λ/40 segments, 0.5 and
2 m counterpoises, band frequencies, 20 and 30 ft roofs and the threshold ±2 dB, and full grids at
20 and 30 ft. 91 s total.

**Result.** Best on the lot: **59.2°M, support 125 ft out at 60 ft, 49/75**; most robust on the lot
58.7°M, 123 ft at 67 ft, 48/75 with every neighbour ≥ 46. Same bearing wins at every roof height
(47/49/51). Best anywhere 54/75 at 148.5°M, 81 ft past the south line. Easy-throw (≤ 55 ft) 47/75,
same bearing. Best downward wire effectively level, 35/75. The earlier NEC search's NR‑SL2
(49/75) was already this wire, which is the check that the search had not missed a better one.

## Phase 18 — 2026-09-12: Deployment 1 build guide

**Operator asked:** detailed diagrams from all angles and precise deployment measurements for
"deployment 1", in a separate section. **Clarified:** the #1 overall wire (148.5°M, support on the
neighbouring parcel), chosen knowingly over the on-lot winners.

`tools/deployment1.py`: geometry from the scan winner. The wire crosses the south line 33.1 ft out
at 36.2 ft up, and the support is 79.1 ft beyond the line measured square to it. Setting-out marks
come from the transformer, the backyard corner, the apex tree and the front-yard corner. The tool
also produces heights at 10 ft stations, current and voltage maxima on all five bands, a slack
table, canopy along the track (22% of the sampled 117 ft, trees from 94 ft out), per-band and
per-region NEC gains, and NEC azimuth and elevation patterns. Resonances were computed on the
exact geometry over ground: 3.597 / 7.360 / 14.889 / 22.390 / 29.862 MHz, or 3.556 / 7.275 /
14.717 / 22.132 / 29.518 scaled to the measured 80 m. Seven matplotlib plates were drawn; the page
gained a "Deployment 1" section.

**Caught on the first draft:** "1–2% slack" was bad advice. Free slack becomes sag fast (1% ≈ 8 ft
mid-span on this span), so the guide now tells the builder to let a 10 lb counterweight set the
tension (≈ 4 ft sag). Three diagram faults were also fixed before publishing: eye-level labels
drawn off-frame, a wrap-around line in the bearing-tolerance plot, and label collisions.

## Corrections summary

| # | Error | Corrected in | Status |
|---|---|---|---|
| 1 | Wire read as 20 m (40 m band) instead of 39.6 m (80 m band) | Phase 2 | ✅ retracted |
| 2 | Travelling-wave lobe formula (35.5°) instead of standing-wave (57.5°) | Phase 3 | ✅ retracted |
| 3 | Bend stated as ~30°, actually 60.9° | Phase 2 | ✅ operator confirmed coordinates |
| 4 | First screenshot assumed north-up; it was rotated | Phase 2 | ✅ operator confirmed |
| 5 | Leg 1 assumed to be 66% of the wire; it is 45% | Phase 2 | ✅ leg 2 dominates |
| 6 | Bearing optimiser had no parcel constraint; picked a point 17 m off the lot | Phase 6 | ✅ `inside_parcel()` added |
| 7 | Optimised on aggregate power alone, which rewards spiky patterns | Phase 6 | ✅ ranks on regions-workable first |
| 8 | End voltage quoted as 2–4 kV; actually ~1 kV RMS / 1.4 kV peak | Phase 7 | ✅ corrected in INSULATORS.md |
| 9 | Support height assumed capped at 50 ft; operator has 150 ft trees | Phase 7 | ✅ T class added |
| 10 | **Slant model treated a steep wire as omnidirectional, band-independently** | Phase 8 | ✅ METHOD.md §9 rewritten; **T-class conclusion reversed** |
| 11 | Three-band ranking first led with regions-covered, repeating error 7 on a new axis | Phase 8 | ✅ ranks on workable cells first |
| 12 | "None of the T options leave the parcel" survived the bearing change that made it false | Phase 9 | ✅ T30 is 39 ft off the lot; dedicated parcel block now printed |
| 13 | Scored the roof as the HIGH support when the operator meant the roof as the FEED | Phase 9 | ✅ both scored, kept separate |
| 14 | Compared a 3-anchor flat-top against 1-anchor slopers on gain alone, leaving the operator to believe A was the harder build | Phase 10 | ✅ throw effort scored; A is the *easiest* option that performs |
| 15 | "No open-ground route exists at any bearing" — radial scan stopped at the first textured pixel | Phase 13 | ✅ as-built wire is 4–5% canopy along 36.6 m of lawn; 62% for F10‑A unchanged |
| 16 | HANDOFF.md: taut-wire end height (~43.6 ft, actually ~60 ft) and GPX parcel status (dwell mean is 0.5 m past the line) | Phase 13 | ✅ corrected; scoring used the stated 45 ft |
| 17 | **§3 long-wire formula was the centre-fed pattern; this antenna is end-fed** — lobes wrong on 40/20/15/10 m (and correction 2 was this error) | Phase 16 | ✅ NEC-2; METHOD.md §3 banner, §11 |
| 18 | **Every analytic ranking superseded** — old vs NEC ρ = −0.07 over 103 wires | Phase 16 | ✅ rankings now from `tools/nec_search.py` |

**Anything in the conversation before each correction is stale.** The files in this
directory reflect only post-correction values.

---

## Not done

- No NEC model — **most needed on the T class**, where §9 has already been wrong once and
  the answer moved 6 dB when it was fixed
- No propagation model. The band figures say where the antenna puts power, never whether
  a band is open. 10 m scores best for the flat-top and is also the band most often shut.
- 30 m / 17 m / 12 m unmodelled — not harmonics of a 39.6 m wire; would need tuner data
- No post-installation sweep — **no recommended design was built as of 2026-09-12**; the
  as-built sloper (CURRENT) has not been swept either
- CURRENT's end height (45 ft) and the far-end tree's side of the south line are unmeasured
- **No NEC run on an inverted‑L.** The Ls top both rankings on a new, unvalidated hybrid model;
  one NEC run on Inverted‑L 1 would say whether the family is real
- No canopy-height correction to the bare-earth horizon
- No live magnetic declination query (15.3°E from general knowledge)
- Building footprints not retrieved; house outline traced from imagery
- Source screenshots not saved to the repo (chat attachments only)
