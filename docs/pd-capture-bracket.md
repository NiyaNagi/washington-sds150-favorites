# SDS150 Peak Design Capture bracket

A **flat 10.00mm plate** that holds the Uniden SDS150 by its belt-clip stud
and mounts to a Peak Design Capture clip through a standard 1/4"-20 tripod
socket.

It reuses the visor mount's keyhole exactly — both include
`models/sds150_stud.scad`, so the stud dimensions and clearances are
defined once and cannot drift apart.

## How it works

1. The stud's head passes through the round entry hole, which is in the
   **middle** of the plate, below the screw.
2. Let the radio drop. The head runs down a hidden channel; the neck runs
   in the slot above it, riding over a ramp that pushes the latch aside.
3. At the bottom the latch springs back above the neck. The radio is
   captive, hanging **below** the mounting screw.
4. To remove: press the paddle on the right-hand edge, lift, and take the
   radio off through the entry hole.

**Gravity does useful work here.** The entry hole is above the locked
position, so the radio's own weight holds the stud away from the only
opening. Getting off requires a deliberate lift *against* gravity as well
as a press on the latch — so the latch only has to cope with knocks and
with the bracket being inverted, not with carrying the radio. That is much
lighter duty than a latch bearing the full load.

## Where the screw goes, and why

The radio hangs **below** the mounting point, so the tripod socket is at
the top of the plate and the keyhole below it. That is the only
arrangement that puts the radio under a Capture clip rather than standing
it up past your shoulder.

Two things have to be true at once, and they pull against each other:

- The screw must be **above** the stud, or the radio does not hang from
  the clip — it stands on it.
- The stud must still enter at the **top** of its slot and drop **down**
  to lock, or gravity stops helping and starts hurting.

So the keyhole keeps its internal sense — entry hole above, locked
position below — and the whole assembly moved down the plate, with the
socket taking the space above the entry hole.

**The latch is not reversed relative to the keyhole.** Flipping it would
put the tooth below the neck, where it blocks nothing: the stud escapes
upward, so the tooth has to sit above it whichever way round the plate is.

An earlier version put the socket directly behind the stud. That left a
1.48mm membrane between the screw hole and the head channel with the
radio's whole weight on it in bending, and needed a 6mm boss to claw back
thread depth — which is what made the part 15.75mm thick. Clear of the
keyhole the socket threads into the plate's full thickness and needs no
boss at all.

The screw stays on the centreline with the stud, so the radio's weight has
no lever arm and produces no twisting moment about the screw.

## Why the plate is the size it is

The outline is **not chosen** — it is derived from the things that have to
fit inside it, and it comes out about **55 × 99mm**:

| Edge | Set by |
|---|---|
| Right | The flexure needs body outboard of it to anchor into |
| Left | The keyhole, or the PD plate — whichever reaches further |
| Top | The PD plate, and nothing else |
| Bottom | The latch's swept relief, or the PD plate |

This replaced four hand-typed numbers, and the reason is worth recording:
**a typed edge does not move when the thing it was covering does.** The
socket was positioned early, the plate's top edge was typed to suit, and
then the socket moved. Nothing connected the two, so the 39mm Peak Design
plate ended up hanging 9.5mm off the top.

The assert that was supposed to catch it compared `plate_x_lo` and
`plate_x_hi` and **never looked at Y at all** — so it passed cheerfully
while the plate overhung an edge it wasn't measuring. It now tests all
four corners of the square against the rounded outline, and
`audit_pd_bracket.py` re-checks it on the exported mesh by sampling the
back face, because the arithmetic is exactly what was wrong before.

About 19.5mm of plate above the socket exists purely to carry the PD
plate. That is real material for no mechanical function, but a plate
supported on three sides pivots on the unsupported edge, and no amount of
screw torque fixes it.

**Moving the socket down instead does not work.** It would put the screw
below the stud, and the radio would then stand on the Capture clip rather
than hang from it — the one thing the whole layout exists to avoid.

The socket sits `entry_d/2 + widest_socket/2 + 2mm` above the entry hole,
using the **widest** of the three socket styles rather than whichever is
being built, so all three variants share one footprint and a Capture clip
set up for one fits another.

## The notch beside the entry hole

The first print had a scallop bitten out of the entry hole. It came from a
fix for a different problem: two voids that almost met were leaving a
0.1mm whisker of plastic between them, and the tooth's relief was widened
right across the neck slot to merge them.

That put the relief's inboard corner **26mm from the pivot**. Rotation
turns distance into travel, so as the latch opened that corner swung
almost 5mm — up and into the entry hole, leaving a 0.20mm ledge.

The relief is now clipped 0.5mm inside the slot edge. Inside the slot the
ledge is already void, so relief there removes nothing — it only swings.
Clipping still overlaps enough to merge the two voids, which is all the
original fix needed.

| Relief reaches to | Ledge left at the entry hole |
|---|---|
| x = −4.45 (across the slot) | 0.20 mm |
| x = 2.15 (tooth tip) | 1.99 mm |
| **x = 3.95 (clipped)** | **2.70 mm measured** |

There is a second-order trap here worth recording, because the obvious fix
is wrong. Narrowing the *swept outline* to the clip line does not work:
each rotated copy drifts outboard as it turns, so the relief's inboard
boundary becomes an **arc** that crosses the slot wall at a glancing angle
and strands a 0.18mm wedge of plastic between the two voids.

The outline is therefore swept at full width and the **result** clipped.
Every rotated copy still reaches past the clip line, so the intersection
leaves a straight vertical edge *inside* the slot — the two voids overlap
at every height and merge cleanly. The model asserts this precondition
rather than assuming it.

`check_entry_wall.py` walks around the hole at ledge height and reports
the reach at each angle, so a bite out of one side shows as a dip instead
of being averaged away.

## Why this plate is thicker than the visor mount's

The first print bound: the stud's wide disc would not slide along its
channel, even though the visor mount — using the **same** nominal
clearance from the same shared file — fits fine.

The difference is not the radio, it is the printing. This part is a flat
plate printed face-down, so the channel's roof is an unsupported bridge
about 16mm across. Bridged filament sags, and it sags into exactly the gap
the disc has to slide through. The visor mount's channel is buried inside
a solid block with no bridge to sag.

So the clearance is split in two:

```scad
head_ch_clr_z_base = 0.40;   // shared - a property of the radio
head_ch_clr_extra  = 0.00;   // per-model - a property of the printing
```

The bracket sets `head_ch_clr_extra = 0.25` after its `include`. The visor
mount keeps the baseline and is not disturbed, because it works.

| | Before | Now |
|---|---|---|
| Head channel | 3.40 mm | **3.65 mm** |
| Plate thickness | 9.75 mm | **10.00 mm** |
| Ledge | 4.35 mm | 4.35 mm (unchanged) |

The ledge is deliberately untouched: it carries the clamping preload that
stops the radio rattling, and it was not what was binding.

**If it still binds, raise `head_ch_clr_extra` first.** It is the only
number here about the printer rather than the radio, and each 0.05mm costs
0.05mm of plate thickness and nothing else.

## Making the latch actually move

The first version had a throw of 1.44mm at the paddle. That is not enough
to feel — the pad of a thumb compresses further than that, so pressing it
seemed to do nothing even though the tooth was clearing the neck properly.

Paddle travel is $\text{arm} \times \sin\theta$ and flexure strain is
$\theta t / 2L$, so travel can be bought two ways and only one is cheap:

| Route | Cost |
|---|---|
| **Longer tab arm** | None in strain. Lengthens the plate downward. |
| **Larger angle** | Costs strain, *and* swings the tooth further along the slot — its relief then marches up into the entry hole, which has to move away in turn. |

The numbers sit near the middle: 8° of rotation, a 21.6mm tab arm, and a
15mm flexure. The press got lighter on the way — a longer arm needs less
force for the same torque — while the shorter tooth arm *holds harder*.

| | Before | Now |
|---|---|---|
| Paddle travel | 1.44 mm | **3.01 mm** |
| Press force | 2.77 N | **1.92 N** |
| Holding force | 3.62 N | **5.24 N** |
| Strain at full press | 0.61% | 0.79% |

## Why the latch flexes sideways

The visor mount's latch is a tongue beneath the head channel that flexes
downward, costing tongue thickness plus a flex void underneath — roughly
6mm of extra plate. Here the latch is a full-depth bar beside the slot
that flexes *in the plane* of the plate, needing no room underneath.

It is a **lever**, not a cantilever. A cantilever moves its tip and its
tooth the same way, so pressing it would only drive the tooth further into
the slot — that mistake cost the visor mount a full redesign. Pivoting the
bar about a flexure reverses the sense: press the paddle, and the tooth on
the far side of the pivot swings outward and frees the neck.

The paddle is 18mm wide, dished, and rounded on every face a finger
touches. It also reaches far enough out to clear the radio's edge — the
radio is ~70mm wide and hangs in front of the bracket, so a paddle tucked
inboard of 35mm would be awkward to find even though the two never touch.

## Printing

| | |
|---|---|
| Orientation | As exported — bearing face down. **Do not rotate.** |
| Supports | **None.** Support inside the latch relief welds the mechanism solid. |
| Material | PLA |
| Layer height | 0.20mm |
| Walls | 3 (the latch bar is only 4mm wide) |
| Infill | 15%+ |

The exported orientation is what makes the latch printable in place: it
flexes in the layer plane, and the slots it moves in are vertical. The
part does bridge ~16mm over the head channel, which is routine.

### There is no test coupon

A coupon is worth having when a small piece can prove the fiddly part of a
design cheaply. That does not apply here — the mechanism runs from the
entry hole at the top to the paddle at the bottom, which is essentially
the whole plate.

Every trim that saved a worthwhile amount of material either cut through
the mechanism or sliced a corner fillet at a shallow angle, leaving a
feather edge under 0.9mm. The trims that kept the walls sound removed 5%.
At 18 cm³ the full bracket prints in well under an hour, so print the real
thing and check the fit on that.

## Tripod socket options

Three variants are exported. They differ only in the socket.

| File | Socket | Notes |
|---|---|---|
| `..._self_tap.stl` | Undersize hole | **Start here.** The steel screw cuts its own full-depth thread, which usually holds better than a printed one. No hardware. |
| `..._insert.stl` | Heat-set insert | Strongest by a wide margin. Needs a 1/4"-20 brass insert and a soldering iron. Best if the plate comes on and off often. |
| `..._nut.stl` | Captive hex nut | Drop a 1/4"-20 nut in from the back before fitting the plate. |

There is deliberately no modelled-helix variant. It was built and
measured: at a 0.4mm nozzle a 1/4"-20 thread form is only 0.69mm deep and
its crests come to a knife edge — the wall check read 0.004mm — so it
prints mushy and holds *worse* than simply letting the screw tap the
plastic. It was dropped rather than left in as a trap.

The radio's weight is not what threatens this joint — with the socket in
solid plate the shear area is far beyond what ~400g demands. The real risk
is over-torquing while fitting the plate.

## Tuning the fit

Edit `models/sds150_stud.scad` — shared with the visor mount, so changes
apply to both.

| Symptom | Change |
|---|---|
| Radio rattles | raise `preload` |
| Will not slide on at all | lower `preload` |
| Head will not enter the hole | raise `hole_comp` |
| Radio rotates on the stud | raise `preload` — friction is what resists rotation |

Latch feel is tuned in `models/sds150_pd_bracket.scad`:

| Symptom | Change |
|---|---|
| Latch too stiff | thin `flex_t`, or lengthen `flex_len` |
| Latch too weak to snap back | thicken `flex_t` |
| Radio releases too easily | raise `detent_bump` |

After any change, re-run the checks — several asserts will catch a value
that breaks the geometry, and the fit checks catch the rest:

```
.venv-cad/Scripts/python.exe scripts/cad/build_all.py
```

## Verified

| Check | Result |
|---|---|
| Seated interference | 0.0 mm³ |
| Slide in past the latch | 11.9 mm³ (the ramp only) |
| Escape while locked | 407 mm³ blocked |
| Rise with latch at rest | 11.9 mm³ — blocked |
| Rise with latch pressed | 0.0 mm³ — **releases** |
| Ledge coverage | 96.6% |
| Latch stroke | overlap flat at ~19 mm³ throughout — no binding |
| Flexure strain at full release | 0.61% (PLA yields ~2%) |
| Press force | 2.8 N (282 gf), 1.44mm of paddle travel |
| Socket to keyhole | 12.8mm |
| Socket to latch | 5.4mm |
| Minimum wall | 1.30mm |
| Unsupported regions | all bridges or self-supporting chamfers |

Three of these deserve comment.

**Rise vs released** is the pair that matters most: together they show the
latch is both the reason the radio stays on *and* the only thing stopping
it coming off — so pressing the paddle genuinely frees it, rather than
merely looking as though it should.

**Latch stroke** exists because the fit checks cannot catch a binding
latch. The relief and the latch are generated from the same outline, so an
error in the swept clearance appears in both and they still nest
perfectly. `check_pd_sweep.py` rotates the latch against the body as a
separate solid and watches whether their shared volume grows — it stays
flat at the flexure's own footprint, which is the joint, not a collision.

**Socket clearances** are measured by `audit_pd_bracket.py`, which probes
the exported STL rather than trusting the model's arithmetic. It exists
because the 1.48mm membrane in the first version passed every check that
then existed: each was looking at one thing, and none asked whether
anything overlapped anything else. It also samples the back face under the
Peak Design plate and reports what fraction lands on solid material.

**Entry-hole ledge** is measured by `check_entry_wall.py`, which walks
around the hole at ledge height. The model asserts this too, but the
assert previously tested the tooth's tip rather than the corner of its
relief that actually swings furthest — so it understated the reach and
passed while the hole was being scalloped.

## Before printing a full bracket

Two inputs here are **not measured**, and both are worth a minute with
calipers before committing to a long print.

**`pd_plate_size = 39.0`** in `sds150_pd_bracket.scad` is taken from the
Peak Design spec rather than from a plate in hand. It now drives the size
of the whole part, so an error propagates straight into the outline. If
you use a **Dual Plate**, it is longer in one axis — set this to the
longer dimension.

**`boss_stud_off_l = -2.5`** in `sds150_stud.scad` was derived from "20mm
from the top of a 35mm pedestal". Worth confirming against the actual
radio, since it sets where the plate sits relative to the body. It is
shared with the visor mounts, so a correction fixes both.

**`head_ch_clr_extra = 0.25`** in `sds150_pd_bracket.scad` was set from a
printed part that bound, not from a calculation. If the disc still will
not slide, raise it — see the section on plate thickness above.

The anti-rotation pedestal pocket (`capture_pedestal`) is **off**: its
walls would rise from the face that sits on the build plate, so they would
print into thin air. If the radio does rotate in use, raise `preload`
first.
