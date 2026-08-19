// =====================================================================
//  SDS150 visor mount - CROSSWISE, COMPLIANT LEVER RELEASE
// =====================================================================
//
//  Variant 4.  Same keyhole socket as the plain crosswise variant, but
//  with a press-to-release lever instead of a pull-off click detent.
//
//  To fit:     drop the stud through the entry hole and slide the radio
//              sideways until it clicks.
//  To remove:  press the tab that reaches out past the block edge, then
//              slide the radio straight back off.
//
//  This is the most robust of the four: the slot is the longest of any
//  variant, and both the arm and its flexure lie in the layer plane in
//  the recommended print orientation, which is where PLA is strongest.
//
//  The tab is on a stiff arm hinged by a short thin flexure - a
//  "small-length flexural pivot" - so the arm rotates rather than bending
//  along its length.  See the notes in sds150_mount_common.scad section 4,
//  and run scripts/cad/design_lever.py for the strain and force figures.
//
//  Anything not overridden below lives in sds150_mount_common.scad.
//
//  Render:
//      openscad -o sds150_visor_mount_crosswise_lever.stl \
//               models/sds150_visor_mount_crosswise_lever.scad
// =====================================================================

variant_slide_axis  = "crosswise";
variant_latch_style = "lever";

// "assembly" | "socket_only" | "coupon" | "section"
variant_render_mode = "assembly";

include <sds150_mount_common.scad>

// ---- variant overrides -------------------------------------------
// These must come AFTER the include: OpenSCAD resolves each variable to
// its last assignment in the file, and everything derived from them is
// recomputed to match.

// Tab reaches out of the open end of the visor tongue, away from the
// folded-over spine, same end as the entry hole.
tab_end = -1;

// This direction has far more room: the pedestal is only 25mm across, and
// the block is 64.85mm long, so scripts/cad/max_travel.py puts the
// ceiling at 33.45mm.  30mm takes nearly all of it while leaving the
// pocket walls a little slack.  The head clears the entry hole at
// 15.93mm, so this is almost DOUBLE the minimum that locks at all.
slot_travel = 30.0;

// Detent depth.  The stud head is 3mm thick, so a 1.4mm bump blocks just
// under half of its edge - a positive, definite catch rather than a token
// one.  The click variants use the same figure.
detent_bump = 1.4;

// Steeper exit than the click variants, since the lever is the intended
// way off.  Not vertical, so a hard pull still works if the lever is ever
// damaged.
detent_exit = 1.2;

// Room beneath the arm.  The arm rotates about the flexure, so its far
// end swings further than the bump does - about 2.7x further here.  A
// 1.4mm bump therefore needs roughly 3.8mm of swing at the block wall,
// and this has to clear that.  The build asserts the relationship.
tongue_gap = 4.5;

// Pivot position, measured back from the chamber's closed end.
//
// Moving it further back would reduce the swing and be mechanically
// nicer, but there is no room: a 30mm slot slides the socket along the
// block, and past about 4mm the flexure root is no longer buried in solid
// material - it would be hinged to thin air and tear away.  The build
// asserts that too.  So the clearance is won with a deeper void instead.
flex_offset = 4.0;

// Longer flexure, to spread the bending over more length.  The deeper
// detent means more rotation at the hinge, and strain scales with angle
// divided by flexure length, so lengthening it keeps peak strain inside
// what PLA tolerates for daily use.
flex_len = 6.0;
