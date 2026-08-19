// =====================================================================
//  Fit-check geometry - not a printable part
// =====================================================================
//
//  Included by a small generated wrapper that first includes one of the
//  real variant files, so these checks always run against exactly what
//  gets printed.  Earlier versions duplicated the variant settings here,
//  which let the checks drift away from the actual models.
//
//  The wrapper sets check_id before including this file:
//
//      0 = seated   stud parked in the locked position
//      1 = slide    stud swept from the entry hole to the lock
//      2 = drop     stud dropping in through the entry hole
//      3 = escape   stud pulled straight out while locked
//      4 = stud     the stud on its own, as a reference volume
//      5 = preview  cutaway with the stud shown locked in place
//      6 = ledge    material directly over the locked head
//      7 = disc     the most ledge a keyhole could have there
//
// =====================================================================

module fc_socket() {
    socket_only();
}

// The stud swept along its path.  The neck and the head are swept
// SEPARATELY and then combined.
//
// Hulling the whole stud at both ends would be wrong: hull() of a
// composite shape fills in the wedge between the head at one end and the
// narrower neck at the other, and that phantom wedge grows with travel.
// It would show up as the slide path being "obstructed" purely because
// the slot got longer.
module fc_swept(from, to, lift_from = 0, lift_to = 0) {
    hull() {
        socket_place() translate([from, 0, lift_from])
            translate([0, 0, -stud_neck_h])
                cylinder(d = stud_neck_d, h = stud_neck_h + 0.01);
        socket_place() translate([to, 0, lift_to])
            translate([0, 0, -stud_neck_h])
                cylinder(d = stud_neck_d, h = stud_neck_h + 0.01);
    }
    hull() {
        socket_place() translate([from, 0, lift_from])
            translate([0, 0, -stud_neck_h - stud_head_t])
                cylinder(d = stud_head_d, h = stud_head_t + 0.01);
        socket_place() translate([to, 0, lift_to])
            translate([0, 0, -stud_neck_h - stud_head_t])
                cylinder(d = stud_head_d, h = stud_head_t + 0.01);
    }
}

module fc_stud_at(pos, lift = 0) {
    socket_place() stud_local(pos, 0, lift);
}

// A disc the size of the stud head, occupying the ledge directly above
// the locked head.
module fc_ledge_disc() {
    socket_place()
        translate([0, 0, -stud_neck_h + 0.05])
            cylinder(d = stud_head_d, h = ledge_t - 0.1);
}

// The most ledge any working keyhole could have: that disc minus the neck
// slot, which has to run through the ledge for the stud to get in at all.
// Comparing against a solid disc would fail every correct design.
module fc_ledge_reference() {
    difference() {
        fc_ledge_disc();
        socket_place()
            translate([0, 0, -stud_neck_h - 1])
                hull() {
                    cylinder(d = neck_w, h = ledge_t + 2);
                    translate([entry_off, 0, 0])
                        cylinder(d = neck_w, h = ledge_t + 2);
                }
    }
}

if (check_id == 0) {
    // Overlap should be nil - the preload is a designed interference that
    // only bites once the radio is pulled onto the mount.
    intersection() { fc_socket(); fc_stud_at(0); }

} else if (check_id == 1) {
    // The only thing in the sliding path should be the detent bump.
    intersection() { fc_socket(); fc_swept(0, entry_off); }

} else if (check_id == 2) {
    // Same story dropping in through the entry hole.
    intersection() { fc_socket(); fc_swept(entry_off, entry_off, 0, 20); }

} else if (check_id == 3) {
    // Pulling straight out while locked MUST be blocked by the ledge, so
    // a large overlap here is the pass condition.
    intersection() { fc_socket(); fc_swept(0, 0, 0, 20); }

} else if (check_id == 4) {
    fc_stud_at(0);

} else if (check_id == 5) {
    difference() {
        union() { fc_socket(); fc_stud_at(0); }
        translate(lengthwise ? [-200, jaw_ctr_y, -200] : [jaw_ctr_x, -200, -200])
            cube([400, 400, 400]);
    }

} else if (check_id == 6) {
    intersection() { fc_socket(); fc_ledge_disc(); }

} else if (check_id == 7) {
    fc_ledge_reference();

} else {
    assert(false, str("unknown check_id: ", check_id));
}
