# Session log — 2026-09-05

Chronological record of the siting session, including every operator input, every
external query, and every correction. Kept because two substantive errors were made and
retracted mid-session; a future agent needs to know which conclusions are stale.

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

**Anything in the conversation before each correction is stale.** The files in this
directory reflect only post-correction values.

---

## Not done

- No NEC model
- No post-installation sweep — **the antenna was not built as of 2026-09-05**
- No canopy-height correction to the bare-earth horizon
- No live magnetic declination query (15.3°E from general knowledge)
- Building footprints not retrieved; house outline traced from imagery
- Source screenshots not saved to the repo (chat attachments only)
