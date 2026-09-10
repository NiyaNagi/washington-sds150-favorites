# ProClip radio mounting plates

Six rigid plates that bolt to a Brodit/ProClip vehicle mount through its
AMPS hole pattern and carry a handheld radio on the front:

| | Uniden SDS150 | Belt-clip radio | Both |
| --- | --- | --- | --- |
| **Horizontal holes** | `proclip_sds_horizontal` | `proclip_clip_horizontal` | `proclip_combined_horizontal` |
| **Vertical holes** | `proclip_sds_vertical` | `proclip_clip_vertical` | `proclip_combined_vertical` |

The radio interfaces are the ones already proven on the
[Peak Design radio standoff](peak-design-radio-standoff.md): the SDS150's
gravity keyhole and the universal belt-clip bridge. The keyhole geometry
now lives in `models/sds150_stud.scad` as `gravity_keyhole_void()` and
`gravity_head_channel()`, taking its fit as arguments, so the two designs
cannot drift apart — `check_proclip_fit.py` fails the build if they do.

---

## Read this before printing anything

**The ProClip side of this design has never been offered up to a ProClip.**

Neither mount is owned yet. Brodit and ProClip USA publish no dimensioned
drawing, no specification table, and no CAD for these parts; their
installation sheets are scans with no dimensions on them. What they do
publish is a sentence: the mounting plate carries *"one set of AMPS-holes
as well as two sets of double-holes placed in different height"*.

So the design uses the AMPS set, which is a real industry standard —
**30.17 mm × 38.05 mm centre-to-centre, four holes, up to 5.2 mm screws**
— and ignores the double-hole pairs entirely, because their spacing is
not published and inventing it would be worse than not using them.

Everything else about the ProClip plate — its outline, its thickness, its
hole diameters — is unknown. The plate thickness appears in the model
only as `proclip_plate_t_est`, which is used to *recommend a screw
length* and never to cut geometry.

**Print `proclip_gauge_horizontal.stl` and `proclip_gauge_vertical.stl`
first, and offer them up to the real mounts.** They answer, in about
fifteen minutes of printing:

- is the pattern actually AMPS, and which way round is it on each mount;
- what diameter are the ProClip's own holes (a 3.0/3.5/4.0/4.5/5.0 mm pin
  ladder — the largest pin that enters without force is the answer);
- where are Brodit's two double-hole pairs (a central window lets you see
  and measure them while the AMPS holes hold the gauge registered).

Then record the answers in
[radio-hardware-measurements.md](radio-hardware-measurements.md) and, if
the orientations turn out to be the other way round, swap the two-line
`ORIENTATIONS` table in `scripts/cad/export_proclip_mounts.py`.
`horizontal` and `vertical` are **labels**, not findings.

---

## What to buy

Four fasteners per plate.

| Item | Spec | Why |
| --- | --- | --- |
| Screws | **M4 × 16 mm countersunk**, 90° head, A2 stainless — ISO 10642 / DIN 7991 (hex socket) or DIN 965 (Phillips) | 15.0 mm is the computed minimum; 16 mm is the next stock size |
| Nuts | **M4 nylon-insert lock nuts**, DIN 985, A2 stainless | Vibration is the whole problem with a car |
| Washers | **M4 plain washers, ~12 mm OD**, under the nut only | Spreads the clamp load on the ProClip's ABS |

Buy a few **M4 × 20 mm** as well. The 16 mm figure rests on an *estimated*
5 mm ProClip plate; if it measures thicker, 16 mm will not reach through
the nyloc.

Countersunk, not pan head: the SDS150's pedestal slides directly across
this face, and a proud head would foul it. The plate leaves 3.25 mm of
material under each head.

**This needs finger access behind the ProClip plate.** If your dash does
not allow it, ProClip's own **#4 self-tapping screws** ([SK16, 0.3"](https://www.proclipusa.com/products/100100-small-self-tapping-screws-4-pack-of-self-tapping-screws-mpn-sk16)
or [SK19, 0.37"](https://www.proclipusa.com/products/100155-medium-self-tapping-screws-4-pack-of-self-tapping-screws-mpn-sk19))
will thread straight into the ABS, but each removal degrades the thread,
and the plate's 4.5 mm clearance holes are sized for M4 — a #4 screw will
be sloppy in them.

---

## Print order

Do not start with a plate.

| Print | File | What it settles |
| --- | --- | --- |
| 1 | `proclip_gauge_{horizontal,vertical}.stl` | Does the pattern fit the real mount at all |
| 2 | `proclip_coupon_sds_{easy,nominal,firm}.stl` | The SDS150 keyhole fit |
| 3 | `proclip_coupon_clip.stl` | The belt-clip bridge fit |
| 4 | `proclip_<variant>_<orientation>.stl` | The plate itself |

The SDS coupons are the real pad and keyhole cropped out of the real
plate at three fits (0.00/0.05/0.10 mm preload against
0.40/0.35/0.30 mm side clearance). Pick the loosest that does not
chatter. `nominal` is the default and matches the standoff's, so if you
have already dialled that one in you can skip straight to step 3.

---

## How each interface works

### SDS150 — gravity keyhole

Identical in principle to the standoff, and deliberately identical in
numbers:

1. The 15.5 mm lug head goes through the upper entry hole.
2. The radio descends 19 mm.
3. The 8.3 mm neck runs in the narrow slot while the head runs in a
   hidden channel behind the 3.115 mm ledge.
4. At the bottom the head sits entirely under solid material.

There is no latch. Removal is a deliberate lift against gravity and then
out through the entry hole. `check_proclip_fit.py` reports zero
interference across eleven travel positions and 137 mm³ of ledge
interception on pull-out.

The 25 × 35 × 6 mm pedestal bears on a **flat pad**, exactly as on the
standoff. The pad is a raised boss 4.7 mm proud of the plate, because the
keyhole needs 8.1 mm of depth behind the bearing face and the plate is
only 5 mm thick.

**There is deliberately no anti-rotation.** The lug is round, so nothing
stops the radio turning on it except friction between the pedestal and
the pad. A pedestal channel — two 3 mm walls, 25.8 mm apart, recessed
into the pad — was built and then removed: it stood proud beside the
keyhole for a radio that is already held flat, and on the combined plate
the AMPS lands necessarily bite one of its two walls, leaving it visibly
asymmetric.

It is still a supported option, `sds_guide = true`, and enabling it
changes nothing else — `sds_face_y`, the face the pedestal bears on and
the datum the whole keyhole hangs from, is invariant because the pad
grows by exactly the channel's depth.

`check_proclip_interface.py` reports the shipped state honestly rather
than asserting it is fine: the pedestal seats flat at 0.00 mm³, a 3°
twist is **free** at 0.00 mm³, and the same twist with `sds_guide = true`
is **blocked** at 11–13 mm³. So the option is kept under test and cannot
quietly rot, while the plates you print are described as they are.

If the radio does turn on its lug in use, that is the fix, and it costs
3 mm of extra depth.

### Belt clip — universal bridge

The standoff's bridge, unchanged: a 35 × 25 × 3 mm plate standing 7 mm
off the face on two end supports, with rounded top and bottom edges, a
21.3 mm pair of centring collars for the measured Kenwood TH-D75A hinge,
and outer stops 33.0 mm apart for wider clips.

The 7 mm standoff is kept even though the fork ears that originally
drove it do not exist here, because 7 mm is the number the measured
Kenwood clip was actually swept against. `check_proclip_clip.py` sweeps
the measured Kenwood and a 32 mm tapered article through nine descent
poses each (0.00 mm³ both), and rejects a 2.5 mm gap and a 40 mm square
clip.

The bridge sits **above** the AMPS pattern rather than centred on it, so
its end supports can never land on a countersink. That is derived, not
placed: `clip_bar_z0 = amps_z/2 + amps_land_r + clip_amps_gap`.

### Combined — side by side

Both radios on the same face, separated by
`sds_body_w/2 + thd_body_w/2 + 8 mm` = 70.95 mm between centres, derived
from the radio envelopes rather than typed as a plate width.

They are side by side horizontally and staggered vertically: the SDS150
sits centred on the screw pattern, and the belt-clip radio sits above and
outboard because the bridge cannot come down over the countersinks. The
Kenwood is 31 mm shorter than the SDS150, so this works out better than
it sounds. The two gravity moments are on the same side and add; the two
in-plane moments are opposed and largely cancel.

---

## Loads

`design_proclip_mount.py` computes these from the model's own echoed
numbers. PLA at a conservative 25 MPa.

| Plate | Load | Moment | Tension per screw | Bending | FoS |
| --- | --- | ---: | ---: | ---: | ---: |
| SDS | 1g | 140 N·mm | 2.3 N | 0.99 MPa | 25.1 |
| SDS | 3g | 420 N·mm | 7.0 N | 2.98 MPa | 8.4 |
| SDS | 5g | 700 N·mm | 11.6 N | 4.97 MPa | 5.0 |
| Clip | 5g | 650 N·mm | 10.8 N | 4.00 MPa | 6.2 |
| Combined | 5g | 1350 N·mm | 22.4 N | 4.97 MPa | 5.0 |

Worst factor of safety anywhere is **5.0**, and the worst screw tension
is 22.4 N — nothing for an M4. Removing the pedestal channel did not
change these: the load arm is measured from `sds_face_y`, which the
channel does not move.

**The plate is not the weak link. The ProClip is.**

A ProClip retains itself by clipping into dashboard panel seams. Brodit
publish no load rating for that grip, and the product line is built
around phones and GPS units. A loaded SDS150 is 400 g; the combined plate
hangs 800 g roughly 35 mm off the dash. Every number above says only that
the printed plate and its screws will not be what fails.

You accepted that risk explicitly. It is written down here so that it
stays a decision rather than an oversight. If the mount ever does let go,
the radio lands in the footwell — a tether anchor would be a sensible
addition and is not currently in the design.

---

## Print settings

| Setting | Value | Why |
| --- | --- | --- |
| Material | PLA | Matches the existing parts and the proven coupon fits |
| Orientation | **Flat on the bearing face** | Layers lie in the plate's strongest bending plane; no supports |
| Layer height | 0.20 mm | |
| Nozzle | 0.4 mm | |
| Wall loops | 4 | The countersink lands and the bridge supports are load paths |
| Top / bottom shells | 5 / 4 | |
| Infill | 30% gyroid | Isotropic |
| Supports | none | |
| Brim | 4–6 mm on the combined plates | 113 mm of thin plate |

Printing flat leaves two bridges, both deliberate:

- The **stud head channel's roof** is a ~16 mm unsupported span, and
  bridged filament sags into the very gap the head slides along. This is
  the same situation as the Peak Design bracket, so it carries the same
  proven allowance: `proclip_head_clr_extra = 0.25 mm`, derived on top of
  the shared 0.40 mm baseline rather than typed as 0.65.
- The **belt-clip bridge's underside** spans 33 mm over the 7 mm slot.
  It is a cosmetic face inside the slot and a routine bridge length; if
  your printer droops badly there, the slot is 7 mm against a spring
  plate of about 1.6 mm, so there is a lot of margin to lose.

### PLA and hot cars

PLA softens around 60 °C. A dashboard beside a windscreen in summer sun
exceeds that comfortably, and these plates hang a 400 g mass in bending.
You chose PLA to keep the fits identical to the proven coupons, which is
a reasonable trade for a garaged car. **It is not qualified for a closed
vehicle in the sun**, and the failure mode is creep — the plate sags
slowly rather than snapping, so it will not be obvious until the radio is
pointing at the floor. PETG or ASA is the fix if that becomes a problem;
expect to re-run a fit coupon, because the clearances will move.

---

## Sizes

| File | Volume | Envelope |
| --- | ---: | --- |
| `proclip_sds_horizontal` | 14.6 cm³ | 52.5 × 9.7 × 49.5 mm |
| `proclip_sds_vertical` | 13.3 cm³ | 44.6 × 9.7 × 52.5 mm |
| `proclip_clip_horizontal` | 21.4 cm³ | 52.5 × 15.7 × 73.0 mm |
| `proclip_clip_vertical` | 21.0 cm³ | 44.6 × 15.7 × 80.8 mm |
| `proclip_combined_horizontal` | 38.6 cm³ | 113.2 × 15.7 × 75.4 mm |
| `proclip_combined_vertical` | 40.6 cm³ | 113.2 × 15.7 × 80.8 mm |
| `proclip_gauge_horizontal` | 11.2 cm³ | 68.5 × 8.5 × 69.6 mm |
| `proclip_gauge_vertical` | 11.0 cm³ | 60.6 × 8.5 × 77.5 mm |

All twelve exports are single watertight solids. `inspect_stl.py` reports
a 1.4 mm minimum wall and **zero probes under 1.2 mm** on every one.

---

## Two bugs the harness caught

Both were invisible in preview and both are the project's usual failure
mode — a number that was right for a situation that then moved.

Both were found while the pedestal channel was still the default. The
shipped plates no longer have that channel, so neither bug can occur in
them — but the channel remains an option, the fixes remain in force
behind `sds_guide`, and the reasoning is the reusable part.

**A 0.53 mm knife edge.** The AMPS countersinks need a flat, open land
around them, so raised features are cut back with a keep-out cylinder. On
the landscape SDS plate that cylinder stopped **0.52 mm short** of the
pedestal channel's wall, leaving a rib far too thin to print, over
60 mm². `inspect_stl.py` found it; the first two explanations
(land radius too large, then pad corner radius too large) were both
wrong, and only the actual probe coordinates identified it — a grazing
tangency between the land circle and the channel wall.

The fix is a rule rather than a number: a land must either clear the
channel wall by a full wall thickness **or** cut cleanly through it, never
stop on the boundary. Where it would, the keep-out opens up until it goes
through. An assert now enforces it for any layout.

**A clearance that only looked at half the screws.** While tracing the
above, `amps_wall_bite` — the measure of how much channel wall the lands
eat — turned out to walk only the +X screw column. It reported a
confident zero for the combined plates, where it is the −X column that
does the biting. It now walks all four screws, and the real figure is
that 24.7 mm to 35 mm of the 35 mm pedestal keeps its channel wall,
against a 15 mm floor.

---

## Adding articulation later

The plates are deliberately rigid, and the geometry is deliberately
separable: the AMPS interface is one module, each radio interface is
another.

If you want movement later, the research is already done and recorded in
[radio-hardware-measurements.md](radio-hardware-measurements.md). The
short version: **do not use a 17 mm ball**, which is what ProClip's own
phone and GPS mounts use — it is a Garmin-class size and a loaded SDS150
is 400 g. The 1" / 25.4 mm RAM B-size ball is the right class (rated 2 lb
standard, 1 lb heavy duty) and bolts to the very same AMPS pattern via an
off-the-shelf adapter such as Arkon's APAMPS25MM or RAM's RAM-B-238U.

The better division of labour is then to **buy the ball and print the
socket**: a printed PLA ball on a stem is a cantilever and the obvious
first thing to fail, whereas a split socket clamping a metal ball puts
the printed part in compression. The repo already has the M6 hardware and
the 1.40× GoPro-style captured-nut knob to close such a socket.

---

## Verification commands

```powershell
.venv-cad\Scripts\python.exe scripts\cad\design_proclip_mount.py
.venv-cad\Scripts\python.exe scripts\cad\check_proclip_interface.py
.venv-cad\Scripts\python.exe scripts\cad\check_proclip_fit.py
.venv-cad\Scripts\python.exe scripts\cad\check_proclip_clip.py
.venv-cad\Scripts\python.exe scripts\cad\export_proclip_mounts.py
.venv-cad\Scripts\python.exe scripts\cad\inspect_stl.py `
    "models\proclip mounts\proclip_combined_horizontal.stl"
```

Every check carries at least one injected fault, because a harness that
cannot fail is not evidence:

| Check | Injected fault |
| --- | --- |
| Countersink lands are clear | Keep-out shrunk to 20%, must be seen |
| Screws clear of the keyhole | Screw envelope grown 12 mm, must collide |
| Pedestal seats flat | 3° twist must be free as shipped, and blocked with `sds_guide = true` |
| Combined plate, both radios fitted | One radio slid 40 mm inboard, must collide |
| SDS150 keyhole fit | Stud oversized 3 mm, must collide |
| Belt-clip bridge | 2.5 mm gap and a 40 mm square clip, both must collide |
| Coupon variants | All three volumes must differ |
| Standoff agreement | Ledge, entry and travel must match to 0.001 mm |

On the combined plates, radio-against-radio, SDS150-against-plate and
belt-clip-radio-against-plate all measure 0.00 mm³ in both orientations,
and sliding one radio 40 mm inboard produces 89,281 mm³ — so the zeros
mean clearance rather than a check that never looks.

---

## Known limits

- **The ProClip interface is unverified.** It is a published standard
  applied to a part nobody here has measured. The gauge exists for
  exactly this reason and should be printed first.
- Which mount is "horizontal" and which is "vertical" is an assumption
  from photographs, not a measurement.
- The ProClip plate thickness is an estimate, and the recommended screw
  length rests on it.
- Brodit's two double-hole pairs are unused. If they turn out to be
  usefully placed, a six- or eight-screw variant would be stiffer.
- **Nothing stops the SDS150 rotating on its lug.** Retention is the lug
  ledge and gravity; orientation is friction between the pedestal and the
  pad, as on the standoff. `sds_guide = true` adds a channel that
  positively blocks it, at 3 mm of extra depth.
- The ProClip's own retention is unrated and is the governing risk.
- TH-D75A clip geometry is physically measured. TD-H9 and UV-5R remain
  envelope-compatible only, exactly as on the standoff.
- The 57 mm vs 69.9 mm SDS150 width conflict is unresolved; 69.9 mm is
  still used, and it sets the combined plate's 113 mm width. A caliper
  measurement would make that plate meaningfully narrower.
- PLA is accepted for a garaged car and is not qualified for a hot one.
- No tether or secondary retention.
- These are analytical values, not destructive test results.
