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

23 topologies × five bands × 25 regions. Generated by
[`tools/compare_options.py`](tools/compare_options.py).

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
| [`SESSION-LOG.md`](SESSION-LOG.md) | Chronology and the fourteen mid-session corrections |
| [`INSULATORS.md`](INSULATORS.md) | Insulator selection, end-voltage working, specific products |
| [`tools/site_geometry.py`](tools/site_geometry.py) | Recomputes everything; stdlib only; **authoritative** |
| [`tools/compare_options.py`](tools/compare_options.py) | Scores 23 topologies × 5 bands; writes the four CSVs below and the KML |
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
