# Parametric 3D modelling — method, tooling, and reference dimensions

This is the working method behind `models/sds150_visor_mount_*.scad` and
`models/sds150_pd_bracket.scad`: how the models are structured, how they
are checked, what every helper script does, and every dimension measured
so far.

It is written to be usable as a **baseline by another person or another
LLM** starting a new part. The specific numbers are for a Uniden SDS150
belt-clip stud, but the method is not about radios.

---

## 1. The one idea that matters

**Anything that must agree with something else is derived, never typed
twice.**

Every real bug in this project — and there have been many — has been the
same bug wearing a different hat: a number was typed to suit a situation,
the situation moved, and the number stayed. Not one was a modelling
mistake. They were all bookkeeping.

| What went wrong | What it actually was |
|---|---|
| Screw hole 1.48mm from the stud channel, radio's weight on the membrane | Socket position typed before the keyhole moved |
| Peak Design plate hanging 9.5mm off the top | Plate edge typed when the socket was elsewhere |
| Scallop bitten out of the entry hole | Relief widened to fix a whisker; nobody checked what it swept into |
| Latch that couldn't move | Clearance and part generated from one outline, so the error cancelled |
| Hex pocket with a 1.06mm wall | Nut sized across the flats instead of across the corners |
| Nut variant "failing" a coverage check it passed | Checker read the *default* variant's dimensions |

So the structure of every model here is:

```
1. MEASURED     what the physical object is         <- calipers
2. FIT          clearances and preloads             <- tuning knobs
3. STRUCTURE    wall thicknesses, radii             <- choices
4. TO SUIT      sizes of things that must fit       <- external specs
5. DERIVED      everything else                     <- computed, never edited
6. ASSERTS      confirmations of 1-5
7. MODULES      geometry
```

If you find yourself typing a number in section 5, it belongs in 1–4.
If you type one in 1–4 that you *calculated*, it belongs in 5.

### Derive bounds from contents

The plate outline is the clearest example. It used to be four typed
numbers. It is now:

```scad
plate_x_hi = max(lever_x1 + flex_len + plate_edge_r + flex_anchor_wall,
                 socket_x + pd_need);
plate_x_lo = min(-entry_d/2 - keyhole_margin, socket_x - pd_need);
plate_y_hi = socket_y + pd_need;
plate_y_lo = min(latch_bottom - latch_margin, socket_y - pd_need);
```

Each edge names *what it is holding back*. Move the socket and the plate
follows. The asserts became confirmations rather than the only defence.

---

## 2. Environment

| | |
|---|---|
| OpenSCAD | 2021.01, `C:\Program Files\OpenSCAD\openscad.exe` |
| Python | `.venv-cad\Scripts\python.exe` — **separate** from the project's `.venv` |
| Packages | trimesh 5.0.0, numpy <2.3 (scipy needs it), scipy, rtree, manifold3d, shapely, mapbox_earcut, matplotlib, pillow, lxml |
| Printer | Bambu H2C, 0.4mm nozzle, PLA, 0.20mm layer, 3 walls, 15% infill |

The CAD environment is deliberately separate: trimesh pins numpy below
the project's own requirement, and merging them breaks one or the other.

**PowerShell notes.** Chain with `;`, never `&&`. String `-D` arguments
need `-D "var=\`"value\`""`. Long renders go quiet for minutes — that is
normal, not a hang.

> PSReadLine crashes on very long heredocs
> (`ArgumentOutOfRangeException ... Parameter name: top`). Write scratch
> `.scad` files with `[System.IO.File]::WriteAllText`, **never**
> `Set-Content -Encoding utf8` — the BOM it adds breaks OpenSCAD's parser.

---

## 2a. `models/thread_lib.scad` — printable screw threads

Generic and reusable; nothing in it is specific to the enclosure. It
sweeps a trapezoidal profile along a helix as an explicit polyhedron,
because `rotate_extrude` cannot make a helix and stacked slices leave
stair-stepped flanks.

```
male_thread(r0, pitch, length, starts, crest_flat, root_flat,
            flank_ang, lead_in, seg, overlap)
female_thread_void(r0, pitch, length, starts, clr, ...)
```

The female is derived from the male profile by a mitred outward offset,
so the two cannot drift apart.

**Every one of these was a real failure, and most were invisible on
screen.** They are recorded because they are the expensive kind — the
model renders, the preview looks right, and the STL is broken.

| Symptom | Cause | Fix |
|---|---|---|
| Multi-start threads all on one helix | z derived from step index, then translated | `z = lead * a / 360` from the full angle |
| `Simple: no`, 8 volumes, 72 broken faces | ribbons abutting at exactly one pitch → coincident face | `z_overlap = 0.4` |
| 2 starts fail where 1 succeeds | root at `dr = 0` lies tangent to the core → zero-thickness pinch along a helix | `root_sink = 0.4` |
| 72 mm³ jam that no clearance fixed | female void chamfered like the male — **shrinking a void adds material** | square trim on the void |
| Slivers along the trim | `rotate_extrude` trim left at default `$fa` | `$fn = seg` on the trim |
| `PolySet has nonplanar faces`, CGAL assertion | quads on a helix are non-planar | **two triangles per quad**, via an explicit third `for` loop |
| `The given mesh is not closed!` | triangle fan from vertex 0 — the profile is not star-shaped | leave caps as n-gon polygons |

> The nonplanar-faces fix has a trap of its own: `let` + `each` inside
> nested list comprehensions does **not** bind, and silently yields an
> unclosed mesh. Use a real nested `for`.

**Structural rule that came out of this:** union a helix with a *simple*
solid, then union that with the complex one. Unioning a thread directly
with a full `rotate_extrude` body profile fails outright —
`CGAL error in applyUnion3D: assertion violation`, no output at all. The
enclosure's neck is built as its own plain tube, threaded, and only then
joined to the can.

---

## 3. Measured dimensions

### The radio's belt-clip stud — `models/sds150_stud.scad`

The single source of truth, `include`d by every mount.

| Parameter | Value | What it is |
|---|---|---|
| `stud_head_d` | 15.5 mm | Wide outer disc, diameter |
| `stud_head_t` | 3.0 mm | Disc thickness |
| `stud_neck_d` | 8.3 mm | Waist diameter |
| `stud_neck_h` | 4.5 mm | Waist height above the pedestal |
| | 7.5 mm | Neck + head, total stand-off |
| `boss_w` | 25.0 mm | Pedestal, across the radio |
| `boss_l` | 35.0 mm | Pedestal, along the radio |
| `boss_h` | 6.0 mm | Pedestal height |
| `boss_stud_off_l` | −2.5 mm | Stud offset from pedestal centre ⚠ |
| `boss_stud_off_w` | 0.0 mm | Stud offset, across |
| Radio body width | 69.9 mm | For paddle reach |
| Radio mass | ~400 g | For latch forces |

⚠ `boss_stud_off_l` was **derived, not measured** — "20mm from the top of
a 35mm pedestal", so 35/2 − 20 = −2.5. Worth confirming.

### Fit and clearance

| Parameter | Value | Notes |
|---|---|---|
| `preload` | 0.15 mm | **The most important number.** Ledge is made thinner than the neck so the head clamps it. Too small → rattles; too large → won't slide on |
| `clr_slide` | 0.30 mm | Per side, sliding faces |
| `hole_comp` | 0.25 mm | Added to round holes — a 0.4mm nozzle prints inside curves undersize |
| `clr_boss` | 0.40 mm | Around the pedestal pocket |
| `shrink_comp` | 1.000 | Global shrink on mating features. Bambu profiles already compensate |
| `head_ch_clr_z_base` | 0.40 mm | Head channel vertical slack, shared |
| `head_ch_clr_extra` | 0.00 mm | Per-model addition (see below) |

### Derived from the above

| Value | Formula | Result |
|---|---|---|
| `ledge_t` | `(stud_neck_h − preload) × shrink` | 4.35 mm |
| `head_ch_h` | `(stud_head_t + clr_z) × shrink` | 3.40 mm base |
| `entry_d` | `(head_d + 2×clr_slide + hole_comp) × shrink` | 16.35 mm |
| `head_ch_w` | `(head_d + 2×clr_slide) × shrink` | 16.10 mm |
| `neck_w` | `(neck_d + 2×clr_slide) × shrink` | 8.90 mm |
| `min_travel` | `(entry_d + head_d)/2` | 15.925 mm |

`min_travel` is the shortest slot where the head fully clears the entry
hole when locked. Any shorter and part of the head still sits under the
open hole, where it can lift and tilt free.

### Per-model clearance — a real lesson

The same nominal clearance does **not** print the same in every part.

The bracket is a flat plate printed face-down, so the head channel's roof
is an unsupported bridge ~16mm across. Bridged filament sags into the very
gap the disc slides along. The visor mount runs the same nominal figure
and fits, because its channel is buried in solid material with no bridge.

Hence the split:

```scad
head_ch_clr_z_base = 0.40;   // shared - about the radio
head_ch_clr_extra  = 0.00;   // per-model - about the printer
head_ch_clr_z      = head_ch_clr_z_base + head_ch_clr_extra;
```

The bracket sets `head_ch_clr_extra = 0.25` after its `include`. The visor
mount is untouched.

> **OpenSCAD semantics, verified not assumed:** an assignment *after*
> `include <file>` overrides the file's value **and feeds back into values
> derived inside it**. Tested with a minimal case before relying on it.
> (This does **not** apply to `use <>`, which imports modules only.)

### Peak Design bracket

| Parameter | Value | Notes |
|---|---|---|
| `travel` | 21.0 mm | Slot length. Above the 15.925 minimum so the tooth's swept relief clears the entry hole |
| `base_t` | 2.0 mm | Solid behind the head channel |
| `plate_t` | **10.00 mm** | Derived: 4.35 + 3.65 + 2.0 |
| Plate outline | ~55 × 99 mm | Derived from contents |
| `pd_plate_size` | 39.0 mm | Peak Design plate, square ⚠ spec not measured |
| `pd_margin` | 2.5 mm | Plate beyond the PD plate |
| `socket_clear` | 2.0 mm | Socket to keyhole |
| `socket_y` | 37.61 mm | Derived, above the entry hole |

### Latch

| Parameter | Value |
|---|---|
| `lever_clr` | 0.90 mm |
| `chan_wall` | 1.60 mm |
| `lever_w` | 4.0 mm |
| `flex_len` | 15.0 mm |
| `flex_t` | 1.25 mm |
| `detent_bump` | 1.40 mm |
| `tooth_y0` / `tooth_y1` | 4.80 / 7.20 mm |
| `tooth_lead` | 1.80 mm |
| `tooth_relief_inset` | 0.50 mm |
| `paddle_w` | 18.0 mm |
| `press_margin` | 1.25 |

Measured behaviour: rotation 8.00°, paddle travel **3.01 mm**, press
**1.92 N**, hold **5.24 N**, strain 0.58% (0.79% at full press).

### Screw sockets

| Style | Dimension | Value |
|---|---|---|
| `self_tap` | Hole diameter | 5.40 mm |
| `insert` | Insert OD / depth | 7.60 / 6.00 mm |
| `nut` | Across flats / thickness | 11.15 / 5.60 mm |
| | **Across corners** | 12.876 mm |
| all | Thread major / pitch | 6.35 / 1.27 mm |

**Hex pockets are sized across the corners**, `af / cos(30°)`. Using the
across-flats figure from the packet left a 1.06mm wall.

The socket is positioned using the **widest** of all three styles, so all
variants share one footprint and a clip set up for one fits another.

There is deliberately **no modelled-helix thread**. At a 0.4mm nozzle a
1/4"-20 form is 0.69mm deep with crests measuring 0.004mm — it prints
mushy and holds worse than letting the screw tap the plastic. Tried,
measured, removed rather than left as a trap.

### Print limits

| Limit | Value | Why |
|---|---|---|
| Min wall | 1.2 mm | 3 extrusions at 0.4mm |
| Min floor under a screw | 1.2 mm | Steel screw, plastic part |
| Min moving clearance | 0.8 mm | Below this parts fuse in print |
| Max strain, daily flexure | 0.8% | PLA is not a living-hinge material |
| PLA yield | ~2% | |
| PLA modulus | 2800 MPa | Along the layer plane |
| Comfortable thumb press | ≤15 N | |

### EFHW enclosure — `models/efhw_enclosure.scad`

The radial stack is derived **outside-in**, which is the opposite of the
mounts and is the honest direction here: the outside diameter is fixed at
128 mm, and whatever is left after the skirt, the thread and the neck wall
have taken their share *is* the mouth. Deriving it the other way would let
the outside grow silently whenever anything inboard changed.

| | Value |
|---|---|
| Interior | Ø120 × 70 mm |
| Outside diameter | 128 mm, constant |
| Mouth | Ø113.04 (on a 107 mm transformer) |
| Assembled height | 96.18 mm |
| Thread | 4 mm pitch × 2 starts, 3 crests, 1.5 turns |
| Seal | none — 3 mm labyrinth rib at 0.30 mm, 10:1 |

Three architectures were built before this one. **v1** put an external
thread on the full diameter with a base flange, which buried the floor
inside the flange — 74 mm of clear height instead of 75, and all four
weep holes blind. **v2** used an internal thread and a plug lid, which
fixed drainage but stacked the lid's height on top of a full-height wall
and left the joint facing upward. **v3** wraps the lid over the body like
a jam jar: 9 mm shorter, and the joint faces down.

> The 45° cone between bore and mouth was not a styling choice. Without
> it the neck's outer face at r 58.5 hung over a bore at r 60.0 touching
> nothing, and the body exported as **two separate solids**. A flat ledge
> would have been a 3.5 mm unsupported overhang.

---

## 4. The helper scripts

In `scripts/cad/`. All take `.venv-cad\Scripts\python.exe`.

### Design — solve before modelling

**`design_lever.py`**, **`design_finger.py`** — size the latches from
beam theory: travel, strain, press force, holding force. They **read
parameters out of the `.scad` files by regex** rather than restating them,
so the calculation cannot drift from the model.

> ⚠ Regex reads **literal assignments only**. Ask for parameters, never
> derived values. When `plate_x_hi` became derived, `design_finger.py`
> failed loudly — which is the correct behaviour, and better than silently
> reading a stale number. Prefer `echo` (below) where you can.

**`design_thread.py`** — sizes the enclosure's screw thread before any of
it is drawn: extrusions per crest, overhang angle at the flanks, helix
angle. A thread that is wrong analytically cannot be rescued by a
clearance, and finding that out costs five minutes of rendering.

> Its most useful output was the one that changed the design: the pitch
> is coarse (4 mm, 2 starts) not for strength — 3 crests strip at 45 kN
> against 0.004 kN applied — but for **warp tolerance**. 0.5 mm of warp
> is 29% of a 1.73 mm deep thread and 57% of a 0.87 mm one.
>
> It originally read the model by regex and so could not see `thread_r0`,
> which is derived. It fell back to a built-in 69.2 mm and sized a thread
> that does not exist — the real one is at 58.9 mm. It now asks OpenSCAD
> to `echo` the values instead. **A fallback default is worse than a hard
> failure**, because it looks like a pass.

### Fit — does it assemble?

**`fit_check.py`**, **`pd_fit_check.py`** — position a *solid model of the
stud* at each stage and measure the intersection volume with the mount.

Stages: `seated`, `slide`, `drop`, `escape`, `rise`, `released`, `ledge`,
`disc`, `clash`.

Reading them: `seated`/`drop`/`released` should be ~0 (it fits and can
move). `escape` should be **large** (it is captive). `ledge` is coverage
over the head — a measure of grip.

Last run: seated 0.0 / slide 11.9 / drop 0.0 / escape 407.3 / rise 11.9 /
released 0.0 / **coverage 96.6%**.

> The check that counts coverage uses `bracket_body()`, not `bracket()` —
> including the latch tooth pushed coverage to an impossible 101.1%. **A
> percentage over 100 always means the numerator and denominator disagree**;
> the PD coverage check had the same fault independently.

**`check_lever_free.py`**, **`check_pd_sweep.py`** — rotate the latch
against the body **as a separate solid** through its stroke and watch the
shared volume.

> This exists because fit checks *cannot* catch a binding latch: the
> relief and the latch are generated from the same outline, so an error
> appears in both and they still nest perfectly. Shared volume should stay
> flat at the flexure's own footprint — that is the joint, not a
> collision. Last run: ~18 mm³ flat across the whole stroke.

**`check_thread_fit.py`** — the same idea applied to a screw. Builds the
male and female as **separate solids** from `thread_lib.scad` and
physically assembles them: free at rest, screwed down the helix, pulled
straight up without turning, and a deliberately miscoupled control.

> `lifted` must be **large**. A thread with far too much clearance passes
> "free" and "screwed" perfectly and then pulls apart in your hand. The
> miscoupled case tests the *harness* — if it cannot see a lead error
> injected on purpose, it would not see a real one either.

**`check_cable_slot.py`** — lays a coax into the enclosure's cable slot,
lowers it down in steps, and screws the lid down on top of it.

> Caught a slot that was open at the top and still unusable: it stopped
> at the shoulder with 13 mm of neck standing directly above it, so there
> was nothing to lower the cable *through*. 62.5 mm³ of collision on the
> way down. The seat width is found by **bisection** rather than compared
> as a volume, because a 0.2 mm squeeze on a 5 mm cable is about 1 mm³ —
> asking "do they overlap enough?" answers nothing.

### Interference — does anything overlap anything else?

**`audit_pd_bracket.py`** — probes the **exported STL**, not the model's
arithmetic. Measures socket-to-keyhole, socket-to-latch, channel-to-relief,
plate margins, PD plate coverage, and hanging sense.

> Exists because the 1.48mm membrane passed *every* check that existed at
> the time. Each was looking at one thing; none asked "does anything
> overlap anything it shouldn't?"

**`check_entry_wall.py`** — walks around the entry hole at ledge height
and reports the solid reach at each angle, so a bite out of one side shows
as a dip instead of being averaged away. It stops at the **first** gap:
totalling material along the ray would count the far side and report a
healthy wall straight across a hole.

**`check_enclosure.py`** — probes the exported enclosure solid for the
features nothing else looks at: the labyrinth rib's real depth, whether
all four weep holes and all four carabiner ears break clean through, and
whether the floor actually falls outward to the gutter.

> Two lessons from its own first run, both in the *probe* rather than the
> part. A radial band drawn **inside** a feature finds nothing, because a
> revolved flat annulus has vertices only at its edges — the rib measured
> −2.00 mm. And a control probe must be spun onto the feature it is meant
> to jam in; left at 0° it hung in the air between two ears and looked
> exactly like a broken probe.

**`check_text.py`** — checks the lid's lettering survives being fattened:
stroke widths, and whether the counters (the enclosed holes in A and D)
close up. Last run: 12 outlines, 3 counters, narrowest stroke 3.72 mm,
tightest counter 1.70 mm.

### Mesh quality and printability

**`inspect_stl.py`** — watertight, body count, degenerate faces, and a
thin-wall probe reporting the **location** of the thinnest region.

**`check_printable.py`**, **`check_pd_printable.py`** — unsupported
regions, distinguishing genuine overhangs from bridges and self-supporting
chamfers.

### Export and preview

**`export_models.py`**, **`export_pd_bracket.py`**, **`export_enclosure.py`**
— render every variant to STL/3MF and verify each is a single watertight
solid.

> `export_enclosure.py` also renders the lid at two different interior
> heights and diffs them, proving the lid is genuinely height-independent
> (0.000 mm³, 0.0000 mm). That is a claim worth checking rather than
> assuming, since it is what lets the body be resized alone.

**`render_stl.py`** — preview PNGs.

### The pipeline

**`build_all.py`** — 21 steps. Stops at the first hard failure.

```powershell
.venv-cad\Scripts\python.exe scripts\cad\build_all.py
```

**Run it to completion and report the verdict.** It goes silent for
minutes at a time; that is CGAL working, not a hang. The enclosure steps
at the end are the slowest — about 85s for the body and 60s for the lid,
because the threads are swept polyhedra at 180 segments per turn.

---

## 5. Verification method

Layered, because each layer catches what the one before cannot.

```
1. Asserts in the model        instant, but only as good as the arithmetic
2. Analytical scripts          beam theory, independent of the geometry
3. Volume/motion checks        catches assembly and binding
4. Mesh probes on the export   catches what the arithmetic got wrong
5. Printed coupon              catches what the model cannot know
```

**The critical rule: layers 1–3 all trust the model. Layer 4 does not.**
Every serious bug was caught at layer 4 or in a photo of a print. When an
assert and a mesh probe disagree, *the mesh is right*.

### Writing asserts that work

- **Measure real 2D/3D distances, not one axis.** The overhang assert
  compared X and never looked at Y. It passed while the plate hung 9.5mm
  off the top.
- **Find the true critical point.** The entry-hole assert tested the
  tooth's tip; the corner that actually swings furthest is the relief's
  inboard one, 26mm from the pivot. Understated the reach, passed while
  the hole was scalloped.
- **Compare with tolerance when values are equal by construction.**
  `socket_y` is derived to give exactly `socket_clear`, and the nut
  variant came out at 1.99999999 and failed against its own design value.
- **Put the fix in the message.** "Lengthen travel, lower `tooth_y1`, or
  reduce `tooth_relief_inset`."

### Sampling meshes

- Use `mesh.contains()` for inside/outside, ray casts for surface height.
- **Mask what is *meant* to be missing** — and mask it correctly. The PD
  coverage check masked the screw bore, but the *chamfer* is wider, so a
  ring of legitimate chamfer counted as unsupported.
- **Match the variant.** The audit read the default self-tap dimensions
  while measuring the nut mesh, and reported a hex pocket as missing
  material.
- Convex shapes need only their corners tested.

---

## 6. Techniques worth reusing

### Swept relief for moving parts

Rotate the real outline through the real stroke and union the steps:

```scad
module lever_swept_2d() {
    for (i = [0 : sweep_steps])
        about_pivot(-sweep_ang * i / sweep_steps) children();
}
```

Tighter than growing the whole outline by the largest swing, which opens
the same gap next to the pivot where nothing moves — wasting plate and
letting grit in. Six steps is ample for a few degrees.

### Sweep wide, then clip

Where a relief meets an existing void, **sweep an outline that spans the
whole void, then intersect with a half-plane just inside its edge.** Order
matters, and both orders were tried:

- *Sweep narrow* → rotated copies drift outboard, so the inboard edge is
  an arc crossing the wall at a glancing angle, stranding a **0.18mm**
  wedge.
- *Sweep wide, then clip* → every copy still reaches past the clip line,
  leaving a straight edge **inside** the void. They overlap at every
  height and merge cleanly.

The clip is also what stops the wide outline swinging on to scallop
something else.

> Two voids that *almost* meet leave whiskers a tenth of a millimetre
> thick. Always overlap; never abut.

### Lever, not cantilever

A cantilever moves its tip and its tooth the same way — pressing drives
the tooth *further in*. That mistake cost the visor mount a full redesign.
Pivot about a flexure and the sense reverses.

### Let gravity work

The bracket's entry hole is *above* the locked position, so the radio's
weight holds the stud away from the only opening. Removal needs a
deliberate lift *against* gravity plus a press. The latch then only
handles knocks and inversion, not the load.

### Rotation turns distance into travel

A point far from the pivot in X moves a long way in Y for a few degrees.
This is the source of *two* separate bugs here. When something rotates,
always ask **which point is furthest from the pivot** — that is the one
that collides, not the one you were thinking about.

---

## 7. Starting a new model

1. **Measure**, and mark anything not measured with ⚠.
2. **Put shared geometry in an include file.** One definition of the
   mating feature, used by every model that mates with it.
3. **Structure the file** in the seven sections above.
4. **Derive every bound from its contents.**
5. **Write asserts as you go**, with the fix in the message.
6. **Add a mesh-level check** for anything an assert can't see.
7. **Wire it into `build_all.py`** so it cannot regress.
8. **Print a coupon** before committing to a long print.

### Checklist before calling it done

- [ ] Renders with no warnings, single watertight solid
- [ ] Min wall ≥ 1.2mm, and you know *where* the thinnest point is
- [ ] Moving parts: shared volume flat across the stroke
- [ ] Overhangs are bridges or self-supporting chamfers
- [ ] Every percentage is ≤ 100
- [ ] Checks match the variant they're measuring
- [ ] Unmeasured inputs flagged in the docs
- [ ] Full pipeline passes end to end

---

## 8. Ten mistakes, and the general rule behind each

1. **Screw into a channel** → check every feature against *every* other,
   not just the ones you were thinking about.
2. **Plate hanging off the edge** → derive bounds from contents.
3. **X-only assert** → measure real distances.
4. **Cantilever instead of lever** → check the *sense* of a mechanism.
5. **Relief swinging into a hole** → find the point furthest from the pivot.
6. **Whisker between two voids** → overlap, never abut.
7. **Hex across flats** → know which dimension a spec quotes.
8. **101% coverage** → a ratio over 100 means the two halves disagree.
9. **Checker reading the wrong variant** → parameterise checks by variant.
10. **Regex reading a now-derived value** → prefer `echo`; fail loudly.

The general rule under all ten: **the model will always tell you what you
asked, not what you meant.** Ask it in more than one way, and make at
least one of those ways independent of the model.

---

## 9. Unverified inputs

| Value | Where | Status |
|---|---|---|
| `pd_plate_size = 39.0` | `sds150_pd_bracket.scad` | Peak Design spec, **not measured**. Drives the whole part size. Dual Plate is longer in one axis |
| `boss_stud_off_l = −2.5` | `sds150_stud.scad` | Derived from "20mm from the top of a 35mm pedestal". Shared with the visor mounts |
| `head_ch_clr_extra = 0.25` | `sds150_pd_bracket.scad` | Set from a **printed part that bound**. Raise if it still binds |
