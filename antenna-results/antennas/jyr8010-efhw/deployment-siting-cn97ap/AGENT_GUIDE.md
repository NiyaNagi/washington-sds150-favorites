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

Then run the generator, which needs no dependencies:

```bash
python3 antenna-results/antennas/jyr8010-efhw/deployment-siting-cn97ap/tools/site_geometry.py
```

It recomputes every geometric result from raw inputs and is **authoritative** where it
disagrees with a stored CSV.

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

---

## Questions with settled answers — do not re-litigate

The operator answered these explicitly. Re-proposing them wastes their time.

| Question | Answer |
|---|---|
| Move the feed / run new coax? | **No.** Truly fixed at the start point. |
| Deploy from the front yard or driveway corner? | **No.** Nulls all of Asia. |
| Build a PVC mast? | **No.** 24 ft under a 50 ft apex buys 0.2 dB. |
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
