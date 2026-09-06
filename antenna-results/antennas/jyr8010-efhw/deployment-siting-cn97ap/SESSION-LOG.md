# Session log — 2026-09-05

Chronological record of the siting session, including every operator input, every
external query, and every correction. Kept because **fourteen** corrections were made and
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

**Anything in the conversation before each correction is stale.** The files in this
directory reflect only post-correction values.

---

## Not done

- No NEC model — **most needed on the T class**, where §9 has already been wrong once and
  the answer moved 6 dB when it was fixed
- No propagation model. The band figures say where the antenna puts power, never whether
  a band is open. 10 m scores best for the flat-top and is also the band most often shut.
- 30 m / 17 m / 12 m unmodelled — not harmonics of a 39.6 m wire; would need tuner data
- No post-installation sweep — **the antenna was not built as of 2026-09-05**
- No canopy-height correction to the bare-earth horizon
- No live magnetic declination query (15.3°E from general knowledge)
- Building footprints not retrieved; house outline traced from imagery
- Source screenshots not saved to the repo (chat attachments only)
