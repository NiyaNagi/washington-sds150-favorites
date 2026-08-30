# Peak Design radio standoff plan

## Goal

Build a support-free PLA standoff for a Peak Design Standard Plate in a
cup-holder mount. A fixed stalk carries one continuously adjustable,
double-sided head:

- a Uniden SDS150 on a gravity-assisted keyhole;
- a Kenwood TH-D75A or similar handheld on a horizontal belt-clip bridge.

The fully seated SDS150 must clear the Peak Design bearing plane by at least
20 mm. The head pitches continuously from −45° to +45° around an M6×30 bolt.
The active radio tilts its display upward; the unused opposite interface tilts
downward. Both radios may still be installed together at 0°.

## Confirmed decisions

- Peak Design interface: 39 × 39 mm Standard Plate contact footprint,
  centered 1/4"-20 UNC socket.
- Radios occupy opposite faces. One is expected at a time when tilted; both
  may occupy the neutral 0° position.
- SDS150 retention is gravity plus ledge coverage. There is no latch.
- The measured 30 mm is clear clip length below the belt contact. The final
  bridge is the requested full-width 35 × 25 × 3 mm plate, moved upward so
  5 mm remains below it for the spring tip to close flush.
- SDS side guides are omitted by user request.
- Belt-clip lateral control comes from shallow collars and outer stops, not
  tight radio-body wings.
- The hand-drawn labels marked `cm` are millimetres.
- PLA is acceptable for the intended use; this is not qualified for heat
  soak in a parked vehicle.

## Architecture

### Base and socket

The base is no wider than 39 × 39 mm, with rounded corners that remain inside
that square. The lower face bears on the plate's rubber pad to resist rotation.
Two variants use side-loading captive metal nuts:

1. standard M6 nut for the user's M6 Peak Design hardware;
2. standard 1/4"-20 nut for conventional tripod hardware.

The nut is trapped between a 1.2 mm floor and 2.9–3.3 mm solid roof. Only the
screw passage interrupts the bearing face; a side tunnel allows nut replacement
without leaving an open-bottom pocket.

### Structural stalk and adjustable head

The stalk prints upright. It uses a narrow visual waist, full-depth edge
ribs, and large tangent transitions into a two-ear clevis. A common radio
head uses an 11.8 mm central tongue between 6.6 mm ears with 0.20 mm clearance
per side. One M6×30 bolt and captive M6 nut clamp 13 mm-radius friction lands.
The head is continuous-adjustable through ±45°, not four separate parts.
Concentric rib/groove rings increase continuous friction without introducing
indexed angle teeth. Large twelve-lobed knobs positively engage 4 mm or 5 mm
Allen recesses so the round cap screw cannot spin inside a round printed cup.

The section is sized analytically for single-radio, two-radio, 3g road-bump,
and 5g shock cases. Conservative design load is 400 g per face until the
radios are weighed.

### SDS150 face

The model includes the shared measured geometry from
`models/sds150_stud.scad` rather than copying it. The entry hole sits above
the locked position and the radio drops approximately 18–20 mm to seat.
The slot must exceed the mathematical 15.925 mm minimum.

This mount starts looser than the visor mount because gravity supplies
retention:

- ledge preload: 0.05 mm;
- slide clearance: 0.35 mm per side;
- round-hole compensation: 0.25 mm.

The broad head face supports the pedestal. No side guides are used.

The locked lug elevation is derived from the 20 mm radio-bottom clearance.
It is never independently typed.

### Belt-clip face

A 35 × 25 × 3 mm full-width rounded plate occupies the measured 4.5 mm
under-clip gap. It sits at z=132…157, leaving 5 mm of the measured 30 mm clip
section below it so the spring tip closes flush. The plate sits 7 mm behind
the head so the inner spring clears the M6 fork ears.

Two-stage shoulders provide broad compatibility:

- inner shallow collars at approximately 22.3 mm clear width center the
  measured 21.3 mm Kenwood hinge;
- outer stops at 33 mm clear width accept the conservative 32 mm envelope.

The inner collars are low enough for a wider clip to ride over them. A 35 mm
bar is the minimum that provides 33 mm clearance plus 1 mm of printable overlap
into each end support. Exact TD-H9 and UV-5R compatibility is still coupon-tested.

## Implementation stages

1. Persist all measured, derived, published, and conservative radio/hardware
   dimensions in `docs/radio-hardware-measurements.md`.
2. Build simplified diagnostic solids for both radios and define all
   attachment datums from those measurements.
3. Calculate spine/root stress and deflection for 1g, 3g, and 5g load cases.
4. Build the parametric base, socket, organic stalk, M6 clevis, adjustable
  common head, gravity keyhole, shortened full-width clip plate, rails, and
  stops.
5. Export a fit coupon before production models:
   - three SDS150 clearance/preload combinations;
   - 2.8, 3.0, and 3.2 mm clip bars with gap/shoulder variants.
6. Independently verify SDS travel and ledge coverage with the real shared
   stud solid.
7. Sweep Kenwood and conservative generic clip solids over the bridge.
8. Check both seated at 0°, each insertion path, continuous head clearance
  every 5° from −45° to +45°, and active-radio clearance at 0/15/30/45°.
9. Audit the exported Peak Design bearing face and every socket variant.
10. Run watertightness, body-count, thin-wall, bridge, overhang, and build-
    volume checks.
11. Export M6-nut and 1/4"-nut stalks, common head, two Allen-drive knobs,
  fit/base/joint coupons, and diagnostic previews.
12. Add the standoff pipeline after all individual checks pass.
13. Record physical coupon results before calling TD-H9 or UV-5R fit
    verified.

## Acceptance criteria

- Base bounds do not exceed 39.0 × 39.0 mm.
- Peak Design contact patch is fully supported and socket is centered.
- Fully seated SDS150 bottom is at least 20.0 mm above the bearing plane.
- SDS slot travel exceeds 15.925 mm with complete ledge coverage.
- Both radio insertion sweeps remain clear at 0°, and each active radio
  clears the stalk at 0°, 15°, 30°, and 45°.
- The M6 head and stalk have zero solid interference throughout ±45°.
- Static deflection is below 0.5 mm at 1g and 1.5 mm at 3g.
- Structural safety factor is at least 3 at 3g and 1.5 at 5g.
- Production exports are one watertight body with no unintended sub-nozzle
  walls or unsupported islands.
- Every automated harness detects its deliberately injected fault.
- Complete CAD pipeline exits zero.

## Physical gate

The fit coupon must be printed in the final material and orientation before
production values are frozen. The SDS150 must drop, slide, seat without
chatter, and lift out deliberately. The TH-D75A clip must pass the lead-in
and seat without excessive spring force or side play. TD-H9 and UV-5R remain
"envelope compatible" until their actual clips pass this coupon.
