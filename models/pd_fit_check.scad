// =====================================================================
//  Fit checks for the Peak Design bracket
// =====================================================================
//
//  Not a printable model.  Each pose renders the material that the stud
//  would collide with, so scripts/cad/pd_fit_check.py can measure a
//  volume and decide pass or fail.  An empty result means "nothing in the
//  way"; a large result means "solidly blocked".  Which of those is the
//  pass depends on the pose - see the driver.
//
//  Include this after including the bracket with variant_render_mode set
//  to "none", so the bracket's own geometry and settings are in scope but
//  it does not draw itself.  Never copy the bracket's numbers in here:
//  during the visor mount's development three false test failures came
//  from check scripts holding stale duplicates.
//
// =====================================================================

// `check_id` selects the pose and is set by the driver before including
// this file.  It is deliberately NOT given a default here: a self-
// referencing default such as `check_id = is_undef(check_id) ? 0 :
// check_id` looks harmless but silently collapses to the fallback,
// which would make every check run the same pose.
//
// The latch deflection comes from the bracket's `lever_press`, likewise
// set by the driver.

lift_max   = 8.0;   // how far "escape" pulls the stud out, mm
sweep_step = 0.5;   // sampling interval along a swept path, mm


// The stud swept along the slot, from `from` to `to`.
//
// The neck and the head are swept SEPARATELY and then unioned.  Hulling
// the composite stud looks tempting and is wrong: hull() of a narrow neck
// and a wide head fabricates a conical wedge between them that does not
// exist, and the error grows with the sweep length.  That bug produced
// confident, entirely fictitious clearance numbers on the visor mount.
module swept_stud(from, to, extra = 0, lift = 0) {
    hull() {
        translate([0, from, -lift]) mirror([0, 0, 1])
            translate([0, 0, -stud_neck_h])
                cylinder(d = stud_neck_d + extra, h = stud_neck_h + 0.01);
        translate([0, to, -lift]) mirror([0, 0, 1])
            translate([0, 0, -stud_neck_h])
                cylinder(d = stud_neck_d + extra, h = stud_neck_h + 0.01);
    }
    hull() {
        translate([0, from, -lift]) mirror([0, 0, 1])
            translate([0, 0, -stud_neck_h - stud_head_t])
                cylinder(d = stud_head_d + extra, h = stud_head_t + 0.01);
        translate([0, to, -lift]) mirror([0, 0, 1])
            translate([0, 0, -stud_neck_h - stud_head_t])
                cylinder(d = stud_head_d + extra, h = stud_head_t + 0.01);
    }
}

// The stud pulled straight out of the locked position, as if the radio
// were yanked off the bracket.
//
// The pull is a straight line, so hulling the two end positions sweeps it
// exactly - no need to union a stack of copies.  Neck and head are still
// swept separately, for the reason given above.
module lifted_stud(extra = 0) {
    hull() {
        bracket_stud(0, extra, 0);
        bracket_stud(0, extra, lift_max);
    }
}


// ---------------------------------------------------------------------
//  0  seated   - stud parked in the locked position.
//                Pass = ~0.  Anything here is interference on assembly.
// ---------------------------------------------------------------------
if (check_id == 0) {
    intersection() { bracket(); bracket_stud(0); }
}

// ---------------------------------------------------------------------
//  1  slide    - stud run from the entry hole down to the lock.
//                Pass = small.  The only thing in the way should be the
//                latch tooth, which the neck pushes aside on its ramp.
// ---------------------------------------------------------------------
else if (check_id == 1) {
    intersection() { bracket(); swept_stud(travel, 0); }
}

// ---------------------------------------------------------------------
//  2  drop     - head pushed in through the entry hole.
//                Pass = ~0.  The hole must swallow the head cleanly.
// ---------------------------------------------------------------------
else if (check_id == 2) {
    intersection() {
        bracket();
        hull() {
            bracket_stud(travel, 0, 0);
            bracket_stud(travel, 0, lift_max);
        }
    }
}

// ---------------------------------------------------------------------
//  3  escape   - stud yanked straight out while locked.
//                Pass = LARGE.  The ledge has to be squarely in the way;
//                this is the check that says the radio cannot fall off.
// ---------------------------------------------------------------------
else if (check_id == 3) {
    intersection() { bracket(); lifted_stud(); }
}

// ---------------------------------------------------------------------
//  4  rise     - stud pushed back up toward the entry hole, latch at
//                rest.  Pass = non-zero: the tooth must block it.
// ---------------------------------------------------------------------
else if (check_id == 4) {
    intersection() { bracket(); swept_stud(0, tooth_y1); }
}

// ---------------------------------------------------------------------
//  5  released - same rise, but with the latch deflected as if pressed.
//                Pass = ~0.  This is what proves the tooth is the ONLY
//                obstruction, so a thumb on the tab really does free the
//                radio rather than merely feeling like it should.
// ---------------------------------------------------------------------
else if (check_id == 5) {
    intersection() { bracket(); swept_stud(0, tooth_y1); }
}

// ---------------------------------------------------------------------
//  6  ledge    - material directly over the locked head.
//                Compared against check 7 to give a coverage percentage;
//                a low figure means the head could tilt out.
//
//                Deliberately measures the BODY only, not the latch.  The
//                tooth reaches into the neck slot, so counting it fills in
//                area that check 7's reference has subtracted, and the
//                ratio comes out above 100% - which is not just untidy but
//                actively misleading, because the latch is a moving part
//                and cannot be relied on to hold the head down.  Coverage
//                is a question about the fixed ledge.
// ---------------------------------------------------------------------
else if (check_id == 6) {
    intersection() {
        bracket_body();
        cylinder(d = stud_head_d, h = ledge_t);
    }
}

// ---------------------------------------------------------------------
//  7  disc     - the reference the ledge is measured against: a full
//                cylinder over the head, MINUS the neck slot, since no
//                keyhole can ever cover that.  Comparing against a solid
//                disc instead would report a permanent, unfixable
//                shortfall - which it did, until this was corrected.
// ---------------------------------------------------------------------
else if (check_id == 7) {
    difference() {
        cylinder(d = stud_head_d, h = ledge_t);
        translate([0, 0, -0.01])
            rotate([0, 0, 90]) capsule(travel, neck_w, ledge_t + 0.02);
    }
}

// ---------------------------------------------------------------------
//  8  clash    - body and latch overlapping, with the latch deflected.
//                Pass = the flexure's own footprint and nothing more.
//                More than that means the latch is jammed against the
//                plate and cannot actually be pressed.
// ---------------------------------------------------------------------
else if (check_id == 8) {
    intersection() { bracket_body(); bracket_lever(); }
}

else {
    assert(false, str("unknown check_id: ", check_id));
}
