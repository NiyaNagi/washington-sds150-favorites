# Method — models, formulas, and how much to trust each one

Everything in this study is **analytical modelling, not measurement.** No NEC solver was
run and no on-air testing was done. This file states each model, its formula, and its
confidence so a future agent knows which numbers are solid and which are indicative.

`tools/site_geometry.py` implements all of it in the standard library and is the
authoritative computation.

---

## 1. Local coordinate frame

Flat-earth ENU with the feed point as origin. Scale factors from the standard series:

```
lat_m = 111132.95 − 559.85·cos(2φ) + 1.175·cos(4φ)
lon_m = 111412.84·cos(φ) − 93.5·cos(3φ) + 0.118·cos(5φ)
```

At φ = 47.6341° N: **111,183.2 m/deg latitude**, **75,151.5 m/deg longitude**
(= 30.884 and 20.875 m per arcsecond).

**Confidence: HIGH.** Over the <60 m extent of this site the flat-earth approximation
errs by far less than a millimetre.

**The binding limit is input precision, not the model.** Operator coordinates were given
to 0.01 arcsecond ≈ **0.3 m**. Every derived position inherits that. Values printed to
the millimetre are arithmetic artefacts, not accuracy.

---

## 2. Great-circle bearings and distances

```
θ = atan2( sin Δλ · cos φ₂ ,  cos φ₁ sin φ₂ − sin φ₁ cos φ₂ cos Δλ )
d = 2R · asin( √( sin²(Δφ/2) + cos φ₁ cos φ₂ sin²(Δλ/2) ) ),  R = 6371 km
```

Computed from 47.6341 N, 121.9966 W to the reference cities in
`data/target-bearings.csv`.

**Confidence: HIGH** for bearings. Distances are spherical-earth and err by up to ~0.5%
versus a geodesic; irrelevant at the precision used here.

Magnetic conversion: **magnetic = true − 15.3°** (2026 epoch, Seattle area). This value
was taken from general knowledge, **not queried live** — verify against NOAA's WMM
calculator if precision matters.

---

## 3. Azimuth pattern — standing-wave long wire

A resonant wire of *n* half-waves has far-field amplitude, with θ measured **from the
wire axis**:

```
F(θ) = | [ cos(n·π/2 · cos θ) − cos(n·π/2) ] / sin θ |
```

For the 39.6 m wire:

| Band | Wire | n | Main lobe from axis | Peak F |
|---|---|---|---|---|
| 80m | 0.482 λ | 1 | 90° (broadside) | 1.00 |
| 40m | 0.944 λ | 2 | 90°, HPBW ±24° | 2.00 |
| 20m | 1.869 λ | 4 | **57.5°** | 2.337 |
| 15m | 2.800 λ | 6 | **48.2°** | 2.683 |
| 10m | 3.764 λ | 8 | ~40° | ~2.9 |

Tabulated in `data/pattern-model-tables.csv`.

> **A correction worth recording.** An early pass in this session used the *travelling-wave*
> long-wire lobe formula `cos θ ≈ 1 − 0.371/n`, which gave 35.5° from the axis on 20 m.
> That formula is for **terminated** long wires. A resonant standing-wave wire gives
> **57.5°**. The wrong figure briefly inverted the orientation conclusions. If you see
> 35° quoted anywhere for this antenna, it is stale.

**Confidence: MODERATE-HIGH for shape, LOW for absolute gain.** Thin-wire, free-space,
sinusoidal current assumed. Lobe *positions* are reliable. Null *depths* are not — real
installations over irregular ground with nearby trees show −10 to −15 dB where theory
says −40.

### Bent wires

A bent wire is approximated as the **union of two lobe sets** — for each target, take the
better of the two legs. Null-filling by a bend is a real and well-established effect, but
this treatment ignores the relative phase and current distribution between legs and so
overstates how cleanly the sets add. Directionally right; not a substitute for NEC.

### The constraint this model exposes

On 20 m the lobes sit at axis ±57° and ±123°, so the only available **lobe-to-lobe
separations are 66°, 114° and 180°**. Consequently:

- Central Europe (30°) and Sydney (245°) are 145° apart → **impossible on one straight wire**
- Florida (109°) and Sydney (245°) are 136° apart → **impossible even with the bend**

This is arithmetic, not modelling uncertainty. It drove the whole design.

---

## 4. Elevation pattern — ground reflection

Horizontal wire at height *h* over ground, relative field versus elevation angle θ:

```
F(θ) = 2 · sin( 2π · (h/λ) · sin θ )
```

Peak lobe where `sin θ = λ/(4h)`, i.e. `θ_peak = asin(λ/4h)` — undefined (no distinct
lobe; response peaks at zenith) when `h < λ/4`.

Average height is **weighted by wire length per span**, not by horizontal distance:

```
h_avg = Σ(wire_length_i · mean_height_i) / total_wire_length
```

**Confidence: MODERATE.** Assumes a perfectly conducting flat ground plane. Real soil
(and this site's forest) reduces the reflection and fills the zenith null. Take-off
*angles* are reliable to a few degrees; *absolute* gain is not.

---

## 5. Terrain horizon

For each radial sample: `angle = atan( (ground_elev − phase_centre) / range )`. The
controlling horizon on a bearing is the **maximum** angle over all ranges sampled there.

Phase centre reference: **107.1 m AMSL** (97.24 m ground + ~9.9 m mean height).

**Two real limitations:**

1. **Bare earth only.** USGS 3DEP is a bare-earth DEM. This site is surrounded by mature
   conifer. **Real obstruction toward any forested bearing is higher than computed.** The
   attempt to retrieve LiDAR canopy height failed (see `data/terrain-samples.json`).
2. **Sparse sampling.** Most bearings have a single sample at 500 m. A ridge between
   sampled ranges would be missed. Only the 30° and 250° radials were profiled properly
   (200 m / 500 m / 1 km / 2 km).

The 250° result depends entirely on this: at 500 m the ground is 59 m *below* the
antenna, but at 1000 m it has recovered to +0.24°. **The far side of the ravine sets the
horizon, not the ravine floor.** Sampling only to 500 m would have given a wrong answer.

### Foreground-slope gain

A downward foreground slope moves the reflection point downhill and far away, effectively
raising the antenna many wavelengths above the reflecting plane. Applied as a simple
subtraction from take-off angle:

| Bearing | Slope | Reduction applied |
|---|---|---|
| 210° / 250° | −8° | 8° |
| 310° | −4.8° | 5° |

**Confidence: LOW-MODERATE.** A rule of thumb, not a model. It predicts direction and
rough magnitude reliably; treat the exact degrees as indicative. This is the single
loosest assumption in the study and it materially affects the Australia and Asia
predictions.

---

## 6. Net coverage figures

```
net_dB = pattern_dB(best leg) + elevation_response_dB(effective arrival angle)
```

where effective arrival angle = typical arrival angle for that path length, shifted by
the foreground-slope reduction, and floored at the terrain horizon where it blocks.

Typical arrival angles by path length (conventional HF values, not computed):

| Path | 20 m arrival |
|---|---|
| 1,500–2,500 km | 20–30° |
| 2,500–4,500 km | 12–22° |
| 5,500–9,000 km | 6–14° |
| 9,000–13,000 km | 4–10° |
| 14,000+ km | 3–8° |

**Confidence: LOW-MODERATE.** This stacks four approximations. Use it to *rank*
directions and spot holes — that ranking is robust. Do not read the absolute dB as
predicted signal strength.

---

## 7. Aggregate scoring across regions

`tools/compare_options.py` reduces 25 per-region net figures to four numbers:

```
aggregate_dB = 10 · log10( mean over regions of 10^(net_dB/10) )
median_dB    = median net_dB
n_workable   = count of regions at or above −10 dB
n_holes      = count of regions below −15 dB
```

**`aggregate_dB` alone is a trap.** Mean *linear* power rewards concentrating radiation
into a few bearings rather than spreading it. Sloper S3 scores −5.98 dB against the
recommendation's −5.51 — apparently within half a dB — while reaching 14 regions instead
of 20, carrying 8 holes instead of 2, and putting an **−87 dB null on Perth**. Two strong
lobes outweigh a dozen nulls in that average.

This is not hypothetical: the first version of the bearing optimiser maximised
`aggregate_dB` and selected 178° for every sloper — a bearing that is also **17 m outside
the parcel**, because the scan had no geometric constraint either. Both faults were fixed:
the scan now rejects out-of-parcel supports and ranks on `n_workable` first,
`aggregate_dB` second.

**Report all four together.** Aggregate answers "how much total power"; workable and
median answer "how evenly spread".

### Parcel constraint

`inside_parcel()` tests the south and east boundary edges from
`data/parcel-1117200390.json` with a 5 m margin. The west and north boundaries are 70 m
and 100 m away and cannot bind for supports placed within 40 m east or south of the feed.

**A support inside the parcel is not necessarily buildable.** The scan knows nothing about
trees, the driveway, or the septic field. The `LAWN` sector (70–135°) restricts bearings to
ground verified clear from imagery; the `ANY` sector only guarantees the parcel. Options S1,
S2 and S3 select bearings near due north, which crosses the driveway turnaround and enters
dense forest — **unverified on the ground.**

## 9. Slant-wire model (T class) — the weakest link

Above roughly 30° of slope a wire stops behaving as a horizontal radiator over ground and
becomes a slant/vertical one. Sections 3 and 4 do not apply. `compare_options.py` switches
to a separate model when `slope_deg > 0.5`:

```
fv = sin²(slope)        vertical power fraction
fh = cos²(slope)        horizontal power fraction

total = fv · V(elev) + fh · H_pattern(azimuth) · H_elev(elev, h_avg)
```

- **Vertical part** is omnidirectional in azimuth and uses `VERT_RESPONSE_dB`, a stylized
  elevation curve for a vertical over average ground (σ 5 mS/m, ε_r 13).
- **Horizontal part** keeps the long-wire pattern of the wire's *ground projection*
  (`39.6 · cos θ`, with `n = 2·L_proj/λ`) and the section 4 ground-reflection response.

At 66° slope, `fv = 0.83` — the antenna is overwhelmingly vertically polarised, hence
omnidirectional, hence no nulls. That part is real physics.

**Confidence: LOW — lower than anything else in this study.**

`VERT_RESPONSE_dB` was traced from standard published curves, **not computed from soil
constants.** It bakes in roughly 4 dB of average-ground loss and a pseudo-Brewster rolloff
below ~12°. It sets the entire T-class result.

Two effects the model ignores entirely, either of which could cost several dB:

1. **Ground loss.** Vertical polarisation depends on soil under the radiator in a way a
   horizontal wire does not. This is a forested hillside with no radial system. An EFHW is
   a half-wave, so it does not *need* radials the way a quarter-wave vertical does — but if
   real loss is 8 dB rather than the 4 dB assumed, most of the T-class advantage
   disappears.
2. **Tree absorption.** A near-vertical wire running 140 ft alongside a wet conifer couples
   to a lossy dielectric along its whole length. The geometry helps — descending at 66° the
   wire clears the trunk within a few metres — but the top attachment sits in the canopy.

**Do not present T-class numbers as comparable in confidence to the horizontal options.**
The geometry (slope angles, support distances, current-maxima heights) is exact arithmetic
and can be trusted; the dB figures cannot.

### Mean current-maximum height

Reported for every option, and worth more than plain average height:

```
mean_imax_height = mean over {4.95, 14.85, 24.75, 34.65} m of height_at_wire(s)
```

Those are the 20 m current maxima on a 39.6 m EFHW. They are what actually radiates, so
their mean height predicts low-angle performance better than averaging the whole wire —
and it is pure arithmetic, **HIGH confidence**, independent of every model above. The
flat-top reaches 41 ft; T-APEX reaches 83 ft.

## 10. What would raise confidence

In rough order of value:

1. **Run NEC** (4nec2, EZNEC, xnec2c) — most valuable on the **T class**, where §9 is
   openly weak and the answer could move by several dB in either direction. Also replaces
   §3, §4 and §6 for the horizontal options and would settle the null depths.
2. **Sweep after installation** and compare against the predicted 1–2% resonance shift.
   This is the only real measurement available and it costs nothing.
3. **Get canopy height data** to correct the bare-earth horizon.
4. **On-air A/B** against a known reference — the only true validation.

Until at least (2) exists, **treat every performance number here as a design prediction,
not a result.**
