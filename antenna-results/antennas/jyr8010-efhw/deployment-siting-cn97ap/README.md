# JYR8010 EFHW — deployment siting study, CN97ap

A site-specific deployment design for the JYR8010-150W at the operator's QTH near Fall
City, WA (grid **CN97ap**, King County parcel **1117200390**), optimised for DX to
Europe, the continental US, Australia, Japan, China and Russia.

> **This is analysis and prediction, not measurement.** NEC-2 was run on 2026-09-12 and
> overturned the analytic rankings — read the NEC section first. No on-air
> testing was done, and **none of the recommended designs had been built as of 2026-09-12**.
> What *is* up is a straight sloper the operator paced off with a GPS watch — scored below as
> [`CURRENT`](#what-is-up-now--the-as-built-sloper-current). Every performance figure is a
> design prediction. See [`METHOD.md`](METHOD.md) for the confidence attached
> to each model.

**Agents: start with [`AGENT_GUIDE.md`](AGENT_GUIDE.md).**

Published field plan: <https://claude.ai/code/artifact/1128955c-5f0e-44c7-82a9-a08a9f9d2fa9>
Published deployment guide: <https://claude.ai/code/artifact/0a8562b0-04ee-473f-9732-3a079305d96b>
Published lineup comparison ("Sixteen Wires on One Lot", including the roof feed): <https://claude.ai/code/artifact/eab86385-ffd8-44a3-b8e2-090b72026cb4>
(regenerate with `python tools/build_lineup_page.py <out.html>`, then publish to that URL)

---

## NEC-2 validation — every ranking below this section is superseded (2026-09-12)

The study's analytic models were checked against **NEC-2** (PyNEC 2.3.4, method of moments over
average ground) — `tools/nec_engine.py`, `tools/nec_validate.py`, `tools/nec_search.py`, details in
[`METHOD.md`](METHOD.md) §11. Published as "Every Wire on One Lot":
<https://claude.ai/code/artifact/eab86385-ffd8-44a3-b8e2-090b72026cb4>.

**NEC passed its checks** — dipole impedance and gain, take-off angles to 0.2°, and your
antenna's 80 m resonance within 1.2% of the 3.6056 MHz measured. **The study's long-wire formula
did not.** It is the centre-fed pattern; this antenna is end-fed, so on 40/20/15/10 m every lobe
was in the wrong place (20 m: 36° from the wire, not 57.5°). Across all 103 wires ever scored,
the old and NEC rankings correlate at **ρ = −0.07** — none of the earlier orderings survive.
Cell by cell the old models agree with NEC at r = 0.24 (bent-wire), 0.29 (slant) and **0.07
(hybrid L)**.

**NEC 40 + 20 + 15 m** (workable ≥ +1.02 dBi, the study's −5 dBi on NEC's ground-inclusive scale):

| NEC rank | Wire | Cells / 75 | dBi | Highest | Lot | Old rank |
|---|---|---|---|---|---|---|
| 1 | Roof feed (25 ft, assumed) up to a 69 ft support 122 ft out @ 150°M | 52 | +2.37 | 69 ft | **81 ft past the south line** | 62 |
| 2 | Roof feed up to a 62 ft support 125 ft out @ 60°M | 49 | +2.73 | 62 ft | **on the lot** | 82 |
| 3 | Roof feed up to a 71 ft support 121 ft out @ 260°M | 49 | +2.61 | 71 ft | inside setback | 51 |
| 9 | Transformer (10 ft) up to a 68 ft support 116 ft @ 145°M | 41 | +1.16 | 68 ft | 29 ft past the line | 71 |
| 11 | Transformer up to a 60 ft support 120 ft @ 250°M | 39 | +1.25 | 60 ft | on the lot | 76 |
| 12 | Roof inverted-V, apex 50 ft 57 ft @ 279°M | 38 | +1.05 | 50 ft | on the lot | 65 |
| 15 | **Transformer up to a 47 ft support 125 ft @ 270°M** | 38 | +1.71 | **47 ft** | on the lot | 93 |
| 16 | **F10‑A with leg 2 re-aimed to 60°M** | 37 | +1.25 | **50 ft** | on the lot | 85 |
| 22 | A (flat-top, 24 ft feed) | 35 | +1.58 | 50 ft | on the lot | 33 |
| 39 | **What is up now** | 30 | +0.66 | 45 ft | 2 ft past the line | 96 |
| 66 | F10‑A | 23 | +0.85 | 50 ft | on the lot | 45 |
| 74 | RB‑POST20 | 20 | +0.84 | 50 ft | on the lot | 46 |
| 91 | BASE | 16 | −0.18 | 35 ft | on the lot | 84 |

**What changed.** Straight wires reaching 45–70 ft now lead; the bent designs fall, because on
20 m their legs aim their lobes at the Americas and away from Europe and Asia. **The antenna up now
outscores both earlier recommendations on NEC.** The inverted-Ls that led yesterday drop to
#13 and below — the hybrid model had inflated them. With the transformer staying at 10 ft and no
throw above 55 ft, the best on the lot are a **straight sloper to 47 ft, 125 ft out at 270°M
(38/75)** and **F10‑A with its second leg swung to 60°M (37/75)**. On **40 + 20 m** straight roof
slopers lead again (35/50); the best easy-throw wires on the lot are S4 (24 ft feed, 26/50) and
the re-aimed F10‑A (25/50).

**Still true:** NEC models no trees, no house, no transformer, and no terrain beyond the arrival
angles. Moving the workable line ±2 dB drops rank correlation to ~0.8, so rows a few cells apart
are ties. The roof height is assumed. Every earlier table in this README is kept for the record.

### Every straight sloper off the roof — exhaustive NEC scan

A straight 39.6 m sloper from a fixed feed has two free parameters, bearing and run; the run fixes
the height. So the roof point was covered completely by
[`tools/nec_roof_sloper_scan.py`](tools/nec_roof_sloper_scan.py): **43,560 slopers** at every 1° ×
0.25 m (up to the 150 ft cap, down to an 8 ft end), 5,842 more refining the best of each category
to 0.25° × 0.05 m, the winners stress-tested against 45 rivals under 10 modelling changes, and
full grids repeated at 20 and 30 ft of roof height. 91 s on 32 cores. Results in
[`data/nec-roof-sloper-scan.json`](data/nec-roof-sloper-scan.json) and
[`data/nec-roof-sloper-grid.csv`](data/nec-roof-sloper-grid.csv); landscape in
[`imagery/nec_roof_sloper_landscape.png`](imagery/nec_roof_sloper_landscape.png).

| NEC 40+20+15 m, roof 25 ft | Bearing | Support out | Attach | Cells | dBi | Neighbours ±2° ±0.5 m | Lot |
|---|---|---|---|---|---|---|---|
| Best anywhere | 148.5°M | 123 ft | 67 ft | **54/75** | +2.49 | 50.2 (min 47) | 81 ft past the south line |
| **Best on the lot** (also clear of setback, ≤70 and ≤90 ft) | **59.2°M** | 125 ft | 60 ft | **49/75** | +2.73 | 47.0 (min 43) | clear of the setback |
| **Most robust on the lot** | **58.7°M** | 123 ft | 67 ft | 48/75 | +2.71 | **47.5 (min 46)** | clear of the setback |
| On the lot, easy throw (≤55 ft) | 59.0°M | 126 ft | 55 ft | 47/75 | +2.73 | 44.2 (min 38) | clear of the setback |
| Sloping down | 308.2°M | 130 ft | level at 25 ft | 35/75 | +1.90 | — | clear |

On **40 + 20 m** the best on the lot is 254.7°M, support 122 ft out at 70 ft (35/50, inside the
setback); clear of the setback, 71.7°M to 77 ft (33/50); easy-throw, 73.7°M to 55 ft (29/50).

**The answer for the roof is a sloper toward about 59° magnetic** — east-north-east over the house
and lawn to a support about 123–126 ft out, 55–67 ft up. It is not a spike: every neighbour within
±2° and ±0.5 m keeps 43–46+ cells; the same bearing wins at 20, 25 and 30 ft of roof (47 / 49 /
51 cells); and it stays in the top handful of rivals under every NEC modelling change. It moves if
the workable threshold moves (28 cells at +2 dB), like everything else. The earlier NEC search had
already found this wire (NR‑SL2, 49/75), so the search was not missing a better on-lot sloper.
**Sloping down off the roof does not work** — the best "down" wire is effectively level at 25 ft.
The support position is a computed point; no tree there has been checked for a 55–67 ft limb.

---

## The aerial photograph changed the picture

Retrieved 2026-09-05 from King County GIS (2025 EagleView orthomosaic, 6 in/px here) and
committed to [`imagery/`](imagery/README.md). It is the first hard evidence in this study of
what the wire actually flies over.

**62% of the antenna's ground path is over tree canopy** — 46%, 69% and 84% by span. The far
support and end tie-off are both inside the woods.

~~**And no open-ground route exists.**~~ **Corrected 2026-09-12 (correction 15).** That came
from a radial scan that stops at the first textured pixel, which near the house wall and beds
happens within a few metres on almost every bearing. The operator's as-built wire runs
**36.6 m straight down the lawn along the house at 139°T with only 4–5% of its ground path
over canopy**, in both ortho captures, and the photo agrees. The recommended *bent* designs
still cannot avoid the trees — they go through the apex tree by construction — but a
straight run down the lawn can.

> **No model in this study contains a tree-absorption term.** METHOD.md could only say the
> site was forested; this measures how much of the wire that omission applies to, and the
> answer is *most of it*. **Treat every dB figure here as an optimistic ceiling.** The
> post-installation NanoVNA sweep is the first real measurement and it costs nothing.

Tree *positions* are now known from the photograph. Tree *heights* still are not — four
canopy-height sources were tried and all failed; every height here remains operator-supplied.

---

## What is up now — the as-built sloper (`CURRENT`)

The operator paced the antenna that is actually hung with a Garmin watch on 2026-09-07 and
confirmed on 2026-09-12 that the walk **started under the elevated end and finished at the
transformer**, and that the wire is **one straight run**. The track itself
(`../50ft sloper antenna deployment.gpx`) is not committed.

| | |
|---|---|
| Feed | surveyed point, **10 ft** (the track's stop dwell landed 4–8 m away — wrist-GPS error) |
| Far end | **120 ft / 36.6 m at 138.9°T / 123.6°M**, about **45 ft** up — mean of the 8-point start dwell |
| Slope | **16.3°**; 38.1 m straight span, so **1.5 m (3.9%) of slack** — a hung wire, not a taut one |
| Average height | 27.5 ft (F10‑A 37.3 ft) |
| Over canopy | **4%** — the only scored layout that mostly avoids the trees |
| Parcel | track puts the end **0.5 m past the south line**; inside GPS error, so **not called either way** |

Scored with the **slant model** (METHOD.md §9, LOW confidence). The horizontal-wire model scores
the same wire worse (−5.15 dBi, 17/75), so the ranking is not an artefact of that choice.

| | **CURRENT** (up now) | BASE (original plan) | RB‑POST20 | F10‑A |
|---|---|---|---|---|
| 3-band rank, of 35 | **29** | 23 | 10 | 9 |
| 3-band aggregate | **−3.70 dBi** | −2.84 | −0.71 | −0.46 |
| Cells workable | **24/75** | 35/75 | 47/75 | 47/75 |
| Regions | 17/25 | 21/25 | 23/25 | 24/25 |
| Median / worst | −8.8 / **−58.9** | −5.9 / −26.2 | −3.1 / −23.1 | −2.5 / −26.2 |
| 80 m | −10.05 (0/25) | −12.46 (0) | −9.32 (1) | −8.68 (3) |
| 40 m | −8.71 (3) | −8.65 (2) | −5.78 (7) | −5.47 (8) |
| 20 m | −5.02 (6) | −3.74 (12) | −1.30 (18) | −0.67 (19) |
| 15 m | −0.81 (15) | +0.01 (21) | +1.88 (22) | +1.93 (20) |
| 10 m | +0.44 (15) | +0.87 (15) | +1.80 (15) | +2.47 (21) |

**It ranks below the original plan, not just below the recommendations**: −0.86 dB and 11 cells
against BASE, −2.99 dB and 23 cells against RB‑POST20. It sits alone in its tie band.

**Why.** A straight 39.6 m wire nulls off both ends on every band, and this one's axis is
**139° / 319°T**. One end aims at South America (132°T); the other at Beijing, Shanghai and
Vladivostok (310–318°T) — the same Asia null that eliminated the driveway layout in Phase 4. And
the first half of the wire is still climbing out of a 10 ft feed, so it averages 27.5 ft.

Per region, 3-band mean dBi against BASE — **worse:** South America −26.7, Dallas −12.8, Denver
−9.3, Beijing −5.7, Shanghai −5.1, UK −4.9, Central Europe −4.8. **Better:** Novosibirsk +3.8,
US Northeast +3.3, India +3.3, Hawaii +2.2, VK2 +2.2.

**GPS sensitivity.** Rotating the end ±10° and pulling it in up to 5 m gives **−3.93 to −2.56
dBi and 24–32 cells**; BASE's 35 is never reached. It cannot be further out than the track says:
at 45 ft the wire reaches only 38.1 m. The GPX point happens to be the *worst* cell count in that
grid, so the real antenna is probably a few cells better — and still in the bottom third. End
height 50 ft instead of 45: −3.20 dBi, 30/75. Full grid in
[`data/current-deployment-sensitivity.csv`](data/current-deployment-sensitivity.csv).

> **The canopy caveat cuts in this wire's favour.** It is 4% over canopy against 62% for F10‑A
> and 49% for RB‑POST20, and no model here charges anything for trees. The real gap is smaller
> than the table. How much smaller is not something this study can say; an on-air A/B or a
> NanoVNA sweep of both is.

---

## The lineup, and the best wires for 40 + 20 m

Asked 2026-09-12: draw what's up now, BASE, RB‑POST20, F10‑A, the top three slopers and the top
three inverted‑V‑or‑L deployments on the property and compare them; then find the best options
if only 40 m and 20 m mattered. Built by
[`tools/topology_search.py`](tools/topology_search.py) and
[`tools/build_lineup_page.py`](tools/build_lineup_page.py); pictures in
[`imagery/lineup_3band.jpg`](imagery/lineup_3band.jpg),
[`imagery/lineup_roof.jpg`](imagery/lineup_roof.jpg) and
[`imagery/lineup_40_20.jpg`](imagery/lineup_40_20.jpg).

**Limits the operator set:** feed at 10 ft for everything. Slopers may run off the lot (status
reported). Inverted‑Vs and inverted‑Ls stay on the lot. Ls have the vertical at the *far* end,
never at the feed.

| Wire | Geometry (bearings magnetic) | 3-band cells | 3-band dBi | Worst | 40+20 cells | Highest |
|---|---|---|---|---|---|---|
| Up now | straight, 45 ft end 120 ft @ 124° | 24/75 | −3.70 | −58.9 | 9/50 | 45 ft |
| BASE | original plan, apex 35 ft | 35/75 | −2.84 | −26.2 | 14/50 | 35 ft |
| RB‑POST20 | apex 50 ft, 20 ft post | 47/75 | −0.71 | −23.1 | 25/50 | 50 ft |
| F10‑A | three trees, none above 50 ft | 47/75 | −0.46 | −26.2 | 27/50 | 50 ft |
| Sloper 1 | 107 ft support 86 ft @ 189° — **15 ft past the south line** | 50/75 | −2.93 | −105.5 | 32/50 | 107 ft |
| Sloper 2 | = **F10‑G** (the search re-found it), 105 ft, 88 ft @ 10° | 49/75 | −3.05 | −44.9 | 35/50 | 105 ft |
| Sloper 3 | 87 ft support 105 ft @ 261° | 49/75 | −1.41 | −45.2 | 31/50 | 87 ft |
| Inverted‑L 1 | up to 53 ft 87 ft @ 256°, 33 ft hanging | **58/75** | −0.59 | −27.2 | 39/50 | 53 ft |
| Inverted‑L 3 | up to 56 ft 84 ft @ 237°, 34 ft hanging | 57/75 | −1.06 | −30.6 | 42/50 | 56 ft |
| Inverted‑L 2 | up to 52 ft 76 ft @ 153°, 43 ft hanging — inside setback | 56/75 | −1.19 | −51.8 | 40/50 | 52 ft |
| *best inverted‑V* | *apex 50 ft 52 ft @ 3°, leg 2 to 333°* | *50/75* | *−0.57* | *−33.0* | *28/50* | *50 ft* |

**All three V‑or‑L picks are inverted‑Ls, and they lead the entire study — which is exactly why
they are not a recommendation.** No model here could score an L before this search. Both legs
are scored on the §9 slant model (LOW, wrong once already) and combined as a union that ignores
leg interaction, at a 90° bend `endpoint_study.py` classes as OVERSTATED. The best V, on the
steadier bent-wire model, is 50/75. **Run NEC on one L before believing it.** The hanging end is
the ~1 kV voltage maximum, so an L also puts that end within reach of the ground.

**40 + 20 m only** (50 cells), every family re-searched, near-duplicates dropped:

| Wire | Geometry | 40+20 cells | 40+20 dBi | Worst | 3-band cells | Highest |
|---|---|---|---|---|---|---|
| 40/20 L1 | up to 46 ft 89 ft @ 237°, 34 ft hanging | **42/50** | −1.62 | −22.2 | 53/75 | 46 ft |
| 40/20 L2 | up to 56 ft 85 ft @ 15°, 33 ft hanging | 40/50 | −1.72 | −19.5 | 50/75 | 56 ft |
| 40/20 L3 | up to 52 ft 75 ft @ 155°, 43 ft hanging — inside setback | 40/50 | −1.46 | −46.6 | 56/75 | 52 ft |
| 40/20 sloper | 98 ft support 95 ft @ 153° — **17 ft past the south line** | 37/50 | −1.92 | −74.4 | 48/75 | 98 ft |
| F10‑A, leg 2 re-aimed | leg 2 to 20°M; nothing above 50 ft | 33/50 | −1.30 | −36.6 | 54/75 | 50 ft |

Dropping 15 m costs the recommendations most, because 15 m was their strongest band: RB‑POST20
25/50, F10‑A 27/50. **The best non‑L that needs only 50 ft throws is F10‑A with leg 2 re-aimed
north** — the same re-aim the study rejected on three bands for what it costs toward Hawaii and
VK (see "Moving the far end"). On 40 + 20 m that trade looks better; the region-by-region cost is
on the comparison page.

### Feeding from the roof

The operator marked a point on the house roof on the lineup map: **49 ft from the transformer at
210°M** (ENU −10.7, −10.5, read from their screenshot and scale-checked against two drawn points).
**Height assumed 25 ft**, the study's existing roof-feed figure; the page re-runs 20 and 30 ft.
Every family was searched from there, including wires sloping **down** off the house.

| Best of family (3-band) | From the transformer, 10 ft | From the roof, 25 ft |
|---|---|---|
| Sloper | 50/75, −2.93 dBi, worst −105.5, 107 ft (15 ft off the lot) | 50/75, −1.97 dBi, worst −55.1, 113 ft (**67 ft** off the lot) |
| Inverted‑V | 50/75, −0.57 dBi, worst −33.0 | **54/75, −0.02 dBi**, worst −33.6 — apex 50 ft 56 ft @ 334°, leg 2 to 3° |
| Inverted‑L (unvalidated) | 58/75, −0.59 dBi | 59/75, −0.75 dBi, worst −19.9 — up to 67 ft, 44 ft hanging |
| Sloping **down** | — | 34/75, −3.37 dBi, worst −114.7 — 25 ft to 21 ft, 130 ft @ 339° |

**Sloping down off the house doesn't work with this wire.** From 25 ft a 130 ft straight wire can
drop only 17 ft before its end is within reach, so it stays within 7.5° of level; the best one is a
low, near-flat wire at 34/75. **Sloping up from the roof is where the gain is**, and the one gain
on a model the study trusts is the **inverted‑V: +4 cells over the best transformer-fed V**, still
with a 50 ft throw. **That gain does not hinge on the assumed roof height**: the best roof V is
53, 54 and 55/75 at 20, 25 and 30 ft. Downward wires stay poor at any of them (24–36/75). The best
roof slopers put their support 67–78 ft past the south line. A roof
feed also puts the ~700 V RMS feed end, the transformer and the coax run beside gutters and house
wiring, which no model here knows about.

---

## The correction that reframes the parent report

The parent [`../README.md`](../README.md) says "The antenna is a 40-meter end-fed
half-wave design" and [`../data/measurement_metadata.json`](../data/measurement_metadata.json)
records `radiating_element_length_m: 40`.

**That means 40 metres of wire — it is an 80 m band EFHW, not a 40 m band antenna.**
Vendor documentation gives **39.6 m / 130 ft**. Confirmed three ways: the best measured
match is 80 m at 3.6056 MHz with Z = 49.8 + 4.3j (a resistive fundamental); a half-wave
at that frequency times 0.96 velocity factor is 39.9 m; and every other measured minimum
is a harmonic of it.

Consequences: the wire is **1.869 λ on 20 m** and **0.944 λ on 40 m**, so its 20 m
pattern is four lobes at 57.5° from the wire axis with deep nulls broadside and off the
ends, while 40 m and 80 m are effectively omnidirectional at this height.

---

## Headline findings

**1. The terrain matters more than the antenna.** The build site is flat to 0.6 m, but it
sits on a southwest shoulder. Ground rises 59 m in 500 m toward Europe and falls 59 m in
500 m toward Australia.

| Sector | Horizon | Verdict |
|---|---|---|
| NE 0–70° (Europe, Africa) | **+5.7° blocked** | worst |
| E/SE 90–160° (Americas) | −3.4° to +0.2° | clear |
| SW 200–270° (VK, ZL, KH6) | **−7.9° drop** | best |
| NW 300–330° (JA, BY, UA0, KL7) | **−4.8° drop** | very good |

Australia and East Asia are the achievable DX. **Europe is terrain-limited and no antenna
geometry on this lot fixes it.**

**2. A bent flat-top, not a sloper, V, or L.** A sloper or inverted-V averages 22.5 ft and
wastes the tree. An inverted-L wants a vertical section at the feed — which on an EFHW is
the high-voltage, low-current node where a vertical radiates poorly. The bend is what
makes Europe *and* Australia possible at all.

**3. Some pairs are arithmetically impossible.** On 20 m the lobes sit at axis ±57° and
±123°, so the only lobe separations available are 66°, 114° and 180°. Europe (30°) and
Sydney (245°) are 145° apart; Florida (109°) and Sydney are 136° apart. **Florida and the
Caribbean are an accepted hole** — work them on 15 m or 40 m.

**4. The fixed feed point beats the alternatives decisively.** Leg 1's bearing is set by
the apex tree at 82°, which puts a 20 m lobe at **319°** — covering Beijing, Alaska,
Vladivostok and Shanghai. A driveway run at ~320° puts that whole cluster in its axial
null and fails 13 of 24 target areas versus 3.

**5. A short mast is not worth building.** A 24 ft PVC mast under a 50 ft apex buys
**0.2 dB** — it holds the wire where the catenary would put it anyway. Rope into a tree
is cheaper and 4 dB better.

---

## Final design

Bent flat-top, four supports. Bearings True / **Magnetic** (declination +15.3°E).

| # | Support | Height | From feed | Bearing | Coordinates |
|---|---|---|---|---|---|
| 1 | Feed + transformer | 24 ft | — | — | 47°38'02.61"N 121°59'47.73"W |
| 2 | Apex tree | 50 ft | 52 ft 6 in | 082° / **067°** | 47°38'02.68"N 121°59'46.97"W |
| 3 | Far support | 50 ft | 83 ft 9 in | 102° / **087°** | 47°38'02.43"N 121°59'46.54"W |
| 4 | End tie-off | 30 ft | 107 ft 1 in | 109° / **093°** | 47°38'02.27"N 121°59'46.25"W |

| Span | Wire | Ground run | Bearing | Slope |
|---|---|---|---|---|
| Feed → apex | 17.86 m / 58 ft 7 in | 16.01 m | 082° / **067°** | 26.3° up |
| Apex → far support | 11.84 m / 38 ft 10 in | 11.84 m | 130° / **115°** | level |
| Far support → end | 9.90 m / 32 ft 6 in | 7.80 m | 130° / **115°** | 38° down |

Support 3 is deliberately at **29.7 m of wire — the 40 m and 15 m current maximum**. The
apex lands at 17.86 m, beside the 19.8 m *voltage* maximum, so it needs the best
insulator on the antenna.

Add 2–3% slack; expect 8–12 in of mid-span sag.

**Predicted:** 41.6 ft average height. Take-off 20 m **24.7°**, 15 m **16.2°**, 10 m
**12.0°** — less roughly 8° toward Australia and 5° toward Asia. About **+4.9 dB** at 10°
on 20 m versus a low sloper. Verified 59 ft clear of the south property line and 56 ft
clear of the east.

---

## Predicted coverage (20 m)

Full table in [`data/coverage-predictions.csv`](data/coverage-predictions.csv).

**Strong (better than −5 dB):** Alaska −0.2 · Vladivostok −3.0 · **Australia VK2/3/4
−3.1** · Beijing −3.1 · Hawaii −3.2 · US Northeast −3.4 · Moscow −4.7 · Central Europe
−4.7 · China −4.7 · Kyiv −4.8

**Workable (−5 to −8):** US Midwest · UK · SoCal · Japan · Australia VK6 · Denver/Dallas

**Marginal (−8 to −12):** South America · New Zealand · Iberia · Novosibirsk

**Holes (worse than −13):** US Southeast/Florida · South Africa · Caribbean · India

On 40 m and 80 m the antenna is near-omnidirectional high-angle — ideal for continental
US with no skip zone, and orientation is irrelevant there.

**Band-by-band, this reorders the priorities.** See
[`data/option-band-aggregate.csv`](data/option-band-aggregate.csv). The short version: the
recommended flat-top is a **15 m and 10 m antenna first** (+2.1 and +2.3 dBi, 20–21 regions
of 25), a competent 20 m antenna (−0.2 dBi, 20 regions), a mediocre 40 m one (−4.8 dBi,
9 regions, 56° take-off) and a regional-only 80 m one (−7.8 dBi, 3 regions, no lobe).
**Florida and the Caribbean — the accepted 20 m hole — come back on the higher bands.**
Caribbean goes −10.7 dBi on 20 m → −2.7 on 15 m → **+1.8 on 10 m**; US Southeast −9.6 →
−2.3 → **+1.4**. The hole is a 20 m hole, not an antenna hole. Work them up, not around.

---

## Bands this antenna actually has

Five, not "80–10 m continuous". The wire is resonant only where it is an integer number of
half-waves:

| Band | λ | L/λ | n | Main lobe from axis | Peak directivity |
|---|---|---|---|---|---|
| 80m | 84.45 m | 0.469 | 1 | 90° broadside | 2.15 dBi |
| 40m | 42.22 m | 0.938 | 2 | 90° broadside | 3.80 dBi |
| 20m | 21.19 m | 1.869 | 4 | 57.5° | 5.30 dBi |
| 15m | 14.14 m | 2.800 | 6 | 48.2° | 6.40 dBi |
| 10m | 10.52 m | 3.764 | 8 | ~40° | 7.10 dBi |

**30 m, 17 m and 12 m are missing by arithmetic, not omission.** The odd harmonics land near
10.65, 17.75 and 24.85 MHz — outside all three allocations. They need a tuner and are not
modelled. That is why the three-band aggregate below is **40 + 20 + 15 m**: 17 m would
otherwise be the natural third DX band, and this antenna does not have it.

---

## Alternatives scored — three-band ranking

23 topologies × five bands × 25 regions, as of Phase 10. Generated by
[`tools/compare_options.py`](tools/compare_options.py), which now scores **35** — the F10, RB and
CURRENT classes are tabled in their own sections, and the tool's ranking block has all of them
in one list.

Ranked on **workable band×region cells first**, regions reachable on at least one band
second, mean power **last** — for the reason in [`METHOD.md`](METHOD.md) §7. Horizontal
rules mark **ties on the primary key**; inside a rule band the ordering is not meaningful,
so read the whole row.

**`anch` and `highest` are deployment effort, not performance**: elevated attachments other
than the feed, and the tallest of them. Throw difficulty: *easy* ≤55 ft, *hard* ≤90,
*very hard* ≤130, *climb* above that.

| # | Key | Configuration | 3-band dBi | Cells | Regions | Worst | anch | highest | throw |
|---|---|---|---|---|---|---|---|---|---|
| 1 | G‑ROOF | Best 1-support sloper, **roof feed**, 47.4°, 63°T | −2.41 | 49/75 | 25/25 | −74.0 | 1 | 121 ft | very hard |
| 2 | G‑FEED | Best 1-support sloper, existing feed, 47.8°, 50°T | −2.45 | 49/75 | 25/25 | −67.1 | 1 | 120 ft | very hard |
| **3** | **A** | **Bent flat-top, 2 tree supports** | **−0.16** | **49/75** | 24/25 | **−25.4** | 3 | **50 ft** | **easy** |
| 4 | T30 | Tall sloper 30°, 176°T — **support 39 ft off the lot** | −0.63 | 49/75 | 24/25 | −45.4 | 1 | 89 ft | hard |
| 5 | T45 | Tall sloper 45°, 143°T — 10 ft from the line | −2.62 | 49/75 | 24/25 | −60.9 | 1 | 116 ft | very hard |
| — | | | | | | | | | |
| 6 | C‑BACK‑X | Locked to backyard bearing 155°T, **8 ft off the lot** | −2.02 | 48/75 | 24/25 | −48.9 | 1 | 110 ft | very hard |
| — | | | | | | | | | |
| 7 | T60 | Tall sloper 60°, 337°T | −4.15 | 44/75 | 25/25 | −67.6 | 1 | 137 ft | climb |
| 8 | C‑FRONT | Locked to front-yard bearing 326°T, 46.8° | −3.05 | 44/75 | 24/25 | −98.4 | 1 | 119 ft | very hard |
| **9** | **V1** | **Inverted-V, one 50 ft support** | **−0.88** | 44/75 | 23/25 | −27.1 | 1 | **50 ft** | **easy** |
| — | | | | | | | | | |
| 10 | V2 | Inverted-V, one 50 ft support, feed 10 ft | −1.31 | 40/75 | 23/25 | −27.9 | 1 | 50 ft | easy |
| — | | | | | | | | | |
| 11 | RF‑APEX | Roof feed → apex tree, 60.8° | −4.11 | 39/75 | 25/25 | −69.0 | 1 | 138 ft | climb |
| 12 | C‑BACK | Locked to backyard bearing 155°T, **on the lot** | −4.53 | 39/75 | 25/25 | −62.9 | 1 | 135 ft | climb |
| — | | | | | | | | | |
| 13 | S3 | Straight sloper → 50 ft tree, due north | −1.22 | 38/75 | 19/25 | −81.9 | 1 | 50 ft | easy |
| 14 | T‑APEX | Tall sloper 66°, existing apex tree | −4.78 | 37/75 | 24/25 | −58.4 | 1 | 143 ft | climb |
| 15 | BASE | Original three-point plan | −2.84 | 35/75 | 21/25 | −26.2 | 1 | 35 ft | easy |
| 16 | S4 | Straight sloper → 50 ft tree, over the lawn | −2.31 | 32/75 | 17/25 | −116.1 | 1 | 50 ft | easy |
| 17 | S2 | Straight sloper → 24 ft PVC, due north | −3.49 | 29/75 | 19/25 | −58.7 | 1 | 24 ft | easy |
| 18 | K‑BACK | Sloper to the **backyard-corner tree**, 71.9° | −5.61 | 26/75 | 23/25 | −87.4 | 1 | 148 ft | climb |
| 19 | T75 | Tall sloper 75°, 105°T | −5.79 | 26/75 | 20/25 | −85.8 | 1 | 149 ft | climb |
| 20 | S5 | Straight sloper → 24 ft PVC, over the lawn | −4.06 | 23/75 | 15/25 | −68.2 | 1 | 24 ft | easy |
| 21 | S1 | Straight sloper → 24 ft PVC, feed 10 ft | −5.93 | 22/75 | 16/25 | −88.1 | 1 | 24 ft | easy |
| 22 | K‑FRONT | Sloper to the **front-yard-corner tree**, 79.7° | −8.07 | 11/75 | 11/25 | −64.1 | 1 | 152 ft | climb |
| 23 | V3 | Inverted-V on a 24 ft PVC mast | −7.99 | 7/75 | 5/25 | −109.1 | 1 | 24 ft | easy |

**The recommendation survives, and the deployment column explains why it should.** Option A
sits in the top tie band, leads it on mean power by 1.9 dB, and has by far the best
worst-case of anything in the study — **−25.4 dBi against G‑FEED's −67.1**. Deep nulls are
what every single-wire option pays for its height.

---

## The garden posts change the answer

The operator marked a strip on the plan view where posts are already staked and PVC can be
attached. Georeferenced from that annotation against the four support markers — a similarity
fit with a **6 cm worst residual on the ground**:

| Corner | ENU (m) | From feed | Bearing T / **M** |
|---|---|---|---|
| 1 | (23.07, −5.62) | 77.9 ft | 104° / **88°** |
| 2 | (20.30, −7.39) | 70.9 ft | 110° / **95°** |
| 3 | (31.99, −20.88) | 125.3 ft | 123° / **108°** |
| 4 | (34.73, −17.85) | 128.1 ft | 117° / **102°** |

A strip **11–13 ft wide and 55–59 ft long**, long axis 139°T, centroid 100 ft from the feed
at **100° magnetic**. Entirely inside the parcel.

### RB‑1TREE — one rope throw instead of two, and a better worst case

| | RB‑1TREE (30 ft post) | F10‑A | A (24 ft feed) |
|---|---|---|---|
| 3-band | **−0.40 dBi** | −0.46 | −0.16 |
| Cells | **48/75** | 47/75 | 49/75 |
| Regions | 23/25 | 24/25 | 24/25 |
| **Worst region** | **−22.5** | −26.2 | −25.4 |
| **Anchors** | **2** — one is a post | 3 | 3 |
| 15 m | **+2.12 dBi, 22/25** | +1.93, 20/25 | +2.06, 20/25 |

**Apex tree at 50 ft, then straight to a post in the strip.** It beats F10‑A on aggregate,
on workable cells and on worst case — which is **the best worst-case figure of any option in
the study** — while needing one fewer rope throw. It gives up one region. Its 15 m figure is
the best anywhere here.

### Post height matters gently — 20 ft is the sweet spot

| Post | 3-band | Cells | Worst | 15 m | Post position |
|---|---|---|---|---|---|
| 10 ft | −1.09 | 44/75 | −23.8 | +1.56 | 86.6 ft @ **100°M** |
| 16 ft | −0.85 | 46/75 | −23.3 | +1.76 | 88.7 ft @ **101°M** |
| **20 ft** | **−0.71** | **47/75** | **−23.1** | +1.88 | **90.9 ft @ 101°M** |
| 24 ft | −0.58 | 47/75 | −22.8 | +1.98 | 93.1 ft @ 102°M |
| 30 ft | −0.40 | 48/75 | −22.5 | +2.11 | 95.4 ft @ 102°M |
| 36 ft | −0.26 | 49/75 | −22.1 | +2.20 | 96.8 ft @ 102°M |

**0.83 dB across 26 ft of post** — about 0.32 dB per 10 ft, and the position barely moves.
**A 20 ft post already matches F10‑A's 47 cells and beats its worst case**, with one fewer
throw. Going to 30 ft buys 0.31 dB more; going to 36 ft matches option A at a 24 ft feed.
Build what stands up safely on a garden stake and stop there.

Two scored options exist so the recommendation and the geometry cannot drift apart:
**`RB-POST20`** is the recommended 20 ft build, **`RB-1TREE`** is the optimiser's best over
all heights (which always picks the tallest allowed, 30 ft).

### Which stake — pick the stake first, then the height

The wire length pins the post's distance from the apex tree, so **only about 7 ft of the
strip's 59 ft length is usable at any one post height**, at the north-west end nearest the
house. Raising the post walks that band further along the strip — which is the useful
freedom when the stakes are already in the ground.

| Post height | Reachable band from the feed | Best point | 3-band | Cells |
|---|---|---|---|---|
| 16 ft | 88.4 – 95.5 ft | 88.7 ft @ **101°M** | −0.85 | 46/75 |
| **20 ft** | **90.6 – 97.6 ft** | **90.9 ft @ 101°M** | **−0.71** | **47/75** |
| 24 ft | 92.8 – 99.0 ft | 93.5 ft @ **102°M** | −0.58 | 47/75 |
| 30 ft | 94.6 – 101.1 ft | 94.6 ft @ **102°M** | −0.40 | 48/75 |

Roughly **2 ft of extra post buys 2 ft further out**. Within each band the near end always
scores better — about 0.2 dB and 5 cells across the 7 ft — so where two stakes both work,
take the one closer to the house.

### RB‑NOTREE — the zero-rope-throw floor

A single span from the feed to a 30 ft post at the strip's far corner, 127.6 ft at
**102°M**: **−6.05 dBi, 11/75 cells, 8 of 25 regions.** That is poor, and it is the entire
antenna reachable from the ground with no line in any tree. Worth knowing the floor exists;
not worth choosing while the apex tree is available.

---

## The 10 ft feed category

The operator has to leave the transformer at 10 ft for now. Every other class here assumes
it can be lifted to 24 ft, so the 10 ft cases get their own family (`F10-*`) rather than
being mixed in.

| Key | Configuration | 3-band dBi | Cells | Regions | Worst | anch | highest | vs A |
|---|---|---|---|---|---|---|---|---|
| F10‑G | Best 1-support sloper, 47.2°, 25°T | −3.05 | **49/75** | **25/25** | −44.9 | 1 | 105 ft | −2.89 |
| **F10‑A** | **Option A geometry, feed at 10 ft** | **−0.46** | 47/75 | 24/25 | **−26.2** | 3 | **50 ft** | **−0.30** |
| F10‑CF | Locked to front-yard bearing 326°T | −3.24 | 42/75 | 24/25 | −48.7 | 1 | 106 ft | −3.08 |
| F10‑V | Inverted-V, one 50 ft support (= V2) | −1.31 | 40/75 | 23/25 | −27.9 | 1 | 50 ft | −1.15 |
| F10‑CB | Locked to backyard bearing 155°T | −4.51 | 39/75 | 25/25 | −56.8 | 1 | 122 ft | −4.35 |
| F10‑APEX | Sloper to the apex tree, 66.2° | −4.49 | 37/75 | 24/25 | −59.5 | 1 | 129 ft | −4.34 |
| F10‑BACK | Sloper to the backyard-corner tree | −5.67 | 27/75 | 22/25 | −89.3 | 1 | 134 ft | −5.51 |
| F10‑FRONT | Sloper to the front-yard-corner tree | −7.63 | 14/75 | 13/25 | −73.0 | 1 | 138 ft | −7.47 |
| *A (24 ft)* | *the benchmark* | *−0.16* | *49/75* | *24/25* | *−25.4* | *3* | *50 ft* | *—* |

### The answer: F10‑A, and the 10 ft feed costs almost nothing

**Lowering the feed from 24 ft to 10 ft costs option A just 0.30 dB and 2 cells.** That is
the whole penalty. The feed is a voltage maximum — a **current null** — so its own height
barely matters; what costs is that it drags the first part of the wire down with it.

F10‑G edges F10‑A on the primary key, 49 cells to 47, and **loses on everything else**:

| | F10‑A | F10‑G |
|---|---|---|
| 3-band aggregate | **−0.46 dBi** | −3.05 dBi |
| Worst region | **−26.2** | −44.9 |
| Highest anchor | **50 ft** — easy throw | 105 ft — very hard |
| 15 m / 10 m | **+1.93 / +2.47 dBi** | −2.79 / −1.15 dBi |

Two extra cells do not buy 2.6 dB, an 18 dB worse null, and a 105 ft rope throw. **F10‑A is
the recommendation while the feed stays at 10 ft.**

### What changes on the ground versus the 24 ft plan

Only support 3 moves. Leg 1 gets longer as the feed drops (17.86 → 20.12 m of wire), so the
29.7 m current maximum arrives sooner along leg 2:

| Support | Option A (24 ft feed) | F10‑A (10 ft feed) |
|---|---|---|
| Feed | 24 ft | **10 ft** |
| Apex tree | 50 ft, 52 ft 6 in @ 082°T | unchanged |
| **Far support** | 50 ft, **83 ft 9 in @ 102°T** | 50 ft, **77 ft 2 in @ 100°T** |
| End tie-off | 30 ft @ 109°T | 30 ft, same bearing |

Average height falls 41.6 → 37.3 ft; mean 20 m current-maximum height 41.0 → 37.5 ft.

Per band, F10‑A against A at 24 ft: 80 m **−0.85**, 40 m −0.67, 20 m −0.46, 15 m −0.13,
10 m **+0.21**. **The higher the band, the less the feed height matters** — and on 10 m
lowering the feed is very slightly *better*, because at 37 ft rather than 42 ft average the
wire's ground-reflection lobe sits closer to the low angles that band wants. Regions
workable are unchanged on 80 m, 15 m and 10 m, and drop by one each on 40 m and 20 m.

---

## Is option A actually harder to deploy? No — it is the easiest thing that works

The operator's premise was that a sloper would be easier to put up than the four-support
flat-top. **The arithmetic says the opposite,** and the reason is structural.

A straight sloper has no free parameters. Once you choose how far away the support is, the
wire length fixes everything else:

```
rise = √(39.6² − run²)
```

So a sloper is forced onto a curve. Make it shallow enough to perform and the anchor climbs:

| Run | Slope | Attachment | Throw | Performance |
|---|---|---|---|---|
| 23 ft (front-yard tree) | 79.7° | **152 ft** | climb | 11/75 — worst but one |
| 40 ft (backyard tree) | 71.9° | 148 ft | climb | 26/75 |
| 52 ft (apex tree) | 66.2° | 143 ft | climb | 37/75 |
| 87 ft (**G‑FEED**) | 47.8° | 120 ft | very hard | **49/75** |
| 127 ft | 11.6° | 50 ft | easy | 38/75 (this is S3/S4) |

**Every single-support option that matches option A needs a 116–120 ft anchor.** The ones
with easy 50 ft anchors are 11–17 cells worse, because at 50 ft the whole wire is low.

Option A needs three attachments — but **the highest is 50 ft**, which is a routine
slingshot-and-weight afternoon. That is not a coincidence. The bend is precisely what lets
the wire carry its current maxima at useful height without any single support being high:
the flat-top gets height *in the middle of the wire*, where the current maxima are, instead
of having to buy it all at one end.

**If you want fewer ropes, the honest answer is V1, not a sloper.** One 50 ft support, same
easy throw, costs 5 cells and 0.72 dB against A. Every sloper that beats V1 needs an anchor
more than twice as high.

---

## Slopers constrained by the yard corners

Two questions here, and they have different answers.

### Rotation locked to a corner bearing (support distance free)

| Key | Bearing | Support | Slope | Top | 3-band | Cells | Parcel |
|---|---|---|---|---|---|---|---|
| C‑BACK | 155°T backyard | 66.9 ft | 59.0° | 135 ft | −4.53 | 39/75 | in |
| **C‑BACK‑X** | 155°T backyard | 97.8 ft | 41.2° | 110 ft | **−2.02** | **48/75** | **8 ft off the lot** |
| C‑FRONT | 326°T front yard | 88.9 ft | 46.8° | 119 ft | −3.05 | 44/75 | in |

**On the backyard heading the property line is the whole story.** Keep the support on the
lot and it has to come in to 66.9 ft, which forces 59° and a 135 ft attachment — 39/75.
Let it run 8 ft past the south line and it drops to 41.2°, a 110 ft attachment, and
**48/75 cells with 2.5 dB more power**. Eight feet of boundary is worth nine cells here.

The front-yard heading has room and does not have that problem: C‑FRONT reaches 88.9 ft
entirely inside the lot. It is the better of the two constrained directions, and the second
best on-the-lot sloper in the study after G‑FEED.

For reference, **T30 rotated onto the backyard bearing** — the specific case asked about —
would need its support 112.5 ft out at 155°T, which lands about **20 ft past the south
line**, worse than C‑BACK‑X's 8 ft.

### Supports *at* the corners themselves

| Key | Corner | Distance | Forced slope | Attachment | 3-band | Cells |
|---|---|---|---|---|---|---|
| K‑BACK | backyard | 40.3 ft | 71.9° | 148 ft | −5.61 | 26/75 |
| K‑FRONT | front yard | 23.2 ft | 79.7° | **152 ft** | −8.07 | 11/75 |

**Both corner trees are too close to the feed to be useful sloper supports.** At 23 and 40
ft out, the forced slopes are 80° and 72° — deep in the over-long-vertical regime where a
39.6 m wire is 1.7 λ tall on 20 m and loses its low-angle lobe. K‑FRONT also needs a
**152 ft** attachment, over the 150 ft cap. It is the second-worst option in the study.

A good sloper wants its support around **85–95 ft out**. Neither corner is anywhere near
that; the useful distance is out in the yard or the treeline, not at the house.

### And the roof feed, scored as a real candidate

G‑ROOF is the fully optimised sloper from a roof feed: **−2.41 dBi, 49/75** against
G‑FEED's **−2.45, 49/75**. **0.04 dB.** Even with azimuth and distance re-optimised around
the new feed position, moving the transformer to the roof is a wash — consistent with the
0.02 dB found at matched slope in [`tools/endpoint_study.py`](tools/endpoint_study.py).
RF‑APEX (roof feed → the existing apex tree) is 39/75, better than T‑APEX's 37/75 only
because the extra 3.3 m of run softens 66.2° to 60.8°.

### The T class reversed when the model was fixed

The previous revision had T‑APEX leading every option at −4.57 dB on 20 m. **That was
wrong.** The slant model treated a 66° wire as omnidirectional with a band-independent
elevation curve. Rewritten to evaluate the long-wire pattern at the true 3-D angle from the
wire axis, band by band:

| Band | A (flat-top) | T30 | T‑APEX (66°) |
|---|---|---|---|
| 80m | −7.83 dBi, 3/25 | −5.01, 10/25 | **−5.10, 14/25** |
| 40m | −4.80 dBi, 9/25 | −3.89, 12/25 | −5.53, 12/25 |
| 20m | **−0.21 dBi, 20/25** | +0.81, 21/25 | −4.89, 12/25 |
| 15m | **+2.06 dBi, 20/25** | −0.09, 16/25 | −4.05, 13/25 |
| 10m | **+2.26 dBi, 21/25** | −1.41, 10/25 | −7.64, 6/25 |

The physics is simple once stated: at 66° a 39.6 m wire has a **1.7 λ vertical extent on
20 m and 3.4 λ on 10 m.** Anything that tall in the vertical plane breaks into lobes and
loses its low-angle response — the same reason a vertical longer than ~0.64 λ is a poor DX
antenna. The tall sloper wins where the wire is short in wavelengths and height dominates
(80 m, 40 m) and loses badly where it is not.

**T‑APEX is now the best 80 m option in the study**, at 14/25 regions against the flat-top's
3/25 — a genuine 2.7 dB and eleven regions. If 80 m DX ever becomes the goal, it is the
answer. For 40/20/15 m it is not.

**Two of the T options now leave the parcel** — and this changed when the three-band scan
moved their bearings. An earlier revision of this file said none of them did; that was true
of the 20 m-optimised bearings and is **no longer true**:

| Key | Bearing | Support distance | Parcel |
|---|---|---|---|
| T30 | 176°T | 112.5 ft | **OUT — about 38 ft past the south line** |
| T45 | 143°T | 91.9 ft | on the lot, but only ~10 ft from the south line |
| T60 | 337°T | 65.0 ft | in |
| T75 | 105°T | 33.6 ft | in |
| T‑APEX | 082°T | 52.5 ft | in |

That matters, because **T30 is the second-ranked option** and it is not buildable on your
land. `tools/compare_options.py` prints the status per support and has always had it right;
the prose here was stale. Height and footprint still trade against each other — at 75° the
support is 34 ft from the feed — but the shallow slopers need a long ground run and the
three-band scan happens to point them south, at the nearest boundary.

**T‑APEX still needs no new support**: the existing apex tree is 52 ft 6 in away and
√(39.6² − 16.01²) = 36.2 m of rise gives 66.2° automatically at a 143 ft attachment.

> **T-class numbers remain the least trustworthy here** — see [`METHOD.md`](METHOD.md) §9.
> The free-space pattern term is now exact, but ground loss on a forested hillside with no
> radials and absorption along 140 ft of wire beside a wet conifer are both unmodelled, and
> either could cost several dB. Watch the `peak_elev` column: it jumps between 14° and 67°
> across adjacent slopes and bands. That is not code noise — it is the real multi-lobed
> pattern of a long slant wire, and it means T performance is **unstable against small
> geometry changes** in a way a flat-top's is not.

### Per-band picture for the recommendation

| Band | Aggregate | Regions | Mean I-max ht | Take-off |
|---|---|---|---|---|
| 80m | −7.83 dBi | 3/25 | 50.0 ft | zenith (h < λ/4) — NVIS/regional only |
| 40m | −4.80 dBi | 9/25 | 38.5 ft | 56° |
| 20m | −0.21 dBi | 20/25 | 41.0 ft | 24.7° |
| 15m | +2.06 dBi | 20/25 | 40.2 ft | 16.2° |
| 10m | **+2.26 dBi** | **21/25** | 41.0 ft | 12.0° |

**The flat-top's best DX bands are 15 m and 10 m, not 20 m.** Height in wavelengths is the
whole story. At 41.6 ft (12.68 m) the wire sits **1.21 λ up on 10 m, 0.90 λ on 15 m, 0.60 λ
on 20 m, 0.30 λ on 40 m and only 0.15 λ on 80 m.** Below the quarter-wave threshold no
distinct lobe forms and the pattern peaks straight up, which is exactly what happens on
80 m. **80 m off this antenna at this height is a regional band. Do not expect DX on it.**

> **None of this says a band is open.** These are antenna figures. 10 m scores best and is
> also the band most often shut. Read the table as "where the antenna puts power", not
> "what you will work".

### Moving the far end — height, azimuth, or onto the roof

Scored separately by [`tools/endpoint_study.py`](tools/endpoint_study.py), because they are
three different questions with three different answers. **All three are no.**

**Raising the end is worth 0.35 dB across 50 ft of height.**

| End tie-off | 10 ft | 20 ft | 30 ft | 40 ft | 50 ft | 60 ft |
|---|---|---|---|---|---|---|
| 3-band | −0.32 | −0.23 | **−0.16** | −0.09 | −0.03 | +0.03 |

Both ends of an EFHW are voltage maxima — **current nulls**. Only current maxima radiate,
and the tail (29.7–39.6 m of wire) holds 0 of 1 on 80 m, 1 of 2 on 40 m, 1 of 4 on 20 m,
2 of 6 on 15 m, 2 of 8 on 10 m. Support 3 was deliberately placed *at* the 29.7 m current
maximum so that the end would not have to matter. It doesn't.

**Re-aiming leg 2 is worth at most +0.5 dB, and it is the wrong trade.** The best azimuth
with a bend the model can honestly score is 35°T (+0.37 dBi, 55/75 cells against 130°T's
−0.16 and 49/75). What it buys and what it costs, in 3-band mean dBi:

| Gains | | Losses | |
|---|---|---|---|
| US Southeast | +5.0 | Hawaii | **−7.8** |
| Caribbean | +4.7 | South Africa | −6.2 |
| India | +3.3 | Australia VK2 | −2.9 |
| Denver / Dallas | +2.9 / +2.4 | Moscow | −2.1 |

Every loser sits in or near the **210–270° sector — the only bearing with a −7.9°
foreground downslope**, and the reason this site can work VK at all. Every winner
**already returns on 15 m and 10 m** without moving anything. Half a dB is not worth
spending the site's one real advantage.

> Two scan traps worth knowing. The raw top-ranked azimuth was 215°T — a **133° bend**,
> two near-antiparallel legs whose cancellation §3 cannot model. And the pattern is
> front/back symmetric, so 35°T and 215°T score identically while being entirely different
> physical wires. Filter on bend angle before quoting a bearing.

**The roof is 2.6–4.1 dB worse than the tree, and it is not close.**

| High support | Distance from feed | Height | Avg wire height | 3-band | Cells |
|---|---|---|---|---|---|
| **Apex tree (current)** | **52.5 ft** | **50 ft** | **41.6 ft** | **−0.16** | **49/75** |
| House ridge | 24 ft | 20 ft | 16 ft | −4.24 | 31/75 |
| House ridge | 24 ft | 25 ft | 19 ft | −3.25 | 35/75 |
| House ridge | 24 ft | 30 ft | 21 ft | −2.72 | 38/75 |
| House ridge | 24 ft | 40 ft | 27 ft | −1.17 | 44/75 |

The ridge is only ~24 ft from the feed, so barely 19% of the wire is in the first leg and
the other 81% slopes away from a low point. Height in wavelengths sets low-angle gain, and
the roof is both too close and too low to supply it. Even a fictional 40 ft ridge loses.

*(Ridge position is estimated from the operator's own corner marks — feed = NE corner,
backyard corner 12.28 m at 155°T, front yard corner 7.08 m at 326°T — giving a long axis of
155/335°T and a ridge ~7.3 m from the feed. The half-width is assumed. The conclusion is
insensitive to it: the ridge would have to move 30 ft away **and** gain 25 ft to compete.)*

**Putting the FEED on the roof and sloping up to a tree is worth 0.02 dB.** This is the
inverse of the case above and a different antenna, so it is scored separately.

| Feed | Slope | Top | 3-band | Cells |
|---|---|---|---|---|
| Current feed, 24 ft | 30° | 89 ft | −0.62 | 48/75 |
| Roof ridge, 25 ft | 30° | 90 ft | −0.60 | 48/75 |
| Current feed, 24 ft | 45° | 116 ft | −2.20 | 48/75 |
| Roof ridge, 25 ft | 45° | 117 ft | −2.21 | 48/75 |
| Current feed, 24 ft | 60° | 137 ft | −4.16 | 44/75 |
| Roof ridge, 25 ft | 60° | 138 ft | −4.15 | 44/75 |

**Both ends of an EFHW are current nulls, so neither end's height is where the gain lives.**
Raising the roof feed 20 → 30 ft moves the 3-band figure by 0.06 dB, and slightly the wrong
way. The one real effect of the move is that the apex tree goes from 16.0 m to 19.3 m away,
which softens the forced slope from 66.2° to 60.8° and is worth +0.67 dB — and a further
support buys far more of that for nothing.

Note what this geometry already is: **an upward sloper off the fixed feed is the T class.**
T‑APEX is literally "feed 24 ft, slope up 66.2° to the apex tree at 143 ft". With a fixed
39.6 m wire the rise is forced by the run, `rise = √(39.6² − run²)`, so choosing the support
distance chooses the slope — and there is no third variable to tune.

**Anchoring the end on the roof is not scored, deliberately.** Feed→apex is 17.9 m, leaving
21.7 m to fold back to a point ~7 m from the feed — a hairpin whose legs are near
antiparallel, which §3 cannot model, so no number here would be honest. It is also wrong on
its own terms: the end is the **voltage maximum, ~1 kV RMS at 150 W**
([`INSULATORS.md`](INSULATORS.md)), and that does not belong on a roof beside gutters,
flashing and house wiring.

### Horizontal classes, 20 m only (unchanged, for continuity)

| Key | Configuration | Avg ht | 20m TO | Aggregate | Workable | Holes | vs A |
|---|---|---|---|---|---|---|---|
| **A** | **Bent flat-top, 2 tree supports** | 41.6 ft | 24.7° | **−5.51 dB** | **20/25** | **2** | — |
| S3 | Straight sloper → 50 ft tree, due north | 37.0 ft | 28.0° | −5.98 dB | 14/25 | 8 | −0.5 |
| V1 | Inverted-V, **one** tree support, feed 24 ft | 33.2 ft | 31.6° | −6.57 dB | 19/25 | 4 | −1.1 |
| V2 | Inverted-V, one tree support, feed 10 ft | 30.0 ft | 35.4° | −7.14 dB | 17/25 | 4 | −1.6 |
| S4 | Straight sloper → 50 ft tree, over the lawn | 37.0 ft | 28.0° | −8.04 dB | 14/25 | 11 | −2.5 |
| S2 | Straight sloper → 24 ft PVC, due north | 24.0 ft | 46.4° | −8.53 dB | 12/25 | 9 | −3.0 |
| BASE | Original three-point plan | 22.5 ft | 50.6° | −9.04 dB | 12/25 | 6 | −3.5 |
| S5 | Straight sloper → 24 ft PVC, over the lawn | 24.0 ft | 46.4° | −9.69 dB | 10/25 | 11 | −4.2 |
| S1 | Straight sloper → 24 ft PVC, feed 10 ft | 17.0 ft | no lobe | −10.98 dB | 9/25 | 12 | −5.5 |
| V3 | Inverted-V on a 24 ft PVC mast | 17.0 ft | no lobe | −12.96 dB | 3/25 | 18 | −7.5 |

Every per-region **dB value** here is bit-identical to the previous revision except S1's
column, whose scanned bearing moved 359° → 358°. The *counts* moved slightly on several
options (V1 18→19 workable, S2 10→9 holes, S1 8→9 and 13→12) because the threshold was
restated on the absolute scale: −5.0 dBi is −10.3 dB relative on 20 m, against a flat −10.0
before. Nothing about the ordering changed.

**A 39.6 m wire cannot form a steep sloper at these heights.** Feed 10 ft to a 24 ft mast
gives a **6.2°** slope over a 39.4 m run; 24 ft to a 50 ft tree gives **11.6°**. A genuine
30° sloper would need 19.8 m (65 ft) of drop. Every "sloper" here is a slightly tilted
flat-top whose performance is set by average height — which is why PVC collapses. At 17 ft
average the wire is 0.24 λ on 20 m, below the quarter-wave threshold, so there is no
distinct lobe and the pattern peaks at zenith.

**The inverted-V is the honest simplification.** V1 keeps both leg bearings — so it keeps
the bend and its null-filling — drops support 3, and costs 1.1 dB and two regions.

> **Do not rank on aggregate alone.** Aggregate is mean *linear* power, so it rewards
> concentrating power rather than spreading it. S3 scores 0.5 dB behind the recommendation
> yet reaches 14 regions instead of 20, has 8 holes instead of 2, and drops an **−87 dB
> null on Perth**. `n_workable` and `median_dB` capture spread; the bearing scan in
> `compare_options.py` ranks on regions-workable first for exactly this reason.

## Contents

| Path | What |
|---|---|
| [`AGENT_GUIDE.md`](AGENT_GUIDE.md) | **Start here.** Traps, settled questions, open items |
| [`METHOD.md`](METHOD.md) | Every formula and its confidence |
| [`SESSION-LOG.md`](SESSION-LOG.md) | Chronology and the sixteen corrections |
| [`INSULATORS.md`](INSULATORS.md) | Insulator selection, end-voltage working, specific products |
| [`tools/site_geometry.py`](tools/site_geometry.py) | Recomputes everything; stdlib only; **authoritative** |
| [`tools/compare_options.py`](tools/compare_options.py) | Scores 35 topologies × 5 bands, including the as-built CURRENT; writes the CSVs below and the KML |
| [`tools/nec_engine.py`](tools/nec_engine.py) | **NEC-2 scoring** (PyNEC): support points → 39.6 m wire → gain toward every region, ranked the study's way |
| [`tools/nec_validate.py`](tools/nec_validate.py) | Engine benchmarks, resonances, the pattern-formula check, NEC sensitivity → `data/nec-validation.json`, `data/nec-resonances.json` |
| [`tools/nec_search.py`](tools/nec_search.py) | **The ranking now in force**: re-runs the searches on NEC and scores all 103 wires → `data/nec-scores.json`, `nec-ranking.csv`, `nec-ranking.kml` |
| [`tools/nec_roof_sloper_scan.py`](tools/nec_roof_sloper_scan.py) | **Exhaustive** NEC scan of every straight sloper off the roof point, with robustness, stress test and 20/30 ft roof heights |
| [`tools/build_nec_page.py`](tools/build_nec_page.py) | "Every Wire on One Lot" page and `imagery/nec_*.jpg` |
| [`tools/topology_search.py`](tools/topology_search.py) | Searches slopers, inverted‑Vs and inverted‑Ls (feed 10 ft) on the 3-band and 40 + 20 m metrics; adds the hybrid L model |
| [`tools/build_lineup_page.py`](tools/build_lineup_page.py) | Builds the lineup comparison page and the two annotated aerial JPEGs |
| [`data/topology-search.csv`](data/topology-search.csv) / [`.kml`](data/topology-search.kml) | Search results: geometry, both metrics, every band, model and parcel status (generated) |
| [`data/current-deployment-sensitivity.csv`](data/current-deployment-sensitivity.csv) | CURRENT's score with the GPS end point rotated/pulled in and the end height varied (generated) |
| [`tools/endpoint_study.py`](tools/endpoint_study.py) | End height, end azimuth, and roof-support sensitivity — why the end stays where it is |
| [`data/deployment-options.kml`](data/deployment-options.kml) | **Google Earth overlay** — every option with its per-band table, ordered by 3-band rank; reference points, parcel line, bearing rays |
| [`data/option-comparison-multiband.csv`](data/option-comparison-multiband.csv) | **Per-region net dB for every band**, long format (generated) |
| [`data/option-band-aggregate.csv`](data/option-band-aggregate.csv) | **Per option per band**: aggregate dB and dBi, regions, I-max height, peak elevation (generated) |
| [`data/option-comparison.csv`](data/option-comparison.csv) | Per-region net dB, 20 m only, kept for continuity (generated) |
| [`data/option-aggregate.csv`](data/option-aggregate.csv) | Headline table: 20 m columns + the 3-band ranking (generated) |
| [`data/antenna-spec.json`](data/antenna-spec.json) | Verified spec, the length correction, current/voltage nodes |
| [`data/site-points.json`](data/site-points.json) | Every operator point + derived ENU + hazards |
| [`data/site-points.csv`](data/site-points.csv) | Same, flat |
| [`data/terrain-samples.csv`](data/terrain-samples.csv) | All 18 USGS 3DEP queries |
| [`data/terrain-samples.json`](data/terrain-samples.json) | Same + horizon model + the failed canopy query |
| [`data/parcel-1117200390.json`](data/parcel-1117200390.json) | King County parcel ring + clearance check |
| [`data/target-bearings.csv`](data/target-bearings.csv) | 27 great-circle bearings and distances |
| [`data/pattern-model-tables.csv`](data/pattern-model-tables.csv) | Long-wire pattern for n = 2, 4, 6 |
| [`data/coverage-predictions.csv`](data/coverage-predictions.csv) | Per-target scores for all three options |
| [`data/deployment-options.json`](data/deployment-options.json) | Every option considered and why rejected |
| [`data/final-design.json`](data/final-design.json) | Machine-readable build spec |
| [`imagery/README.md`](imagery/README.md) | Georeferencing record; **source screenshots are missing** |

---

## Reproduce

```bash
python3 antenna-results/antennas/jyr8010-efhw/deployment-siting-cn97ap/tools/site_geometry.py
```

No dependencies. Where a stored CSV and the script disagree, **the script wins** — see
the reconciliation note in `data/coverage-predictions.csv`.

## Sources

- King County GIS, [`Property/KingCo_Parcels` MapServer](https://gismaps.kingcounty.gov/arcgis/rest/services/Property/KingCo_Parcels/MapServer) — parcel geometry
- USGS 3DEP [Elevation Point Query Service](https://epqs.nationalmap.gov/v1/json) — 1 m bare-earth DEM
- [JYR8010-150W listing](https://www.amazon.com/JYR8010-150W-Half-Antenna-Shortwave-Radio/dp/B0DBDCNVZD) and [manual](https://manuals.plus/asin/B0DBDCNVZD)
- Operator-supplied coordinates and Google Earth captures (imagery dated 2026-06-06)
- Parent report [`../README.md`](../README.md); sloper reference [`../../gowenic-efhw/README.md`](../../gowenic-efhw/README.md)
