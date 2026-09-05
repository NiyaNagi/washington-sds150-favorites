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

## Contents

| Path | What |
|---|---|
| [`AGENT_GUIDE.md`](AGENT_GUIDE.md) | **Start here.** Traps, settled questions, open items |
| [`METHOD.md`](METHOD.md) | Every formula and its confidence |
| [`SESSION-LOG.md`](SESSION-LOG.md) | Chronology and the five mid-session corrections |
| [`tools/site_geometry.py`](tools/site_geometry.py) | Recomputes everything; stdlib only; **authoritative** |
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
