# Agent guide — how to pick this study up

Read this first if you are an agent asked to extend, revise, or act on the CN97ap
deployment study.

---

## Read these four things, in this order

1. **`data/antenna-spec.json` → `THE_CORRECTION`** — 60 seconds, and it stops you
   repeating the session's biggest error.
2. **`README.md`** — findings and the final design.
3. **`METHOD.md`** — what each number is worth. Several are LOW confidence and labelled.
4. **`SESSION-LOG.md`** — **fourteen** corrections were made across the session. Know which
   conclusions are stale. Correction 10 reversed the T class outright; correction 12 put
   T30's support 39 ft off the lot.

Then run the two generators, which need no dependencies:

```bash
D=antenna-results/antennas/jyr8010-efhw/deployment-siting-cn97ap
python3 $D/tools/site_geometry.py     # geometry, bearings, terrain horizon
python3 $D/tools/compare_options.py   # 23 topologies x 5 bands; 4 CSVs + KML
python3 $D/tools/endpoint_study.py    # end height / azimuth / roof sensitivity
```

They recompute every result from raw inputs and are **authoritative** where they disagree
with a stored CSV.

---

## Traps that already caught someone

**The antenna is 39.6 m of wire — an 80 m band EFHW.** The parent report says "40-meter
end-fed half-wave design" and `radiating_element_length_m: 40`. That means *40 metres of
wire*, not the 40 m band. If you find yourself computing a half-wave for 7.15 MHz, stop.

**20 m lobes are at 57.5° from the wire axis, not 35°.** The `1 − 0.371/n` formula is for
*terminated travelling-wave* long wires. This is a *resonant standing-wave* wire:
`F(θ) = |[cos(nπ/2·cos θ) − cos(nπ/2)]/sin θ|`.

**The feed is the high-voltage end.** On an EFHW both ends are voltage maxima and the
current maxima are at 9.9 m and 29.7 m of wire. Do not propose an inverted-L with a
vertical section at the feed — it radiates poorly there. Support 3 sits at 29.7 m
deliberately.

**Terrain data is bare earth.** The site is surrounded by mature conifer that is not
modelled. Every horizon angle is optimistic toward forested bearings.

**Coordinates are precise to ±0.3 m.** They were given to 0.01 arcsecond. Millimetre
figures in the data files are arithmetic, not accuracy.

**Confirm north-up before georeferencing any screenshot.** The first capture in this
session was rotated ~90° and briefly produced a contradiction.

**A straight sloper has no free parameters, and that is the key structural fact.** Once the
support distance is chosen the wire length fixes everything: `rise = √(39.6² − run²)`. So
slope, attachment height and performance all move together on one curve, and "make it
shallower" always means "put the anchor further away", never "lower the anchor". This is
why every good sloper here needs a 110–120 ft attachment and why the corner trees (23 and
40 ft out) cannot work.

**Score deployment effort, not just dB.** `Option.n_anchors` / `.max_anchor_ft` /
`.throw_class` exist because an earlier revision compared a 3-anchor flat-top against
1-anchor slopers on gain alone and let the operator believe the flat-top was the harder
build. It is the easier one: three 50 ft throws beat one 120 ft throw. **Fewer anchors is
not less work.**

**Filter azimuth recommendations by bend angle before you quote them.** METHOD.md §3
scores a bent wire as the *union* of two lobe sets — it ignores relative phase between the
legs and overstates how cleanly they add, and that gets worse as the bend sharpens. The
first run of `endpoint_study.py` ranked leg 2 at 215°T first; that is a **133° bend**, two
near-antiparallel legs whose cancellation the model cannot see. Anything past ~110° is
reported as NOT VALID rather than ranked. Note also that the pattern is front/back
symmetric, so the scan cannot distinguish a bearing from its reciprocal — 35°T and 215°T
score identically and are completely different physical wires.

**Never rank deployments on aggregate power alone.** It is mean *linear* power, so it
rewards concentrating radiation into a few bearings. A spiky straight wire can score
within 0.5 dB of a broad one while covering six fewer regions and nulling Perth by 87 dB.
Always read `n_workable` and `median_dB` beside it. An optimiser pointed at
`aggregate_dB` alone will hand you a bad antenna — that already happened once here.

**T-class dB figures are not comparable in confidence to the rest.** The slant model
(METHOD.md §9) still relies on a stylized average-ground loss curve and ignores both ground
loss on a forested hillside without radials and tree absorption along a 140 ft near-vertical
wire. The *geometry* — slope angles, support distances, current-maxima heights — is exact
arithmetic and can be trusted. The dB cannot. Never quote a T number beside an A number
without that caveat.

**Any T-class dB figure from before 2026-09-05 is stale.** The slant model was rewritten
(correction 10) and the result reversed: T-APEX went from leading every option at −4.57 dB
on 20 m to −10.19 dB and 8th of 15. The old model treated a 66° wire as omnidirectional
with a band-independent elevation curve; it is neither. If you find "83% vertically
polarised — omnidirectional, hence no nulls" anywhere, that framing is superseded.

**There are exactly five bands: 80/40/20/15/10 m.** 30 m, 17 m and 12 m are not harmonics
of a 39.6 m wire — the odd harmonics land near 10.65, 17.75 and 24.85 MHz, outside all
three allocations. If asked to score 17 m, say why it cannot be scored rather than
inventing a number. See METHOD.md §8.

**Two dB scales, and mixing them is an error.** `net_dB` is normalised to each wire's own
peak lobe — valid *within* a band only. `net_dBi` adds the band's peak directivity and is
the only scale that may be compared *across* bands. A 4 λ wire has ~5 dB more peak gain
than a half-wave one, so comparing raw `net_dB` across bands under-credits the high bands
by exactly that much. `option-comparison.csv` and `aggregate_dB` are the normalised scale;
everything with `dBi` in the name is absolute.

**Antenna gain is not band availability.** Nothing in this study knows whether a band is
open. 10 m scores best for the flat-top and is also the band most often shut. Do not let a
table of dBi become a prediction of what the operator will work.

**Re-check parcel status after ANY bearing change, and do not trust prose about it.**
The three-band re-scan moved T30 to 176°T and T45 to 143°T, which put **T30's support 39 ft
off the lot** and T45's inside the 5 m setback — while a sentence saying "none of the T
options leave the parcel", true of the previous bearings, survived into the same commit.
`compare_options.py` now prints a dedicated **SUPPORTS THAT ARE NOT ON THE PARCEL** block
that distinguishes "off the lot" from "on the lot but inside the setback". Read that block,
not the README, when it matters.

**A support inside the parcel is not necessarily buildable.** `inside_parcel()` knows
about property lines and nothing else — not trees, the driveway, or the septic field.
Options S1/S2/S3 select bearings near due north that cross the driveway and enter forest.
Use the `LAWN` sector for anything you intend to actually build.

---

## Questions with settled answers — do not re-litigate

The operator answered these explicitly. Re-proposing them wastes their time.

| Question | Answer |
|---|---|
| Move the feed / run new coax? | **Superseded.** Was "truly fixed"; on 2026-09-05 the operator asked for the roof ridge to be scored as a real candidate. It is (G‑ROOF, RF‑APEX) and it is a **0.04 dB** wash, so the answer is unchanged in practice. The front-yard and driveway corners remain rejected outright. |
| Deploy from the front yard or driveway corner? | **No.** Nulls all of Asia. |
| Build a PVC mast? | **No.** Scored in full: −3.0 to −7.5 dB, 3–12 of 25 regions. A 39.6 m wire on a 24 ft mast slopes 6.2° and averages 17–24 ft. |
| Sloper off a *mast*? | **No.** At mast heights a 39.6 m "sloper" is a tilted flat-top. |
| Is option A hard to deploy? | **No — it is the easiest thing that works.** Three attachments but the highest is **50 ft**, a routine throw. Every one-support sloper that matches it needs **116–120 ft**. The bend is what buys height in the middle of the wire, where the current maxima are, without any one support being high. |
| Want fewer ropes than A? | **V1, not a sloper.** One 50 ft support, costs 5 cells and 0.72 dB. Every sloper that beats V1 needs an anchor more than twice as high. |
| Best one-support sloper? | **G‑FEED** — 47.8° at 50°T, support 87 ft out, 120 ft attachment, 49/75 cells, on the lot. Ties A's cell count; loses 2.3 dB and has a −67 dBi worst case against A's −25. |
| Sloper to a corner tree? | **No.** The corner trees are 23 ft (front) and 40 ft (back) from the feed, forcing 79.7° and 71.9°. K‑FRONT needs a **152 ft** attachment and scores 11/75 — second worst in the study. A good sloper wants its support **85–95 ft out**. |
| Sloper rotated onto a corner bearing? | **Front yard yes, backyard no.** C‑FRONT (326°T) reaches 88.9 ft inside the lot, 44/75. C‑BACK (155°T) is boundary-limited to 66.9 ft → 59° → 39/75; letting it run **8 ft past the south line** gets 48/75 and +2.5 dB. |
| Roof feed as a real candidate? | **Scored, and it is a wash.** G‑ROOF −2.41 vs G‑FEED −2.45 with azimuth and distance re-optimised. 0.04 dB for relocating the transformer. |
| Sloper off a *150 ft tree*? | **Only for 80 m.** T-APEX is the best 80 m option in the study (−5.10 dBi, 14/25 vs the flat-top's 3/25) and 8th of 15 on the 40/20/15 m aggregate. The earlier "scores highest" answer came from the broken slant model. |
| Raise the far END for more height? | **No — 0.35 dB from 10 ft to 60 ft.** The end is a voltage maximum, i.e. a current null, and the far support already sits at the 29.7 m current maximum so the tail carries almost nothing. Run `tools/endpoint_study.py`. |
| Re-aim leg 2 / move the end elsewhere? | **No.** The best gently-bent azimuth (35°T) is worth +0.5 dB and 6 of 75 cells, and pays for it with Hawaii −7.8, South Africa −6.2, VK2 −2.9 — the 210–270° sector that holds the site's only −7.9° downslope. What it buys (Florida, Caribbean, Denver) returns on 15/10 m for free. |
| Use the house ROOF as the high support (wire sloping DOWN)? | **No — 2.6 to 4.1 dB worse.** The ridge is ~24 ft from the feed against the tree's 52.5 ft, and 20–30 ft up against 50 ft. Average height collapses 41.6 → 16–27 ft. Even a 40 ft ridge loses 1.0 dB. |
| Put the FEED on the roof, sloping UP to a tree? | **No — 0.02 dB at matched slope.** Different question from the row above, and scored separately in §4 of `endpoint_study.py`. The feed is the *other* voltage maximum, so its height buys as little as the end's. Note this geometry already exists as the **T class** — T‑APEX is "feed 24 ft, up 66.2° to the apex tree at 143 ft". |
| Anchor the END on the roof? | **No, and do not score it.** It needs a near-antiparallel hairpin that METHOD.md §3 cannot model, and the end is the ~1 kV RMS voltage maximum — see `INSULATORS.md`. Wrong on both counts. |
| Which bands does it have? | **80/40/20/15/10 only.** Not 30/17/12 — see the trap above. |
| Best band for the recommended flat-top? | **15 m and 10 m** (+2.1 / +2.3 dBi, 20–21 of 25 regions), then 20 m. 80 m is regional-only at 41 ft. |
| Inverted-V off one point? | **Viable.** V1 costs 1.1 dB and 2 regions vs the flat-top. Take it if two rope throws is one too many. |
| Support height available? | **150 ft trees.** The 50 ft figure in option A is a conservative throw-line assumption, not a limit. |
| Trade to option B for Florida/Caribbean? | **No.** Accepted as a hole; work them on 15/40 m. |
| Support height available? | **50 ft+ at both**, by throw line. |
| Inverted-V, sloper, or L? | **None.** Bent flat-top — reasons in `data/deployment-options.json`. |

---

## Open items, roughly by value

1. **Post-installation NanoVNA sweep.** Not built as of 2026-09-05. This is the only real
   measurement available and it costs nothing. Predicted shift is 1–2% down (≈3.55 /
   7.10 / 14.10 MHz). File under `../measurements/` following the parent report's
   conventions, then link it from this README.
2. **Verify the two unknowns** in `data/site-points.json` → `hazards_and_unknowns`: the
   cylindrical object near leg 1, and whether a usable 50 ft limb exists at the far
   support.
3. **Run NEC** on the actual bent geometry over real ground. Would replace the three
   weakest models at once and settle the null depths. **Highest value on the T class**,
   where §9 has now been wrong once already and the answer moved by 6 dB when it was fixed.
   A model that has flipped its own conclusion is not one to build from.
4. **Save the source screenshots** — see `imagery/README.md`. They were chat attachments
   and could not be written to disk.
5. **Canopy height.** The USDA ImageServer returned HTTP 500; alternatives are listed in
   `data/terrain-samples.json` → `failed_queries`.

---

## If the operator changes a constraint

| Change | What to redo |
|---|---|
| Different support height | `tools/site_geometry.py` constants `APEX_H` / `FAR_H`; height ladder in `data/deployment-options.json` already covers 40–60 ft |
| Different leg 2 bearing | `LEG2_BEARING` in the script; then re-score coverage |
| Feed becomes movable | Reopens option C — but re-check the Asia null first, it is the reason C lost |
| Different antenna | Everything. Lobe angles, current maxima and wire budget are all length-dependent. |
| Priorities change (e.g. Florida matters) | `data/deployment-options.json` has option B scored and the three-leg idea sketched |

---

## Working conventions in this repo

- `antennas/<name>/` per antenna, with `README.md`, `data/`, `measurements/`, `charts/`
- Sub-studies live in a named subdirectory — this one mirrors
  `../../gowenic-efhw/installed-office-feed/`
- Measurement directories hold preserved S1P/JSON/NPZ and are treated as immutable
- Reports state their limitations plainly; invalid captures are preserved and labelled,
  not deleted

**Keep that last habit.** This study is prediction, not measurement, and says so in every
file. Do not let a later summary quietly upgrade it.
