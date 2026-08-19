// =====================================================================
//  SDS150 visor mount - CROSSWISE variant
// =====================================================================
//
//  Identical to the lengthwise variant except the keyhole slot runs
//  across the radio's width, so you slide the radio sideways to lock it
//  instead of along its length.
//
//  Strength: printed in the orientation the original mount uses (on its
//  side, so the C-clamp is drawn in-layer), this variant's sprung tongue
//  also lies in-layer.  That makes it the more durable latch of the two,
//  and the one to print first.
//
//  Weakness: the pedestal is only 25mm across in this direction, so the
//  capture pocket has a shorter span to grip, and the block is chunkier
//  because the pocket has to be wide as well as long.
//
//  Anything not overridden below lives in sds150_mount_common.scad.
//
//  Render:
//      openscad -o sds150_visor_mount_crosswise.stl \
//               models/sds150_visor_mount_crosswise.scad
// =====================================================================

variant_slide_axis  = "crosswise";

// "assembly" | "socket_only" | "coupon" | "section"
variant_render_mode = "assembly";

include <sds150_mount_common.scad>

// ---- variant overrides -------------------------------------------
// These must come AFTER the include: OpenSCAD resolves each variable to
// its last assignment in the file, and everything derived from them is
// recomputed to match.

// The slot runs the length of the clamp here, so send the tab out of the
// open end of the visor tongue, away from the folded-over spine.
tab_end = -1;

// This direction has far more room: the pedestal is only 25mm across, and
// the block is 64.85mm long, so scripts/cad/max_travel.py puts the
// ceiling at 33.45mm.  30mm takes nearly all of it while leaving the
// pocket walls a little slack.  The head clears the entry hole at
// 15.93mm, so this is almost DOUBLE the minimum that locks at all.
slot_travel = 30.0;
