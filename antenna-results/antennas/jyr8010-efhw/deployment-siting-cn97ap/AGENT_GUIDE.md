# Agent guide — how to pick this study up

Read this first if you are an agent asked to extend, revise, or act on the CN97ap
deployment study.

---

## Read these four things, in this order

1. **`data/antenna-spec.json` → `THE_CORRECTION`** — 60 seconds, and it stops you
   repeating the session's biggest error.
2. **`README.md`** — findings and the final design.
3. **`METHOD.md`** — what each number is worth. Several are LOW confidence and labelled.
4. **`SESSION-LOG.md`** — five corrections were made mid-session. Know which conclusions
   are stale.

Then run the two generators, which need no dependencies:

```bash
D=antenna-results/antennas/jyr8010-efhw/deployment-siting-cn97ap
python3 $D/tools/site_geometry.py     # geometry, bearings, terrain horizon
python3 $D/tools/compare_options.py   # scores 10 topologies; writes CSVs + KML
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

**Never rank deployments on aggregate power alone.** It is mean *linear* power, so it
rewards concentrating radiation into a few bearings. A spiky straight wire can score
within 0.5 dB of a broad one while covering six fewer regions and nulling Perth by 87 dB.
Always read `n_workable` and `median_dB` beside it. An optimiser pointed at
`aggregate_dB` alone will hand you a bad antenna — that already happened once here.

**T-class dB figures are not comparable in confidence to the rest.** The slant model
(METHOD.md §9) uses a stylized vertical-over-ground curve traced from published charts,
not computed from soil constants, and ignores both ground loss on a forested hillside and
tree absorption along a 140 ft near-vertical wire. The *geometry* — slope angles, support
distances, current-maxima heights — is exact arithmetic and can be trusted. The dB cannot.
Never quote a T number beside an A number without that caveat.

**A support inside the parcel is not necessarily buildable.** `inside_parcel()` knows
about property lines and nothing else — not trees, the driveway, or the septic field.
Options S1/S2/S3 select bearings near due north that cross the driveway and enter forest.
Use the `LAWN` sector for anything you intend to actually build.

---

## Questions with settled answers — do not re-litigate

The operator answered these explicitly. Re-proposing them wastes their time.

| Question | Answer |
|---|---|
| Move the feed / run new coax? | **No.** Truly fixed at the start point. |
| Deploy from the front yard or driveway corner? | **No.** Nulls all of Asia. |
| Build a PVC mast? | **No.** Scored in full: −3.0 to −7.5 dB, 3–12 of 25 regions. A 39.6 m wire on a 24 ft mast slopes 6.2° and averages 17–24 ft. |
| Sloper off a *mast*? | **No.** At mast heights a 39.6 m "sloper" is a tilted flat-top. |
| Sloper off a *150 ft tree*? | **Yes — scores highest.** See the T class. T-APEX uses the existing apex tree at 143 ft, 25/25 regions, zero holes. But read §9 first: those dB figures are LOW confidence. |
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
   weakest models at once and settle the null depths.
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
