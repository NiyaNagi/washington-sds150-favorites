// =====================================================================
//  SDS150 belt-clip stud - shared geometry
// =====================================================================
//
//  One definition of the stud, its clearances, and the keyhole that
//  captures it.  Included by every mount so they cannot drift apart.
//
//  This file was extracted from sds150_mount_common.scad when the Peak
//  Design bracket was added.  Keeping two copies of these numbers would
//  be a mistake: during development of the visor mount, three separate
//  false test failures were traced to check scripts holding their own
//  duplicates of variant values that had since changed.
//
//  Nothing here is printable on its own.  A mount includes this file,
//  then builds a body around keyhole_void().
//
//
//  HOW THE KEYHOLE WORKS
//  ---------------------
//  The radio's stud is a mushroom: a wide flat head on a narrow neck.
//
//    1. The head passes through a round entry hole.
//    2. The radio slides along the slot.  The head runs in a hidden
//       channel; the narrow neck runs in the slot above it.
//    3. At the end of travel the head sits entirely under solid material
//       - the "ledge" - and cannot pull out.
//
//  The ledge is deliberately made a hair thinner than the stud neck, so
//  the head squeezes it against the radio's pedestal.  That squeeze is
//  what removes wobble, and it is the single most important fit number.
//
// =====================================================================


// ---------------------------------------------------------------------
//  STUD DIMENSIONS  (measured from the radio - change if yours differ)
// ---------------------------------------------------------------------

// Wide outer disc of the stud.
stud_head_d      = 15.5;   // diameter, mm
stud_head_t      = 3.0;    // thickness, mm

// Narrow waist between the head and the radio's pedestal.
stud_neck_d      = 8.3;    // diameter, mm
stud_neck_h      = 4.5;    // height above the pedestal, mm
                           // stud_neck_h + stud_head_t = 7.5 total

// Raised pedestal the stud sits on, measured on the radio's back.
boss_w           = 25.0;   // across the radio's width, mm
boss_l           = 35.0;   // along the radio's length, mm
boss_h           = 6.0;    // how far it stands proud of the back panel, mm

// The stud is not in the middle of the pedestal.  These say how far the
// stud sits from the pedestal's centre.  Measured 20mm from the top of a
// 35mm pedestal, so 35/2 - 20 = -2.5.
boss_stud_off_l  = -2.5;   // along the radio's length, mm
boss_stud_off_w  =  0.0;   // across the radio's width, mm


// ---------------------------------------------------------------------
//  FIT AND CLEARANCE   <-- tune these first if the print does not fit
// ---------------------------------------------------------------------

// PRELOAD is the single most important number.  The slot ledge is made
// slightly thinner than the stud neck, so the stud head squeezes the
// ledge against the radio's pedestal.  That squeeze removes all wobble.
//   too small -> radio rattles
//   too large -> radio will not slide onto the mount at all
preload          = 0.15;   // mm

// Sliding clearance applied per side to the head channel and neck slot.
clr_slide        = 0.30;   // mm

// Extra diameter added to round holes only.  A 0.4mm nozzle tends to
// print inside curves undersize; this compensates.  Increase if the stud
// head will not pass through the entry hole.
hole_comp        = 0.25;   // mm

// Clearance around the pedestal capture pocket.
clr_boss         = 0.40;   // mm per side

// Global scale on mating features only, for filament shrinkage.
// 1.000 = none.  Bambu PLA profiles already compensate bulk shrinkage,
// so leave this alone unless a printed test coupon says otherwise.
shrink_comp      = 1.000;

// Vertical slack for the stud head in its channel, in two parts.
//
// The BASELINE is a property of the radio and the printer, so it is
// shared.  The EXTRA is per-model, because the same nominal channel does
// not print the same in every part: in the flat bracket the channel's
// roof is a ~16mm unsupported bridge and sags into the gap, while in the
// chunky visor mount it is buried in solid material and does not.  The
// visor mount is a snug but working fit at the baseline; the bracket
// needed more.
//
// To use it, assign head_ch_clr_extra AFTER including this file.  In
// OpenSCAD the last assignment in a scope wins and feeds back into values
// derived here, so head_ch_h picks it up - verified, not assumed.
head_ch_clr_z_base = 0.40;   // shared baseline, mm
head_ch_clr_extra  = 0.00;   // per-model addition, mm - override on include

head_ch_clr_z    = head_ch_clr_z_base + head_ch_clr_extra;


// =====================================================================
//  DERIVED - computed, not edited
// =====================================================================

// The ledge is deliberately thinner than the neck; the difference is the
// clamping preload.
ledge_t     = (stud_neck_h - preload) * shrink_comp;
head_ch_h   = (stud_head_t + head_ch_clr_z) * shrink_comp;

entry_d     = (stud_head_d + 2 * clr_slide + hole_comp) * shrink_comp;
head_ch_w   = (stud_head_d + 2 * clr_slide) * shrink_comp;
neck_w      = (stud_neck_d + 2 * clr_slide) * shrink_comp;

// Everything the stud needs, measured down from the bearing face at z=0.
stud_depth  = ledge_t + head_ch_h;

// Shortest slot that actually locks.  Below this the head is still partly
// under the open entry hole when "locked", so it can lift and tilt free.
// Verify any slot length against this with scripts/cad/check_travel.py.
min_travel  = (entry_d + stud_head_d) / 2;


// =====================================================================
//  SHARED MODULES
// =====================================================================

// Capsule prism running along +X from x = 0 to x = length.
module capsule(length, width, height) {
    linear_extrude(height = height)
        hull() {
            circle(d = width);
            translate([length, 0]) circle(d = width);
        }
}

// The void the stud moves through, in a frame where the bearing face is
// z = 0, the locked stud is at the origin, and the entry hole is `travel`
// away along +X.  `above` is how far the slot is cut up through whatever
// sits on the bearing face.
module keyhole_void(travel, above = 1.0) {
    // Neck slot through the ledge, open at the bearing face.
    translate([0, 0, -ledge_t - 0.01])
        capsule(travel, neck_w, ledge_t + above + 0.02);

    // Round entry hole, big enough for the head to drop through.
    translate([travel, 0, -ledge_t - 0.01])
        cylinder(d = entry_d, h = ledge_t + above + 0.02);
}

// The head channel: a hidden slot beneath the ledge that the stud head
// runs in.  This is what actually traps the radio.
module head_channel(travel, extra_w = 0) {
    translate([0, 0, -ledge_t - head_ch_h])
        capsule(travel, head_ch_w + 2 * extra_w, head_ch_h);
}

// The stud itself, for fit checking.  Locked position is the origin.
module stud_solid(pos = 0, extra = 0, lift = 0) {
    translate([pos, 0, lift]) {
        translate([0, 0, -stud_neck_h])
            cylinder(d = stud_neck_d + extra, h = stud_neck_h + 0.01);
        translate([0, 0, -stud_neck_h - stud_head_t])
            cylinder(d = stud_head_d + extra, h = stud_head_t + 0.01);
    }
}
