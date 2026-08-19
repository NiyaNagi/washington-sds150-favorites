// =====================================================================
//  SDS150 visor mount - shared parametric library
// =====================================================================
//
//  Replaces the radio-mounting block of the "Slim Radio mount" with a
//  captive keyhole socket for the Uniden SDS150 belt-clip stud.
//
//  DO NOT render this file directly.  Render one of:
//      sds150_visor_mount_lengthwise.scad   (slot runs along radio length)
//      sds150_visor_mount_crosswise.scad    (slot runs across radio width)
//
//
//  HOW THE ORIGINAL IS REUSED
//  --------------------------
//  The source mount is a C-clamp: a lower jaw at Z -19.8..-14.9 and an
//  upper jaw at Z 3.0..8.0, with the old radio block stacked on top of
//  that upper jaw.  We import the source whole and trim everything above
//  Z = 8.0, which keeps the entire clamp and discards only the block.
//
//  The new block is then grown straight off the jaw's top face, using
//  that face's own outline (taken by projecting the mesh, so it matches
//  exactly and follows the original's rounded corners).  The block tapers
//  inward as it rises and its top edges are chamfered, so it reads as a
//  continuation of the part rather than a slab bolted on.
//
//
//  HOW THE LATCH WORKS
//  -------------------
//  1. The radio's raised pedestal drops into a rectangular pocket in the
//     top of the block.  Because that pocket is rectangular and the
//     pedestal is 25 x 35mm, the radio cannot rotate.
//  2. The stud's wide head passes down through the round entry hole into
//     a hidden channel, pressing down a sprung tongue on the way.
//  3. Slide the radio along the slot.  The head runs under a ledge; the
//     narrow neck runs in the slot above it.
//  4. At the end of travel the head clears the tongue, which springs back
//     up.  Its bump now blocks the return path.  The radio is captive.
//  5. The radio's weight pulls the head up against the ledge.  The ledge
//     is deliberately a hair thinner than the stud neck, so the head
//     clamps it against the pedestal - that clamp is what kills wobble.
//  6. To remove: slide the radio back the way it came.  A deliberate firm
//     pull rides the head back over the detent, then it lifts out through
//     the entry hole.  There is no release button - see section 4 for why.
//
//  Coordinates match the original mesh.  +Z points away from the visor,
//  i.e. downwards when installed, since the radio hangs below.
//
// =====================================================================


// ---------------------------------------------------------------------
//  1. THE STUD, AND HOW IT IS CAPTURED
// ---------------------------------------------------------------------
//
//  Stud dimensions, fit clearances and the keyhole geometry all live in
//  sds150_stud.scad, shared with the Peak Design bracket.  Edit them
//  there, not here - two copies would drift apart, which during
//  development of this mount caused three separate false test failures.
//
//  That file defines, among others:
//      stud_head_d, stud_head_t, stud_neck_d, stud_neck_h
//      boss_w, boss_l, boss_h, boss_stud_off_l, boss_stud_off_w
//      preload, clr_slide, hole_comp, clr_boss, shrink_comp
//      ledge_t, head_ch_h, entry_d, head_ch_w, neck_w, min_travel

include <sds150_stud.scad>


// ---------------------------------------------------------------------
//  3. BLOCK SHAPE
// ---------------------------------------------------------------------

// How far the radio slides to lock.
//
// This must be long enough that the stud head ends up entirely clear of
// the entry hole - otherwise part of the head still sits under an open
// hole and can lift and tilt free.  The head only just clears at
//     (entry_d + stud_head_d) / 2  =  (16.35 + 15.5) / 2  =  15.93 mm
// so the default adds ~1.5mm of margin on top.  Verify any change with
// scripts/cad/check_travel.py.
slot_travel      = 17.5;   // mm
base_t           = 1.6;    // solid floor under the tongue's flex void, mm
wall             = 3.6;    // material around the socket cavity, mm
pocket_wall      = 2.4;    // material around the pedestal pocket, mm

// Pocket that captures the radio's pedestal.  This is what stops the
// radio rotating, so leave it on unless it fouls something.
capture_boss     = true;
skirt_h          = 3.0;    // pocket depth, mm.  Must be less than boss_h.

// The block follows the clamp's own outline, so its sides sit flush and
// there is no visible seam.  With the footprint now built from an exact
// rectangle rather than a projected section, no inset is needed: the two
// match to the micron, so there is nothing to oversail.
taper            = 0.0;    // inset from the clamp outline, mm
top_round        = 3.0;    // radius of the rounded top edge, mm
round_steps      = 10;     // facets used to build that rounding


// ---------------------------------------------------------------------
//  4. RETENTION DETENT
// ---------------------------------------------------------------------
//
//  Two latch styles are available, selected by the wrapper file.
//
//  latch_style = "click"   (variants 1 and 2)
//  -------------------------------------------
//  A bump on a sprung tongue, ramped on BOTH sides.  The stud head presses
//  the tongue down as it rides over the bump going in, the tongue springs
//  back behind it, and a deliberate firm pull rides back over it coming
//  out.  Exactly how a belt clip behaves.  Nothing to break.
//
//  latch_style = "lever"   (variants 3 and 4)
//  -------------------------------------------
//  The same bump, but carried on a rigid arm hinged by a compliant
//  flexure, with a tab reaching out past the block edge.  Press the tab
//  down and the bump retracts, so the radio slides straight off.
//
//  Why a flexure hinge and not a plain cantilever: a uniform cantilever
//  deflects as x^2(3L-x), so a point partway along moves far less than the
//  tip.  A first attempt with a plain sprung tab failed for exactly that
//  reason - pressing the tab moved the bump only about a third as much,
//  and the tab bottomed out before the bump had retracted far enough.
//
//  Concentrating all the compliance into one short thin ligament - a
//  "small-length flexural pivot" - makes the arm rotate as a rigid body
//  instead.  Displacement is then LINEAR in distance from the pivot, and
//  all the strain lives in one place where it can be checked.  See
//  scripts/cad/design_lever.py, which sizes the flexure and reports the
//  strain, press force and holding force.
//
//  The detent does not carry the radio's weight in either style; the ledge
//  does.  It only has to resist vibration along the slot.

tongue_t         = 2.4;    // spring thickness - stiffness lives here, mm
tongue_gap       = 2.4;    // room beneath the tongue to flex into, mm
tongue_relief    = 1.20;   // side gap that frees the tongue, mm

detent_bump      = 1.40;   // how far the bump rises into the channel, mm
detent_crest     = 1.20;   // flat top of the bump, mm
detent_ramp      = 4.00;   // lead-in ramp, entry side, mm
detent_exit      = 2.60;   // exit ramp - shorter, so it holds harder than
                           // it inserts, but still releases with a pull
detent_standoff  = 0.50;   // gap between locked head and the bump, mm


// ---- compliant lever release, used when latch_style = "lever" --------

// Flexure hinge.  Thickness is the main tuning knob: thicker holds the
// detent more firmly but strains more when pressed.  PLA is not a
// living-hinge material, so keep peak strain under about 0.8% for daily
// use - design_lever.py reports it.
//
// The flexure is made as WIDE as the arm rather than narrow: width adds
// stiffness and strength in proportion, but strain depends only on
// thickness and length.  So a wide thin ligament is both robust and
// low-strain, where a narrow one would simply be fragile.
flex_offset      = 6.0;    // pivot sits this far behind the chamber, mm
flex_len         = 5.0;    // flexure length, mm
flex_t           = 1.3;    // flexure thickness, mm
flex_root        = 3.0;    // how far the flexure is buried in the wall, mm

// The arm.  Wider than the head channel and ribbed down each side, so
// that essentially all the bending happens at the flexure.  A slender arm
// would just flex along its length, which is the failure mode the flexure
// exists to avoid.
arm_w            = 22.0;   // arm width, mm
rib_w            = 2.0;    // stiffening rib width, mm
rib_h            = 1.8;    // how far the ribs stand down, mm

// The push tab.
tab_protrude     = 10.0;   // how far it reaches past the block edge, mm
tab_w            = 10.0;   // width, mm.  Must be under head_ch_w so the
                           // stud head can never escape through its slot.
tab_lip          = 2.0;    // upstand at the tip so a finger catches it, mm
tab_clearance    = 4.0;    // headroom in the wall slot for it to swing, mm


// ---------------------------------------------------------------------
//  5. SOURCE PART AND ASSEMBLY
// ---------------------------------------------------------------------

arm_stl          = "slim_radio_mount_source.stl";

// Z plane where the old radio-mounting block is trimmed away.  The
// original is a C-clamp with a lower jaw at Z -19.8..-14.9 and an upper
// jaw at Z 3.0..8.0; the old block sat on top of that upper jaw.
//
// The cut is taken at 7.0 rather than 8.0 because the jaw's top edge is
// ROUNDED OVER: it measures 59.90mm wide at Z 7.0 but only 58.15mm at
// Z 7.99.  Cutting at the very top would leave the new block overhanging
// that rounding by about 0.4mm per side - a thin lip running down each
// side of the part, clearly visible in a slicer.  Cutting at 7.0 removes
// the fillet and lands on full-width material, so the join is flush.
//
// Do not lower this to 3.0 - that is the UNDERSIDE of the upper jaw, and
// cutting there removes a jaw of the clamp entirely.
arm_top_z        = 7.0;    // mm

// Extents of the jaw's top face, measured by scripts/cad/probe_jaw.py.
// The block's outline is projected from the mesh so it always matches;
// these are only used to work out where the release tab reaches the edge.
jaw_x_lo         = -29.85;
jaw_x_hi         =  29.85;
jaw_y_lo         = -37.45;
jaw_y_hi         =  27.40;

// Which end of the slot the release tab pokes out of: +1 or -1 along the
// slide axis.  The wrappers set this to whichever end is easiest to reach.
tab_end          = 1;

// Set by the wrapper files.  Do not edit here.
//   variant_slide_axis  : "lengthwise" | "crosswise"
//   variant_latch_style : "click" | "lever"
//   variant_render_mode : "assembly" | "socket_only" | "coupon" | "section"
//                       | "none"
slide_axis  = is_undef(variant_slide_axis)  ? "lengthwise" : variant_slide_axis;
latch_style = is_undef(variant_latch_style) ? "click"      : variant_latch_style;
render_mode = is_undef(variant_render_mode) ? "assembly"   : variant_render_mode;

$fa = 2;
$fs = 0.4;


// =====================================================================
//  DERIVED VALUES - computed, not edited
// =====================================================================

// ledge_t, head_ch_h, entry_d, head_ch_w and neck_w all come from
// sds150_stud.scad, along with the shrink compensation applied to them.

plate_t     = ledge_t + head_ch_h + tongue_t + tongue_gap + base_t;
block_h     = plate_t + (capture_boss ? skirt_h : 0);

// Layer boundaries, measured down from the bearing face at z = 0.
z_ledge     = -ledge_t;                   // underside of the ledge
z_chan      = z_ledge - head_ch_h;        // top of the tongue
z_tongue    = z_chan - tongue_t;          // underside of the tongue
z_void      = z_tongue - tongue_gap;      // floor of the flex void

// The stud sits at the origin when locked, and the entry hole is
// slot_travel away along +X.  Everything in the socket's local frame is
// built with +X pointing at the entry hole and the release tab; the
// tab_end flip is applied once, in socket_place().  Handling it in more
// than one place is what previously put the tab slot on the wrong side
// and fused the lever to the block.
entry_off   = slot_travel;

// Chamber holding the head channel, the tongue, and the void it flexes
// into.  Closed at the lock end, and just past the entry hole.
chan_w      = head_ch_w + 2 * tongue_relief;
chan_back   = head_ch_w / 2;
chan_front  = entry_off + entry_d / 2 + 0.5;

// The detent bump sits just outside the locked head.
bump_x      = head_ch_w / 2 + detent_standoff;

// Pedestal pocket, sized so the pedestal can traverse the full travel,
// and offset so it never touches a wall at either end of that travel.
lengthwise    = (slide_axis == "lengthwise");
boss_along    = lengthwise ? boss_l : boss_w;
boss_across   = lengthwise ? boss_w : boss_l;
boss_off_a    = lengthwise ? boss_stud_off_l : boss_stud_off_w;
boss_off_c    = lengthwise ? boss_stud_off_w : boss_stud_off_l;

pocket_along  = boss_along + slot_travel + 2 * clr_boss;
pocket_across = boss_across + 2 * clr_boss;

// Pedestal centre relative to the stud, midway through the travel.
pocket_ctr_a  = entry_off / 2 - boss_off_a;
pocket_ctr_c  = -boss_off_c;

// Centre of the jaw's top face; the socket is placed on it so the block
// stays balanced over the clamp.
jaw_ctr_x = (jaw_x_lo + jaw_x_hi) / 2;
jaw_ctr_y = (jaw_y_lo + jaw_y_hi) / 2;

bearing_z = arm_top_z + block_h;          // face the radio rests on

// ---- compliant lever geometry ---------------------------------------
lever = (latch_style == "lever");

// Pivot sits behind the chamber's closed end, so the arm is long and the
// rotation needed is small.
pivot_x   = -(chan_back + flex_offset);
arm_start = pivot_x + flex_len;

// Where the tab passes out through the block wall, and where it ends.
//
// The wall has to be located from the block's actual outline, not from
// the end of the chamber - there can be a lot of solid block between the
// two, and measuring from the chamber would leave the tab barely proud of
// the surface.  In the tongue's own frame +X points at the entry hole and
// the tab, so this is the distance from the socket origin out to the wall
// on that side.
axis_lo     = lengthwise ? jaw_x_lo : jaw_y_lo;
axis_hi     = lengthwise ? jaw_x_hi : jaw_y_hi;
axis_ctr    = (axis_lo + axis_hi) / 2;

// socket_place() shifts by -pocket_ctr_a in the socket's own frame, and
// that frame is flipped when tab_end is negative, so the shift lands on
// the opposite side in global terms.
origin_axis = axis_ctr - tab_end * pocket_ctr_a;

block_edge = tab_end > 0 ? (axis_hi - taper) - origin_axis
                         : origin_axis - (axis_lo + taper);

tab_exit  = block_edge;
tab_tip   = block_edge + tab_protrude;

// Lever arms, and how far the tab must travel to retract the bump.
arm_bump   = bump_x - pivot_x;
arm_tab    = tab_tip - pivot_x;
lever_gain = arm_bump / arm_tab;
tab_travel = detent_bump / lever_gain;

// The lever's arm is wider than the head channel, so its chamber has to
// be wider too, with clearance all round for it to move.
lever_chan_w = arm_w + 2 * tongue_relief;

// The arm must not touch the chamber floor before the bump has cleared.
// Deflection grows linearly with distance from the pivot, so the worst
// point inside the chamber is at its far end.
swing_at_chamber_end = tab_travel * (tab_exit - pivot_x) / arm_tab;

echo(str("VARIANT=", slide_axis, "/", latch_style, "  mode=", render_mode,
         "  block_h=", block_h, "  plate_t=", plate_t,
         "  ledge_t=", ledge_t, "  entry_d=", entry_d,
         "  neck_w=", neck_w, "  head_ch_w=", head_ch_w,
         "  slot_travel=", slot_travel));

if (lever)
    echo(str("  LEVER  gain=", lever_gain,
             "  tab_travel=", tab_travel,
             "  swing_in_chamber=", swing_at_chamber_end,
             "  gap=", tongue_gap,
             "  block_edge=", block_edge,
             "  tab_tip=", tab_tip));

assert(skirt_h < boss_h, "skirt_h must be less than boss_h");
assert(neck_w < head_ch_w, "neck slot must be narrower than the head");
assert(ledge_t < stud_neck_h, "ledge must be thinner than the stud neck");
assert(slot_travel > 0, "slot_travel must be positive");
assert(abs(tab_end) == 1, "tab_end must be +1 or -1");

// The locked head must end up entirely clear of the entry hole, or part
// of it still sits under an open hole and can lift and tilt free.
assert(slot_travel >= (entry_d + stud_head_d) / 2,
       "slot_travel is too short - the stud head would still overlap the entry hole");

assert(latch_style == "click" || latch_style == "lever",
       "latch_style must be \"click\" or \"lever\"");

// The tab's slot through the block wall must be too narrow for the stud
// head, or the head could escape sideways through it.
assert(!lever || tab_w < stud_head_d,
       "tab_w must be narrower than the stud head");

// Pressing the tab must retract the bump before the arm hits the floor.
assert(!lever || swing_at_chamber_end < tongue_gap + rib_h - 0.3,
       "lever arm would bottom out before releasing - increase tongue_gap");

// The arm needs clearance around it inside its chamber.
assert(!lever || arm_w + 2 * tongue_relief <= lever_chan_w + 0.001,
       "lever chamber is narrower than the arm");
assert(!lever || rib_h < tongue_gap,
       "stiffening ribs are deeper than the void they hang in");

// The flexure root must be fully buried in solid block, or the hinge is
// anchored to thin air and will simply tear away.  A long slot pushes the
// socket along the block, which can walk the pivot out past the far wall.
back_edge = tab_end > 0 ? origin_axis - (axis_lo + taper)
                        : (axis_hi - taper) - origin_axis;

assert(!lever || back_edge >= -pivot_x + flex_root + 1.0,
       str("flexure root is not fully buried - only ",
           back_edge - (-pivot_x), " mm of block behind the pivot, needs ",
           flex_root + 1.0, " mm.  Reduce flex_offset or slot_travel."));


// =====================================================================
//  MODULES
// =====================================================================

// The original mount with its old radio block trimmed away, leaving just
// the C-clamp that grips the visor.
module visor_clamp() {
    difference() {
        import(arm_stl, convexity = 10);
        translate([-200, -200, arm_top_z]) cube([400, 400, 400]);
    }
}

// Footprint of the block.
//
// These are the clamp's own measured dimensions at the trim plane, so the
// block's side walls continue the clamp's exactly and there is no step or
// lip at the join.  Measured with scripts/cad/check_joint.py.
//
// An earlier version projected the mesh section and re-rounded it with
// offset(r)/offset(-r); that could not reproduce the original outline and
// left the wall wandering by about 0.4mm along its length - visible as
// shallow dents down each side.
block_face_x = 59.90;      // clamp width at the trim plane, mm
block_face_y = 65.60;      // clamp length at the trim plane, mm
block_face_r = 2.00;       // corner radius, matching the original, mm
block_face_ctr_y = -4.65;  // its centre, mm

module jaw_profile() {
    translate([0, block_face_ctr_y])
        offset(r = block_face_r)
            square([block_face_x - 2 * block_face_r,
                    block_face_y - 2 * block_face_r], center = true);
}

// The block, grown straight off the jaw with matching sides, then rounded
// over at the top edge so it reads as one continuous part.
//
// The rounding is built as a stack of thin lofted layers following a
// quarter circle.  The first layer is dropped below the shoulder so it
// genuinely overlaps the body: if the two only met on a coincident face,
// CGAL would leave them as separate solids joined by sliver triangles.
module block_solid() {
    straight = block_h - top_round;
    overlap  = 0.6;

    translate([0, 0, arm_top_z]) {
        // Body: the jaw's own outline, extruded upward.
        linear_extrude(height = straight)
            offset(r = -taper) jaw_profile();

        // Top edge rolled over on a quarter circle.
        translate([0, 0, straight])
            for (i = [0 : round_steps - 1]) {
                a0 = i * 90 / round_steps;
                a1 = (i + 1) * 90 / round_steps;
                z0 = top_round * sin(a0) - (i == 0 ? overlap : 0);
                z1 = top_round * sin(a1);
                r0 = top_round * (1 - cos(a0));
                r1 = top_round * (1 - cos(a1));
                hull() {
                    translate([0, 0, z0])
                        linear_extrude(height = 0.01)
                            offset(r = -taper - r0) jaw_profile();
                    translate([0, 0, z1])
                        linear_extrude(height = 0.01)
                            offset(r = -taper - r1) jaw_profile();
                }
            }
    }
}

// capsule() comes from sds150_stud.scad.

// Pocket that swallows the radio's raised pedestal, blocking rotation.
module boss_pocket() {
    translate([pocket_ctr_a, pocket_ctr_c, -0.01])
        linear_extrude(height = skirt_h + 0.02)
            offset(r = 1.5) offset(r = -1.5)
                square([pocket_along, pocket_across], center = true);
}

// The rectangular cavity holding the head channel, the tongue or rocker,
// and the void it flexes into.
//
// With the lever latch it runs the whole way out to the block wall, so
// the arm is surrounded by air along its entire length.  If it stopped at
// the entry hole the arm would be buried in solid material beyond that
// point and the mechanism would be a lump.
module chamber() {
    back  = lever ? -pivot_x : chan_back;
    front = lever ? tab_exit + 1.0 : chan_front;
    width = lever ? lever_chan_w : chan_w;

    translate([-back, -width / 2, z_void])
        cube([front + back, width, z_ledge - z_void]);
}

// Slot through the block wall that lets the push tab reach the outside,
// and gives it room to swing down.  Deliberately narrower than the stud
// head, so the head can never escape through it.
module tab_slot() {
    slot_w = tab_w + 2 * tongue_relief;
    translate([tab_exit - 1.0, -slot_w / 2, z_tongue - tab_clearance])
        cube([tab_protrude + 3.0, slot_w,
              tongue_t + tab_clearance + tab_lip + 1.0]);
}

// Neck slot through the ledge, plus the round entry hole.  Both open
// through the bearing face and drop into the chamber below.
module stud_void() {
    translate([0, 0, z_ledge - 0.01])
        capsule(entry_off, neck_w, ledge_t + skirt_h + 1.02);
    translate([entry_off, 0, z_ledge - 0.01])
        cylinder(d = entry_d, h = ledge_t + skirt_h + 1.02);
}

// The detent bump itself, ramped on both sides.  `exit` sets how steeply
// it resists coming back out.
module detent_solid(width, rise, exit) {
    translate([0, width / 2, 0]) rotate([90, 0, 0])
        linear_extrude(height = width)
            polygon([
                [bump_x - exit,                        z_chan],
                [bump_x,                               z_chan + rise],
                [bump_x + detent_crest,                z_chan + rise],
                [bump_x + detent_crest + detent_ramp,  z_chan],
            ]);
}

// CLICK latch: a plain sprung tongue anchored in the closed end wall of
// the chamber, carrying the detent bump.  The stud head rides over the
// bump in both directions, pressing the tongue down as it passes.
module tongue_click() {
    tw    = head_ch_w;
    root  = -chan_back - 3.0;
    reach = chan_front - 1.0;

    // Beam, buried at its root in the end wall.
    translate([root, -tw / 2, z_tongue])
        cube([reach - root, tw, tongue_t]);

    detent_solid(tw, detent_bump, detent_exit);
}

// LEVER latch: the same bump on a stiff arm, hinged by a short thin
// flexure so the arm rotates rather than bending along its length.  A tab
// reaches out past the block edge; pressing it down retracts the bump.
//
// The arm is made WIDER than the head channel, and given stiffening ribs
// down each side, so that all of the bending happens at the flexure and
// none along the arm.  A slender uniform arm would simply flex, which is
// the failure the flexure exists to avoid.
module tongue_lever() {
    aw = arm_w;

    // Flexure, centred in the arm's thickness and buried at its root in
    // the back wall so the joint is solid.
    translate([pivot_x - flex_root, -aw / 2,
               z_tongue + (tongue_t - flex_t) / 2])
        cube([flex_len + flex_root, aw, flex_t]);

    // Stiff arm, from the flexure out through the wall to the tab.
    translate([arm_start, -aw / 2, z_tongue])
        cube([tab_exit - arm_start, aw, tongue_t]);

    // Stiffening ribs along the arm, standing down into the flex void so
    // they do not foul the stud head passing overhead.
    for (side = [-1, 1])
        translate([arm_start, side * (aw / 2 - rib_w), z_tongue - rib_h])
            cube([tab_exit - arm_start, rib_w, rib_h + 0.01]);

    // Tab, narrowed so it fits its slot, reaching out past the block.
    translate([tab_exit - 1.0, -tab_w / 2, z_tongue])
        cube([tab_protrude + 1.0, tab_w, tongue_t]);

    // Upstand at the tip so a fingertip catches it.
    translate([tab_tip - tab_lip, -tab_w / 2, z_tongue])
        cube([tab_lip, tab_w, tongue_t + tab_lip]);

    detent_solid(head_ch_w, detent_bump, detent_exit);
}

module tongue() {
    if (lever) tongue_lever();
    else       tongue_click();
}

// Places socket-local geometry onto the jaw, oriented for the chosen
// slide axis and centred so the pedestal pocket sits over the jaw.
//
// Socket-local geometry is always built with +X pointing at the entry
// hole and the release tab.  The tab_end flip is applied HERE and only
// here - doing it inside individual modules as well previously put the
// tab slot on the opposite side from the tab, which fused the lever to
// the block.
module socket_place() {
    translate([jaw_ctr_x, jaw_ctr_y, bearing_z])
        rotate([0, 0, lengthwise ? 0 : 90])
            rotate([0, 0, tab_end > 0 ? 0 : 180])
                translate([-pocket_ctr_a, -pocket_ctr_c, 0])
                    children();
}

// Everything cut out of the block.
module block_cavities() {
    socket_place() {
        if (capture_boss) boss_pocket();
        chamber();
        if (lever) tab_slot();
        stud_void();
    }
}

// Full part: the original visor clamp with the new socket block on top.
module mount() {
    union() {
        difference() {
            union() {
                visor_clamp();
                block_solid();
            }
            block_cavities();
        }
        socket_place() tongue();
    }
}

// Just the block, without the visor clamp below it.  The tongue is part
// of the block: leaving it out would hide the detent from the fit checks,
// which would then report the slide path as clear when it is not.
module socket_only() {
    union() {
        intersection() {
            difference() {
                union() { visor_clamp(); block_solid(); }
                block_cavities();
            }
            translate([-200, -200, arm_top_z]) cube([400, 400, 400]);
        }
        socket_place() tongue();
    }
}

// Small standalone test print for dialling in the fit before committing to
// a full-size print.  It is the block cropped to just the socket region,
// so it carries the real keyhole, ledge, tongue and release tab while
// using a fraction of the filament.
coupon_margin = 10.0;   // material kept around the socket features, mm

module coupon() {
    // Extent to keep, measured along the slide axis from the locked stud:
    // back past the closed end or the flexure anchor, forward past the
    // entry hole and the push tab.
    keep_back  = (lever ? -pivot_x : chan_back) + coupon_margin;
    keep_front = (lever ? tab_tip : chan_front) + coupon_margin;
    keep_w     = chan_w + 2 * coupon_margin;

    translate([0, 0, -arm_top_z])
        intersection() {
            union() {
                difference() {
                    intersection() {
                        union() { visor_clamp(); block_solid(); }
                        translate([-200, -200, arm_top_z])
                            cube([400, 400, 400]);
                    }
                    block_cavities();
                }
                socket_place() tongue();
            }
            socket_place()
                translate([tab_end > 0 ? -keep_back : -keep_front,
                           -keep_w / 2, -block_h - 1])
                    cube([keep_back + keep_front, keep_w, block_h + 2]);
        }
}

// The stud, in the socket's local frame, at position `pos` along the
// slide axis.  pos = 0 is locked, pos = entry_off is under the entry
// hole.  `lift` raises it, for testing whether it can escape upwards.
// The shape itself is stud_solid(), from sds150_stud.scad.
module stud_local(pos = 0, extra = 0, lift = 0) {
    stud_solid(pos, extra, lift);
}

// Same, transformed onto the assembled mount.  Used by the fit harness.
module stud_positioned(pos = 0, extra = 0, lift = 0) {
    socket_place() stud_local(pos, extra, lift);
}


// Lay the part in its PRINT orientation: on its side, resting on the
// build plate.
//
// This is not cosmetic.  The C-clamp's profile is then drawn within each
// layer, so it does not split when it springs over the visor, and the
// lever's flex void becomes a vertical slot.  Laid flat instead, that
// void is a horizontal gap with the arm hovering over it - about
// 3900 mm^2 of floating surface that a slicer can only build on support,
// which would weld the mechanism solid.
//
// Which way round depends on where the release tab leaves the block, so
// print_flip lets a variant turn the part over.  Always confirm a change
// with scripts/cad/check_printable.py, which compares all orientations
// and reports the unsupported area of each.
print_flip = false;

module print_oriented() {
    translate([0, 0, 30])
        rotate([0, print_flip ? -90 : 90, 0])
            children();
}


// =====================================================================
//  ENTRY POINT
// =====================================================================

if (render_mode == "assembly") {
    print_oriented() mount();

} else if (render_mode == "socket_only") {
    socket_only();

} else if (render_mode == "coupon") {
    print_oriented() coupon();

} else if (render_mode == "assembly_unrotated") {
    // As modelled, for the checks that reason in model coordinates.
    mount();

} else if (render_mode == "section") {
    // Cut along the slide axis so the keyhole and tongue are exposed.
    difference() {
        mount();
        if (lengthwise) translate([-200, jaw_ctr_y, -200]) cube([400, 400, 400]);
        else            translate([jaw_ctr_x, -200, -200]) cube([400, 400, 400]);
    }

} else if (render_mode == "none") {
    // Library only - the including file draws its own geometry.

} else {
    assert(false, str("unknown render_mode: ", render_mode));
}
