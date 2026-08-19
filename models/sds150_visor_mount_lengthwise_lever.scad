// =====================================================================
//  SDS150 visor mount - LENGTHWISE, COMPLIANT LEVER RELEASE
// =====================================================================
//
//  Variant 3.  Same keyhole socket as the plain lengthwise variant, but
//  with a press-to-release lever instead of a pull-off click detent.
//
//  To fit:     drop the stud through the entry hole and slide the radio
//              along its length until it clicks.
//  To remove:  press the tab that reaches out past the block edge, then
//              slide the radio straight back off.
//
//  The tab is on a stiff arm hinged by a short thin flexure - a
//  "small-length flexural pivot" - so the arm rotates rather than bending
//  along its length.  That is what makes the release work at all; see the
//  notes in sds150_mount_common.scad section 4, and run
//  scripts/cad/design_lever.py for the strain and force figures.
//
//  Anything not overridden below lives in sds150_mount_common.scad.
//
//  Render:
//      openscad -o sds150_visor_mount_lengthwise_lever.stl \
//               models/sds150_visor_mount_lengthwise_lever.scad
// =====================================================================

variant_slide_axis  = "lengthwise";
variant_latch_style = "lever";

// "assembly" | "socket_only" | "coupon" | "section"
variant_render_mode = "assembly";

include <sds150_mount_common.scad>

// ---- variant overrides -------------------------------------------
// These must come AFTER the include: OpenSCAD resolves each variable to
// its last assignment in the file, and everything derived from them is
// recomputed to match.

// Thicker arm, because in this orientation it bends across layer lines.
tongue_t = 3.0;

// Tab reaches out of the right-hand edge, same end as the entry hole.
tab_end  = 1;

// Longest slot this direction can take.  The pedestal is 35mm along the
// radio's length and has to traverse the travel inside its pocket, so the
// pocket is what runs out of room first; scripts/cad/max_travel.py puts
// the ceiling at 18.30mm, and this sits right at it.  Going further would
// mean thinning the pocket walls or dropping the pocket altogether, and
// the pocket is what stops the radio rotating.
slot_travel = 18.0;

// Detent depth.  The stud head is 3mm thick, so a 1.4mm bump blocks just
// under half of its edge - a positive, definite catch rather than a token
// one.  The click variants use the same figure.
detent_bump = 1.4;

// Steeper exit than the click variants, since the lever is the intended
// way off.  Not vertical, so a hard pull still works if the lever is ever
// damaged.
detent_exit = 1.2;

// Room beneath the arm.  The arm rotates about the flexure, so its far
// end swings further than the bump does - about 2.6x further here.  A
// 1.4mm bump therefore needs roughly 3.6mm of swing at the block wall,
// and this has to clear that.  The build asserts the relationship.
tongue_gap = 4.5;

// Pivot position, measured back from the chamber's closed end.
//
// Moving it further back would reduce the swing and be mechanically
// nicer, but there is no room: the slot slides the socket along the
// block, and past about 4mm the flexure root is no longer buried in solid
// material - it would be hinged to thin air and tear away.  The build
// asserts that too.  So the clearance is won with a deeper void instead.
flex_offset = 4.0;

// Longer flexure, to spread the bending over more length.  The deeper
// detent means more rotation at the hinge, and strain scales with angle
// divided by flexure length, so lengthening it keeps peak strain inside
// what PLA tolerates for daily use.
flex_len = 6.0;

// Turn the part over for printing.
//
// This variant's release tab leaves the block on the opposite face from
// the crosswise one, so the default side-on orientation would leave the
// arm hanging over its void with about 1870 mm^2 unsupported.  Flipped,
// that drops to 29.6 mm^2 - just the C-clamp's own mouth, which is
// inherent to the original part.  Measured by check_printable.py.
print_flip = true;
