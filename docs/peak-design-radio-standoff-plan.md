# Peak Design radio standoff plan

## Goal

Build a one-piece, support-free PLA standoff for a Peak Design Standard
Plate in a cup-holder mount. It carries two radios simultaneously on
opposite faces:

- a Uniden SDS150 on a gravity-assisted keyhole;
- a Kenwood TH-D75A or similar handheld on a horizontal belt-clip bridge.

The fully seated SDS150 must clear the Peak Design bearing plane by at
least 20 mm. Both displays face outward and both antennas point upward.

## Confirmed decisions

- Peak Design interface: 39 × 39 mm Standard Plate contact footprint,
  centered 1/4"-20 UNC socket.
- Radios occupy opposite faces, so their insertion paths and controls do
  not compete for the same space.
- SDS150 retention is gravity plus ledge coverage. There is no latch.
- Belt-clip lateral control comes from clip-centering shoulders, not tight
  radio-body wings.
- The hand-drawn labels marked `cm` are millimetres.
- PLA is acceptable for the intended use; this is not qualified for heat
  soak in a parked vehicle.

## Architecture

### Base and socket

The base is no wider than 39 × 39 mm, with rounded corners that remain
inside that square. The entire bottom face bears on the plate's rubber pad
to resist rotation. A centered female socket is offered in three variants:

1. 5.40 mm pilot for a self-tapping 1/4"-20 screw;
2. 7.60 mm × 6.00 mm heat-set insert pocket;
3. captive nut pocket, 12.876 mm across corners × 5.60 mm deep.

The heat-set insert is preferred for repeated use. All variants share one
external envelope sized around the captive-nut option.

### Structural spine

The spine prints upright. It uses a narrow visual waist, full-depth edge
ribs, and large tangent transitions into the base and radio heads. This
puts material away from the neutral axis, increasing bending stiffness
without turning the part into a solid rectangular slab.

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

A shallow, open-ended pedestal guide follows the radio through its insertion
stroke and limits rotation. It is not a latch and does not block lifting the
radio back out.

The locked lug elevation is derived from the 20 mm radio-bottom clearance.
It is never independently typed.

### Belt-clip face

A rounded 3.0 mm horizontal bridge occupies the measured 4.5 mm under-clip
gap. Forty-five-degree end haunches keep the first unsupported span inside
the repository's proven bridge range.

Two-stage shoulders provide broad compatibility:

- inner shallow ramps at approximately 22.3 mm clear width center the
  measured 21.3 mm Kenwood hinge;
- outer stops at approximately 33 mm clear width accept the published
  32 mm UV-5R replacement-clip envelope.

The inner ramps are low enough for a wider clip to ride over them. Exact
TD-H9 clip dimensions are not reliably published, so compatibility is
coupon-tested rather than claimed from web data.

Broad, shallow radio-body pads below the bridge are bump stops only. They
do not closely capture any one body width.

## Implementation stages

1. Persist all measured, derived, published, and conservative radio/hardware
   dimensions in `docs/radio-hardware-measurements.md`.
2. Build simplified diagnostic solids for both radios and define all
   attachment datums from those measurements.
3. Calculate spine/root stress and deflection for 1g, 3g, and 5g load cases.
4. Build the parametric base, socket, organic spine, gravity keyhole, clip
   bridge, shoulders, and bump pads.
5. Export a fit coupon before production models:
   - three SDS150 clearance/preload combinations;
   - 2.8, 3.0, and 3.2 mm clip bars with gap/shoulder variants.
6. Independently verify SDS travel and ledge coverage with the real shared
   stud solid.
7. Sweep Kenwood and conservative generic clip solids over the bridge.
8. Check simultaneous seated and insertion poses for both radios.
9. Audit the exported Peak Design bearing face and every socket variant.
10. Run watertightness, body-count, thin-wall, bridge, overhang, and build-
    volume checks.
11. Export self-tap, insert, and nut STL/3MF variants plus coupons and
    diagnostic previews.
12. Add the standoff pipeline after all individual checks pass.
13. Record physical coupon results before calling TD-H9 or UV-5R fit
    verified.

## Acceptance criteria

- Base bounds do not exceed 39.0 × 39.0 mm.
- Peak Design contact patch is fully supported and socket is centered.
- Fully seated SDS150 bottom is at least 20.0 mm above the bearing plane.
- SDS slot travel exceeds 15.925 mm with complete ledge coverage.
- Both radio insertion sweeps remain clear with the other radio seated.
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
