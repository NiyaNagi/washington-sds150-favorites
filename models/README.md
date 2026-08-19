# SDS150 mounts

Two ways to hold a Uniden SDS150 by its belt-clip stud:

- **Visor mount** — a parametric replacement for the mounting block of the
  "Slim Radio mount". The visor clamp, the C-shape that grips the sun
  visor, is reused unchanged from the original model; only the block the
  radio attaches to has been redesigned.
- **Peak Design Capture bracket** — a low-profile plate with a 1/4"-20
  tripod socket. See [docs/pd-capture-bracket.md](../docs/pd-capture-bracket.md).

Both capture the stud with the same keyhole, defined once in
`sds150_stud.scad` so the two cannot drift apart.

For the method behind these models — how they are structured, every helper
script, the verification approach, and a full table of measured dimensions
— see [docs/modelling-method.md](../docs/modelling-method.md). Start there
if you are building a new part rather than adjusting an existing one.

## Files

### Shared

| File | What it is |
| --- | --- |
| `sds150_stud.scad` | The stud, its clearances, and the keyhole. Edit fit here — it applies to both mounts. |

### Visor mount

| File | What it is |
| --- | --- |
| `sds150_mount_common.scad` | Parameters and geometry for the visor mount. |
| `sds150_visor_mount_lengthwise.scad` | Variant: slot runs along the radio's length |
| `sds150_visor_mount_crosswise.scad` | Variant: slot runs across the radio's width |
| `sds150_visor_mount_*.stl` / `.3mf` | Ready-to-slice exports |
| `coupon_*.stl` | Small test prints of just the socket, for dialling in the fit |
| `slim_radio_mount_source.stl` | The original mount, unmodified. The clamp is cut from this at render time. |
| `fit_check.scad` | Test harness used by `scripts/cad/fit_check.py`. Not printable. |
| `Slim_Radio_mount.3mf` | The original Bambu project. Untouched, kept for reference. |
| `SDS100_Belt_Clip.stl` | Reference part. Untouched. |

### Peak Design bracket

| File | What it is |
| --- | --- |
| `sds150_pd_bracket.scad` | Parameters and geometry for the bracket. |
| `sds150_pd_bracket_self_tap.stl` / `.3mf` | **Start here.** Screw cuts its own thread. |
| `sds150_pd_bracket_insert.stl` / `.3mf` | For a 1/4"-20 heat-set brass insert. Strongest. |
| `sds150_pd_bracket_nut.stl` / `.3mf` | For a captive 1/4"-20 hex nut. |
| `pd_fit_check.scad` | Test harness used by `scripts/cad/pd_fit_check.py`. Not printable. |

## How the original is reused

The source mount is a C-clamp with a lower jaw at Z −19.8…−14.9 and an upper
jaw at Z 3.0…8.0, with the old radio block stacked on top of that upper jaw.
The new model imports the source whole and trims everything above **Z = 8.0**,
keeping the entire clamp and discarding only the block.

That number matters. Trimming at Z = 3.0 looks plausible but is the
*underside* of the upper jaw — it removes a jaw of the clamp completely and
leaves a feathered, zero-thickness edge along the cut. `arm_top_z` is
documented in the SCAD file for that reason.

The new block is then grown straight off that jaw, using the jaw's own outline
— taken by projecting the mesh, so it follows the original's rounded corners
exactly. Its sides are flush with the clamp, and its top edge is rolled over
on a 3mm radius, so it reads as a continuation of the part rather than a slab
bolted on. A 0.4mm inset stops it oversailing the jaw, which would leave a
knife edge along the joint.

The cut is done inside OpenSCAD with exact arithmetic rather than by
pre-slicing the mesh, which avoids sliver triangles.

## How the latch works

1. The radio's raised pedestal drops into a rectangular pocket in the top of
   the block. Because the pocket is rectangular and the pedestal is 25 × 35mm,
   **the radio cannot rotate** — no wings or extra hardware needed.
2. The stud's 15.5mm head passes down through the round entry hole into a
   hidden channel, pressing down a sprung tongue on the way.
3. Slide the radio. The head runs under a ledge; the 8.3mm neck runs in the
   slot above it.
4. At the end of travel the head clears the tongue, which springs back up. Its
   bump now sits behind the head and blocks the return path. The radio is
   captive.
5. The radio's weight pulls the head up against the ledge. The ledge is
   deliberately 0.15mm thinner than the stud neck, so the head clamps it
   against the pedestal. **That clamp is what removes the wobble.**
6. To remove: slide the radio back the way it came. A deliberate firm pull
   rides the head back over the detent, then it lifts out through the entry
   hole.

The slot is **17.5mm** long, which is not arbitrary: the head only just clears
the entry hole at (16.35 + 15.5) / 2 = 15.93mm, and anything shorter leaves
part of the head sitting under an open hole where it can lift and tilt free.
`scripts/cad/check_travel.py` shows the arithmetic, and the build asserts it.

### Why there is no release button

There is deliberately no press-to-release tab. One was designed and then
removed, because the numbers showed it could not work:

- The detent bump has to sit within about 8mm of the locked stud, which is
  underneath the radio. Any push pad therefore has to live further out along
  the tongue than the bump itself.
- A cantilever deflects as x²(3L−x), so pressing a point beyond the bump
  mostly just bends the far end. Pressing the tab moved the bump only **34%**
  as much.
- Releasing needed **4.2mm** of tab travel, but there was only **2.4mm** of
  room beneath it. The tab bottomed out having moved the bump 0.81mm of the
  1.40mm required.

Run `scripts/cad/check_release.py` to see that worked through.

What replaced it is a symmetric click detent — ramped on both sides, with the
exit ramp shorter than the entry ramp so it holds harder than it inserts.
This is safe because **the detent never carries the radio's weight**; the
ledge does. Gravity pulls the radio off the plate face, perpendicular to the
slot, so the detent only has to resist vibration along the slot. It also has
no thin cantilever tip to snap off in a hot car.

If the detent feels too stiff or too loose, adjust `detent_bump` and
`detent_exit`.

Note that the radio's back lies flat against the block, so gravity pulls it
straight off the plate rather than along the slot. The ledge carries the
weight; the tongue only has to stop the sliding. Neither variant gets a
"gravity assist", which is why both have a substantial detent.

## Which variant to print

| | Lengthwise | Crosswise |
| --- | --- | --- |
| Slide direction | Along the radio's length | Across its width |
| Pedestal grip | **35mm span — better** | 25mm span |
| Tongue vs layer lines | Bends across layers (thicker to compensate) | **Bends in-layer — stronger** |
| Whole part | 60 × 75 × 47.8mm, 108.0 cm³ | 60 × 75 × 47.2mm, 105.8 cm³ |
| Coupon | 54 × 38.5 × 17.8mm, 31.7 cm³ | 38.5 × 54 × 17.2mm, 30.6 cm³ |

Both share the same footprint as the original clamp, so neither is bulkier on
the visor than the part you started with. See `preview_lengthwise.png` and
`preview_crosswise.png`.

**Print the crosswise one first.** Its sprung tongue lies in the layer plane,
which matters because PLA is roughly half as strong across layer lines as
along them, and the tongue is the only moving part.

Pick lengthwise if you prefer the slimmer block or want the longer pedestal
engagement; its tongue is made thicker (3.0mm vs 2.4mm) to make up for the
weaker orientation.

## Print settings

Adapted from the profile embedded in the original `Slim_Radio_mount.3mf`
(Bambu A1, 0.4mm nozzle, 0.20mm Standard, PLA), stiffened for a part that has
to act as a spring and carry a radio over bumps.

| Setting | Value | Why |
| --- | --- | --- |
| Nozzle | 0.4mm | as measured |
| Layer height | 0.20mm | matches the original profile |
| Wall loops | **4** (original used 2) | the ledge and tongue are load paths |
| Top / bottom shells | 5 / 4 | |
| Infill | **40%, gyroid** | isotropic; grid is weak in one axis |
| Filament | PLA | PLA is stiff, which the snap-fit wants |
| Supports | tree (auto) | for the C-clamp overhang, as the original |
| Brim | auto | small footprint in this orientation |
| Filament shrink | leave at 100% | Bambu PLA profiles already compensate |

### Orientation

Print it the same way the original was plated: **on its side**, so the
C-clamp's profile is drawn within each layer. That is what keeps the clamp
from splitting when it springs over the visor.

Do **not** stand it up with the block on top — the clamp would then be built
from stacked layers along its bending direction and will delaminate.

## Dialling in the fit

Print `coupon_crosswise.stl` first. It is the socket region cropped out of the
block, roughly 38.5 × 54 × 17mm, so it carries the real keyhole, ledge, tongue
and detent at about a quarter of the material. Try the radio on it and check:

- The stud head passes through the entry hole without force.
- It clicks at the end of travel and does not creep back on its own.
- The radio does not rock or rattle.
- A firm deliberate pull slides it back off.

Then adjust, in this order, in `sds150_mount_common.scad`:

| Symptom | Change |
| --- | --- |
| Radio rocks or rattles | Increase `preload` in 0.05mm steps |
| Will not go on at all | Decrease `preload` |
| Head will not pass the entry hole | Increase `hole_comp` in 0.1mm steps |
| Sliding is stiff or gritty | Increase `clr_slide` in 0.05mm steps |
| Detent too hard to click past | Decrease `detent_bump`, or lengthen `detent_ramp` |
| Comes off too easily | Increase `detent_bump`, shorten `detent_exit`, or thicken `tongue_t` |
| Too hard to pull off | Lengthen `detent_exit` |
| Radio can still twist | Decrease `clr_boss`, or increase `skirt_h` |

`preload` is the one that matters most — it is doing double duty, holding the
radio steady *and* generating the friction that resists rotation. Start there.

## If your radio differs

Every measurement lives in a named parameter at the top of
`sds150_mount_common.scad`. The ones most likely to need changing:

```
stud_head_d      = 15.5;   // wide disc diameter
stud_head_t      = 3.0;    // its thickness
stud_neck_d      = 8.3;    // narrow waist diameter
stud_neck_h      = 4.5;    // waist height above the pedestal
boss_w           = 25.0;   // pedestal, across the radio
boss_l           = 35.0;   // pedestal, along the radio
boss_h           = 6.0;    // pedestal height above the back panel
boss_stud_off_l  = -2.5;   // stud offset from the pedestal centre
```

Set `capture_boss = false` if your radio has no raised pedestal — but be aware
that without it nothing stops the radio rotating on the stud.

## Rebuilding

Requires OpenSCAD and the `.venv-cad` environment (see
`scripts/cad/requirements.txt`).

```powershell
# check the latch still captures the stud
.venv-cad\Scripts\python.exe scripts\cad\fit_check.py

# check the keyhole is long enough for the head to clear the entry hole
.venv-cad\Scripts\python.exe scripts\cad\check_travel.py 17.5

# check the detent can be worked by hand without yielding the tongue
.venv-cad\Scripts\python.exe scripts\cad\check_release.py

# regenerate every STL and 3MF in this folder
.venv-cad\Scripts\python.exe scripts\cad\export_models.py

# check a result for thin walls, stray bodies and bad topology
.venv-cad\Scripts\python.exe scripts\cad\inspect_stl.py `
    models\sds150_visor_mount_crosswise.stl
```

`fit_check.py` measures how much material the stud would collide with in
several poses, and fails the build if the latch stops working:

| Pose | Expectation | Actual |
| --- | --- | --- |
| seated | ~0 — the stud sits free when locked | 0.0 mm³ |
| slide | a bump's worth — the detent is in the way | 257.0 mm³ |
| drop | clear — the head drops straight in | 0.0 mm³ |
| escape | large — the ledge blocks pull-out | 402.1 mm³ |
| ledge over head | near 100% of what a keyhole can have | **97.6%** |

That last one is the check that catches a too-short slot. It is measured
against the head's footprint *minus the neck slot*, because the slot has to
pass through the ledge for the stud to get in at all — comparing against a
solid disc would fail every correct design.

`inspect_stl.py` checks the mesh is a single watertight solid with no
degenerate faces, and measures wall thickness by ray-casting inward from every
face. It discards grazing hits, without which tapered and filleted regions
report phantom near-zero readings. Calibration: the untouched original model
reports a 4.0mm minimum wall, matching its design. All four exports currently
report a **1.98mm minimum wall and zero probes under 1.2mm**.

## Provenance

`slim_radio_mount_source.stl` is the original `Slim_Radio_mount.3mf` geometry,
exported unmodified by `scripts/cad/export_source_mesh.py`. The 3MF itself is
untouched. See the repository `NOTICE.md` for licensing of the original model.
