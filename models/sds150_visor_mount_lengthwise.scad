// =====================================================================
//  SDS150 visor mount - LENGTHWISE variant
// =====================================================================
//
//  The keyhole slot runs along the radio's long axis.  Push the stud
//  through the entry hole, then slide the radio along its own length
//  until the detent clicks.
//
//  Strength: the radio's pedestal is 35mm long in this direction, so the
//  capture pocket grips it over the longest possible span.
//
//  Weakness: printed in the orientation the original mount uses (on its
//  side, so the C-clamp is drawn in-layer), this variant's sprung tongue
//  runs along the build direction, which means it bends across layer
//  lines.  The tongue is therefore made thicker here to compensate.
//  If you want the strongest possible latch, print the crosswise variant.
//
//  Anything not overridden below lives in sds150_mount_common.scad.
//
//  Render:
//      openscad -o sds150_visor_mount_lengthwise.stl \
//               models/sds150_visor_mount_lengthwise.scad
// =====================================================================

variant_slide_axis  = "lengthwise";

// "assembly" | "socket_only" | "coupon" | "section"
variant_render_mode = "assembly";

include <sds150_mount_common.scad>

// ---- variant overrides -------------------------------------------
// These must come AFTER the include: OpenSCAD resolves each variable to
// its last assignment in the file, and everything derived from them is
// recomputed to match.

// Thicker spring, because in this orientation it bends across layers.
tongue_t = 3.0;

// Slot runs across the visor, so the tab reaches the right-hand edge.
tab_end  = 1;

// Longest slot this direction can take.  The pedestal is 35mm along the
// radio's length and has to traverse the travel inside its pocket, so the
// pocket is what runs out of room first; scripts/cad/max_travel.py puts
// the ceiling at 18.30mm, and this sits right at it.  Going further would
// mean thinning the pocket walls or dropping the pocket altogether, and
// the pocket is what stops the radio rotating.
slot_travel = 18.0;
