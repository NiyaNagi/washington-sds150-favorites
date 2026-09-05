# JYR8010 EFHW — deployment siting study, CN97ap

A site-specific deployment design for the JYR8010-150W at the operator's QTH near Fall
City, WA (grid **CN97ap**, King County parcel **1117200390**), optimised for DX to
Europe, the continental US, Australia, Japan, China and Russia.

> **This is analysis and prediction, not measurement.** No NEC model was run, no on-air
> testing was done, and **the antenna was not built as of 2026-09-05**. Every performance
> figure is a design prediction. See [`METHOD.md`](METHOD.md) for the confidence attached
> to each model.

**Agents: start with [`AGENT_GUIDE.md`](AGENT_GUIDE.md).**

Published field plan: <https://claude.ai/code/artifact/1128955c-5f0e-44c7-82a9-a08a9f9d2fa9>

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

---

## Alternatives scored

Fifteen topologies scored against the same 25 regions on 20 m, all sharing the fixed feed
point. Generated by [`tools/compare_options.py`](tools/compare_options.py).

### T class — tall slopers (height and parcel unconstrained)

With 150 ft trees available the sloper stops being a compromise. At 66° the wire is **83%
vertically polarised** — effectively an end-fed half-wave vertical: omnidirectional in
azimuth, with its current maxima far above anything a flat-top reaches.

| Key | Slope | Top | Support dist | Bearing T/M | Mean I-max ht | Aggregate | Workable | In parcel |
|---|---|---|---|---|---|---|---|---|
| T75 | 75° | 149 ft | 33.6 ft | 030 / 015 | 86.7 ft | **−4.30 dB** | **25/25** | yes |
| **T‑APEX** | **66°** | **143 ft** | **52.5 ft** | **082 / 067** | **83.4 ft** | **−4.57 dB** | **25/25** | yes |
| T60 | 60° | 137 ft | 65.0 ft | 033 / 018 | 80.3 ft | −4.64 dB | 25/25 | yes |
| T45 | 45° | 116 ft | 91.9 ft | 036 / 021 | 69.9 ft | −5.29 dB | 25/25 | yes |
| T30 | 30° | 89 ft | 112.5 ft | 101 / 086 | 56.5 ft | −5.36 dB | 25/25 | yes |

**None of the T options leave the parcel.** Height and footprint trade against each other —
at 75° the support is 34 ft from the feed. The tall sloper is simultaneously the
highest-scoring *and* most compact class. Only the short slopers, needing a ~130 ft ground
run, ever threatened the boundary.

**T‑APEX needs no new support.** The existing apex tree is 52 ft 6 in away; hang the wire at
143 ft in that same tree and √(39.6² − 16.01²) = 36.2 m of rise gives a 66.2° slope
automatically.

The T class trades **1–5 dB off the flat-top's best lobes to fill every one of its holes**:
Caribbean +11.6 dB, Florida +10.8, India +10.7, Novosibirsk +7.8; against Alaska −4.6,
US Northeast −1.4, VK2 −0.9. Worst region −8.7 dB versus the flat-top's −17.0.

> **These are the least trustworthy numbers here.** The T class rests on a stylized
> vertical-over-average-ground curve traced from published charts, not computed from soil
> constants, and it ignores two effects that could each cost several dB: **ground loss**
> under a vertically polarised radiator on a forested hillside with no radials, and
> **tree absorption** along a wire running 140 ft beside a wet conifer. This is where NEC
> would most change the answer. See [`METHOD.md`](METHOD.md) section 9.

### Horizontal classes (parcel-constrained)

| Key | Configuration | Avg ht | 20m TO | Aggregate | Workable | Holes | vs A |
|---|---|---|---|---|---|---|---|
| **A** | **Bent flat-top, 2 tree supports** | 41.6 ft | 24.7° | **−5.51 dB** | **20/25** | **2** | — |
| S3 | Straight sloper → 50 ft tree, due north | 37.0 ft | 28.0° | −5.98 dB | 14/25 | 8 | −0.5 |
| V1 | Inverted-V, **one** tree support, feed 24 ft | 33.2 ft | 31.6° | −6.57 dB | 18/25 | 4 | −1.1 |
| V2 | Inverted-V, one tree support, feed 10 ft | 30.0 ft | 35.4° | −7.14 dB | 17/25 | 4 | −1.6 |
| S4 | Straight sloper → 50 ft tree, over the lawn | 37.0 ft | 28.0° | −8.04 dB | 14/25 | 11 | −2.5 |
| S2 | Straight sloper → 24 ft PVC, due north | 24.0 ft | 46.4° | −8.53 dB | 12/25 | 10 | −3.0 |
| BASE | Original three-point plan | 22.5 ft | 50.6° | −9.04 dB | 12/25 | 6 | −3.5 |
| S5 | Straight sloper → 24 ft PVC, over the lawn | 24.0 ft | 46.4° | −9.69 dB | 10/25 | 11 | −4.2 |
| S1 | Straight sloper → 24 ft PVC, feed 10 ft | 17.0 ft | no lobe | −10.99 dB | 8/25 | 13 | −5.5 |
| V3 | Inverted-V on a 24 ft PVC mast | 17.0 ft | no lobe | −12.96 dB | 3/25 | 18 | −7.5 |

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
| [`SESSION-LOG.md`](SESSION-LOG.md) | Chronology and the nine mid-session corrections |
| [`INSULATORS.md`](INSULATORS.md) | Insulator selection, end-voltage working, specific products |
| [`tools/site_geometry.py`](tools/site_geometry.py) | Recomputes everything; stdlib only; **authoritative** |
| [`tools/compare_options.py`](tools/compare_options.py) | Scores all ten topologies; writes the two CSVs below and the KML |
| [`data/deployment-options.kml`](data/deployment-options.kml) | **Google Earth overlay** — every option, reference points, parcel line, bearing rays |
| [`data/option-comparison.csv`](data/option-comparison.csv) | Per-region net dB, all ten options (generated) |
| [`data/option-aggregate.csv`](data/option-aggregate.csv) | Aggregate, median, worst, workable, holes (generated) |
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
