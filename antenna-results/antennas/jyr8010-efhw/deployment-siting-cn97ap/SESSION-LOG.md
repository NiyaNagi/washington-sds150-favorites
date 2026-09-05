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

## Corrections summary

| # | Error | Corrected in | Status |
|---|---|---|---|
| 1 | Wire read as 20 m (40 m band) instead of 39.6 m (80 m band) | Phase 2 | ✅ retracted |
| 2 | Travelling-wave lobe formula (35.5°) instead of standing-wave (57.5°) | Phase 3 | ✅ retracted |
| 3 | Bend stated as ~30°, actually 60.9° | Phase 2 | ✅ operator confirmed coordinates |
| 4 | First screenshot assumed north-up; it was rotated | Phase 2 | ✅ operator confirmed |
| 5 | Leg 1 assumed to be 66% of the wire; it is 45% | Phase 2 | ✅ leg 2 dominates |

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
