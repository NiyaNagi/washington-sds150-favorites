# EFHW antenna enclosure

A screw-lid cylinder for an end-fed half-wave transformer, meant to hang
from a tree by a carabiner and shrug off rain.

|  |  |
| --- | --- |
| Interior | Ø120 × 70 mm |
| Outside diameter | 128 mm, constant top to bottom |
| Height, assembled | 96.18 mm |
| Across the carabiner ears | 156 mm |
| Mouth | Ø113.04 |
| Thread | 4 mm pitch, 2 starts, 3 crests engaged, 1.5 turns to close |
| Body | 202.6 cm³ |
| Lid | 55.3 cm³ |
| Cable exits | 2 open-topped slots for 5 mm coax |

Everything is generated from `models/efhw_enclosure.scad`. Nothing in the
exported files was drawn by hand.

## Print these

| File | What it is |
| --- | --- |
| `models/efhw_coupon_body.stl` / `.3mf` | **Print these two first.** |
| `models/efhw_coupon_lid.stl` / `.3mf` | |
| `models/efhw_enclosure_body.stl` / `.3mf` | The can |
| `models/efhw_enclosure_lid.stl` / `.3mf` | The lid, already flipped for printing |

The coupons are the thread and the knurl with the middle taken out —
about 20 minutes for the pair against roughly five hours for the body.
They carry the real thread at the real diameter, so if they screw
together the full-size parts will too. If the fit is wrong, the only
thing lost is 20 minutes.

### Settings

Bambu H2C, 0.4 mm nozzle, PLA, 0.20 mm layer.

| Setting | Value | Why |
| --- | --- | --- |
| Wall loops | 4 | the thread crest is 2.4 extrusions wide, so it needs to be walls rather than infill |
| Top / bottom shells | 5 / 4 | the floor is the only thing between the transformer and the ground |
| Infill | 15 %, gyroid | the walls carry everything; infill is just there to support the top |
| Supports | **none** | see below |
| Brim | none | 128 mm of first layer is plenty of adhesion |

### Orientation

Both parts print exactly as exported. Do not rotate them.

- The **body** stands on its floor. The thread is on the outside of the
  neck, pointing up and away, so every flank is self-supporting.
- The **lid** is already upside-down in the file — the lettering faces
  the build plate. That is deliberate twice over: it puts the internal
  thread's flanks the right way up to print without support, and it gives
  the text a glass-smooth face straight off the build sheet, which reads
  far better at 1 mm deep than a top surface ever would.

The 45° cone between the bore and the mouth is the steepest overhang in
either part, and 45° prints unsupported.

## How it seals

There is no gasket, no O-ring, and nothing to buy. Water is kept out by
being made to climb.

The lid wraps **over** the body like a jam jar rather than plugging into
it. Rain running down the outside reaches the parting line and meets a
0.6 mm chamfer on both parts — a drip edge, so surface tension pulls the
water off rather than round the corner. To get any further it would have
to run *uphill* over the shoulder, then down the thread, and then over a
3 mm rib that hangs into the mouth at 0.30 mm clearance.

That last part is the labyrinth: a 10 : 1 length-to-gap ratio. It is not
a pressure seal and is not claimed to be one — the box is drip-proof, not
submersible. It has weep holes in the floor precisely because the honest
assumption is that some water will eventually get in.

The floor is domed 1 mm from the middle to the wall, so anything that
does get in runs outward to a gutter and out through four 3 mm weep
holes. Those are drilled at 30° from vertical, so they exit further out
than they enter and drain by gravity rather than holding a bead.

## The cable exits

Two slots, opposite each other, **open at the top**.

You do not thread the coax through a hole. You lay it in from above, with
the PL-259 already fitted, and screw the lid down over it.

```
        z 93.68  ──┐  channel runs out the top of the neck
                   │
        z 79.48  ──┼─ shoulder: where the lid lands
                   │
        z 77.38  ──┤  top of a 5 mm cable  ← 2.1 mm of air below the lid
                   │
        z 74.88  ──┘  the seat, 4.8 mm wide, grips a 5 mm cable
```

The channel runs the full height of the neck and out of the top of it.
That is the part that matters and the part that is easy to get wrong: a
slot that stops at the shoulder has no roof but 13 mm of neck standing
directly above it, so there is nothing to lower the cable *through*. It
is open and useless at the same time. The first version of this was
built that way and `check_cable_slot.py` caught it — 62.5 mm³ of
collision on the way down.

Carrying the channel through the neck interrupts the thread at two
places, about 3 % of it. Interrupted threads are ordinary — most moulded
caps have them — and the loss was measured rather than assumed: the lid
still turns through all 1.5 turns with zero interference and still
interlocks against a straight pull.

The slot narrows from a 5.6 mm mouth to a 4.8 mm seat, so the cable
pushes in past the flare and is then held while you fit the lid. The
2.1 mm of clearance under the lid is not decoration: **the lid turns one
and a half times to close**, so a cable it caught would not simply be
squashed, it would be wound around the neck and chafed through.

For a different coax, change `cable_d` and everything else follows.

## Assembling it

1. Drop the transformer in. The mouth is Ø113.04 against a 107 mm
   transformer, and the 45° cone funnels it past the step.
2. Lay the coax into one slot and push it down until it seats.
3. Screw the lid on — 1.5 turns.
4. Hang it by a carabiner through any of the four ears.

The second slot is there so you can run a counterpoise or a second
radiator out the other side. If you only need one, the spare is a drain.

## Why the thread is so coarse

4 mm pitch and 2 starts gives an 8 mm lead, so the lid closes in one and
a half turns instead of six. That is worth having when you are up a
ladder in the rain.

The obvious objection is strength, and the numbers dismiss it: three
crests engaged strip at about **45 kN**, against **0.004 kN** applied by
a 400 g transformer. That is a margin of roughly 11,000 : 1. Strength was
never the constraint.

What actually drives the pitch is **warp**. A large-diameter printed
cylinder is not perfectly round when it comes off the plate. Half a
millimetre of warp is 29 % of a 1.73 mm deep thread, but 57 % of a
0.87 mm one. A coarse thread tolerates a distorted print; a fine one
jams.

## Rebuilding it

Requires OpenSCAD and the `.venv-cad` environment.

```powershell
# analytical sizing - extrusions per crest, overhang angle, helix angle
.venv-cad\Scripts\python.exe scripts\cad\design_thread.py

# screw the male and female together as separate solids and measure
.venv-cad\Scripts\python.exe scripts\cad\check_thread_fit.py

# the lettering: stroke widths, and whether the counters survive fattening
.venv-cad\Scripts\python.exe scripts\cad\check_text.py

# lay a cable in, drop it down the slot, close the lid on it
.venv-cad\Scripts\python.exe scripts\cad\check_cable_slot.py

# probe the finished solid: labyrinth, weeps, ears, floor crown
.venv-cad\Scripts\python.exe scripts\cad\check_enclosure.py

# render all four parts to STL and 3MF
.venv-cad\Scripts\python.exe scripts\cad\export_enclosure.py
```

Or run the whole thing, in order, stopping at the first failure:

```powershell
.venv-cad\Scripts\python.exe scripts\cad\build_all.py
```

Renders are slow — about 85 s for the body, 60 s for the lid — because
the threads are swept polyhedra with 180 segments per turn.

### What each check is actually for

Every one of these measures the **exported mesh**, not the model's own
arithmetic. That distinction is the whole point. The model asserts a
great deal about itself, but an assert can only compare numbers the model
also computed, so it cannot see a feature that was calculated correctly
and then destroyed by a later boolean. This project has hit that failure
repeatedly: a `hull()` that erased the ear fillets, another that filled
in the knurl scallops, a floor that ended up buried inside a flange. All
of those passed every assert in the file.

Each check that must pass is paired with a deliberately faulty control
that must fail. A harness measuring nothing reports a clean sweep, and
the control is the only way to tell that apart from a part that is
genuinely right. This is not theoretical either — on its first run
`check_enclosure.py` reported the carabiner probe finding nothing, which
turned out to be the control rod hanging in the air between two ears
rather than over one.

## Adjusting the fit

In `models/efhw_enclosure.scad`:

| Symptom | Change |
| --- | --- |
| Lid will not start on the thread | Increase `thread_clr` in 0.05 mm steps |
| Lid is sloppy and rattles | Decrease `thread_clr` |
| Lid does not pull down tight | Increase `thread_crests` |
| Cable falls out of the slot | Increase `cable_grip` |
| Cable is hard to push into the slot | Decrease `cable_grip`, or increase `cable_mouth_flare` |
| Lid drags on the cable | Increase `cable_lid_clr` |
| Different coax | Set `cable_d`; the rest follows |
| Knurl too fine to grip wet | Decrease `knurl_count`, or increase `knurl_depth` |
| Transformer will not fit | Increase `interior_d`; the outside grows with it |

`thread_clr` is the one that matters. Print the coupons, and change it
0.05 mm at a time.

## Known limitations

- **Drip-proof, not waterproof.** It will handle rain hanging in a tree.
  It will not survive being dropped in a lake, and the weep holes mean it
  is not even trying to.
- The labyrinth depends on the lid being screwed fully down. At 1.5 turns
  that is quick, but it is also easy to leave half-done.
- No pressure equalisation. A sealed box taken up a mountain and back
  will breathe through the weep holes, which is what they are for, but it
  does mean air moves in and out.
- The thread is interrupted at the two cable slots. Verified harmless,
  but it does mean the lid can be started at two orientations that feel
  slightly different.

## Design history

The enclosure went through three complete architectures before this one.
The first two are worth recording because the reasons they failed are
the reasons this one is shaped the way it is.

**v1 — external thread on the full diameter, with a base flange and a
carabiner boss.** Abandoned because the flange buried the floor: the
clear interior height came out at 74 mm rather than 75, all four weep
holes were blind, and the box would have held water rather than drained
it. The O-ring groove it was built around was also solving a problem
nobody had — the requirement was rain, not immersion.

**v2 — internal thread with a plug lid.** Solved the drainage, but the
plug lid stacked its own height on top of a full-height wall, and the
joint faced upward where water collects.

**v3 — the current design.** The wrap-over lid was the user's own idea,
after finding a jam-jar style enclosure on Printables. It saved 9 mm of
overall height against the plug design and turned the joint to face
downward, which is worth more than the 9 mm.

The interior went from 75 mm to 70 mm during v3, and the mouth got its
45° cone after the body exported as two separate solids — the neck's
outer face at r 58.5 was hanging over a bore at r 60.0, touching nothing
at all.

Full method, including the thread library's bug history and the CGAL
failures behind the neck's construction, is in
[docs/modelling-method.md](modelling-method.md).
