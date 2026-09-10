// =====================================================================
//  ProClip radio mounting plates
// =====================================================================
//
//  Six rigid plates that bolt to a Brodit/ProClip vehicle mount through
//  its AMPS hole pattern, and carry a handheld radio on the front:
//
//      variant "sds"       Uniden SDS150, gravity keyhole on its lug
//      variant "clip"      Kenwood TH-D75A / generic belt-clip bridge
//      variant "combined"  both, side by side on one plate
//
//  each in two hole orientations:
//
//      amps_orientation "landscape"   38.05 across, 30.17 up
//      amps_orientation "portrait"    30.17 across, 38.05 up
//
//  3 variants x 2 orientations = the six designs.
//
//  FRAME.  X runs across the car, Z runs up, Y runs out of the ProClip
//  plate toward the cabin.  The bearing face - the face that lies flat
//  against the ProClip - is y = 0.  Both radios face +Y, upright,
//  displays outward, antennas up.  Gravity is -Z, which is what retains
//  the SDS150: its entry hole sits above its locked position.
//
//  PRINT flat on the bearing face, no supports.  That puts the plate's
//  layers in its strongest orientation for bending, and it is why the
//  stud head channel carries the flat-plate bridge allowance rather than
//  the shared baseline - see proclip_head_clr_extra.
//
//  Units are mm.
//
//  UNVERIFIED.  The AMPS pattern below is the published industry
//  standard and is the only part of the ProClip interface that is
//  documented anywhere.  Brodit additionally describes "two sets of
//  double-holes placed in different height" whose spacing they do not
//  publish, and neither the plate outline, its thickness, nor its hole
//  diameters could be sourced.  Nothing here has been offered up to a
//  physical mount.  Print the gauge first.
//

include <../sds150_stud.scad>

// =====================================================================
//  1. FIT
// =====================================================================

// Identical to the Peak Design standoff, so its printed coupon results
// carry straight over.  Do not diverge these without re-running a coupon.
standoff_preload     = 0.05;
standoff_clr_slide   = 0.35;
standoff_hole_comp   = 0.25;
standoff_ledge_scale = 0.70;

// This is a flat plate printed face-down, so the head channel's roof is
// an unsupported bridge and sags into the very gap the head slides in.
// The Peak Design BRACKET is the same situation and 0.25 is its proven
// value; the standoff is not, because its channel prints vertically.
// Derived from the shared baseline so the two cannot drift apart.
proclip_head_clr_extra = 0.25;
proclip_head_clr_z     = head_ch_clr_z_base + proclip_head_clr_extra;

sds_travel = 19.0;

// =====================================================================
//  2. TO SUIT - external interfaces
// =====================================================================

// AMPS: the published 4-hole standard, 30.17 x 38.05 centre-to-centre.
// This is what a ProClip mounting plate carries and what the M4s go
// through.  See docs/radio-hardware-measurements.md for provenance.
amps_long   = 38.05;
amps_short  = 30.17;
amps_orientation = "landscape";  // landscape | portrait

// M4 countersunk machine screw and nyloc nut.  Countersunk so the head
// finishes flush: the SDS150 pedestal slides directly over this face.
m4_clear_d   = 4.50;
m4_cs_head_d = 8.00;
m4_cs_angle  = 90;
m4_nut_af    = 7.00;
m4_nyloc_t   = 5.00;

// ProClip plate itself.  ESTIMATE ONLY - used to recommend a screw
// length, never to cut geometry.  The gauge exists to replace it.
proclip_plate_t_est = 5.00;

// =====================================================================
//  3. MEASURED RADIO ENVELOPES
// =====================================================================
//  Carried over from docs/radio-hardware-measurements.md unchanged.

sds_body_h        = 153.0;
sds_body_w        = 69.9;   // conservative repo envelope; sketch says 57
sds_body_d        = 40.0;
sds_lug_from_bottom = 108.0;
sds_mass_g        = 400.0;

thd_body_h        = 121.9;
thd_body_w        = 56.0;
thd_body_d        = 35.0;
thd_clip_w_max    = 21.3;
thd_clip_w_tip    = 17.6;
thd_clip_gap      = 4.5;
thd_clip_clear_h  = 30.0;
thd_mass_g        = 400.0;

uv5r_clip_env_w   = 32.0;   // published overall clip envelope, not jaw width

// =====================================================================
//  4. STRUCTURE
// =====================================================================

variant        = "sds";     // sds | clip | combined

plate_t        = 5.00;      // must swallow the countersink and still bear
plate_corner_r = 6.00;
plate_edge_ch  = 0.80;
plate_edge_wall = 3.00;     // material outboard of any raised feature
amps_wall      = 3.20;      // plate material around a countersunk head
amps_driver_clr = 1.60;     // open space around it for a driver bit

// SDS150 pedestal channel.  OFF, matching the Peak Design standoff: the
// pedestal bears on a flat pad and the lug ledge plus gravity retain it.
//
// The channel is a working option, not dead code - it is the only
// positive anti-rotation available on a round lug, and
// check_proclip_interface.py still proves it blocks a 3 degree twist
// when enabled.  It was switched off because it stands 3 mm proud beside
// the keyhole for a radio that is already held flat, and because the
// AMPS lands necessarily bite one of its two walls on the combined
// plate, leaving it visibly asymmetric.
//
// Turning it back on moves nothing else: sds_face_y - the face the
// pedestal bears on, and the datum the whole keyhole hangs from - is
// invariant, because the pad grows by exactly the channel's depth.
sds_guide      = false;
sds_guide_h    = 3.00;      // channel depth; pedestal stands 6.0 proud
sds_guide_clr  = 0.40;      // per side, matches clr_boss
sds_roof_min   = 1.60;      // solid material behind the head channel
sds_pad_wall   = 4.00;      // pad material beside the pedestal channel
sds_min_wall   = 1.20;      // the limit scripts/cad/inspect_stl.py enforces

// Belt-clip bridge.  Geometry is the standoff's proven bridge; only the
// frame changed.  clip_back_gap stays at the standoff's 7.0 even though
// there are no fork ears here to clear, because 7.0 is the number the
// measured Kenwood clip was actually swept against.
clip_bar_w       = 35.00;
clip_bar_h       = 25.00;
clip_bar_t       = 3.00;
clip_back_gap    = 7.00;
clip_rail_h      = 0.65;
clip_collar_w    = 1.40;
clip_support_w   = 2.80;
clip_inner_clear = thd_clip_w_max + 1.0;   // 22.3, centres the Kenwood
clip_outer_clear = uv5r_clip_env_w + 1.0;  // 33.0, outer end stops
clip_clear_below = thd_clip_clear_h;
clip_amps_gap    = 2.00;    // keeps the end supports off the countersinks

// Side-by-side separation for the combined plate, from the two radio
// envelopes rather than a typed plate width.
combined_gap   = 8.00;

// Gauge.  A throwaway print that answers what the web could not.
gauge_t          = 2.50;
gauge_margin     = 8.00;
gauge_pin_d      = [3.00, 3.50, 4.00, 4.50, 5.00];
gauge_pin_h      = 6.00;
gauge_pin_pitch  = 9.00;

// Diagnostic drivers.  Check wrappers override these after include.
check_pos          = 0.0;
check_lift         = 0.0;
check_extra        = 0.0;
clip_check_w       = thd_clip_w_max;
clip_check_tip_w   = thd_clip_w_tip;
clip_check_gap     = thd_clip_gap;
clip_check_dz      = 0.0;
clip_check_plate_t = 1.6;
screw_check_grow   = 0.0;   // radial inflation of the screw clearance solid
check_rot          = 0.0;   // pedestal rotation about its lug, degrees
amps_keepout_scale = 1.0;   // <1 injects a keep-out that fails to clear
coupon_fit         = "nominal"; // easy | nominal | firm

// =====================================================================
//  5. DERIVED - computed, never edited
// =====================================================================

is_landscape = amps_orientation == "landscape";
amps_x = is_landscape ? amps_long  : amps_short;
amps_z = is_landscape ? amps_short : amps_long;

// A 90 degree countersink is a 45 degree cone, so the depth is just half
// the diameter it has to open out by.
m4_cs_depth = (m4_cs_head_d - m4_clear_d) / (2 * tan(m4_cs_angle / 2));
m4_cs_land  = plate_t - m4_cs_depth;    // solid left under the head

// Two different radii, which were one radius until a render showed why
// they must not be.
//
//   amps_land_r  how much OPEN SPACE a screw needs on the front face, so
//                a driver reaches a flush countersunk head.  Raised
//                features are cut back to this, and every millimetre of
//                it is bitten out of whatever it passes through - in the
//                SDS pad's case, out of the pedestal channel walls.
//   amps_pad_r   how much PLATE has to surround the hole.  This only
//                sizes the outline, so making it generous costs nothing.
//
// Sizing the keep-out with the plate margin scalloped the channel walls
// away over most of the seated pedestal.  They are separate requirements
// and are now separate numbers.
amps_land_r_nom = m4_cs_head_d / 2 + amps_driver_clr;
amps_pad_r      = m4_cs_head_d / 2 + amps_wall;

has_sds  = variant == "sds"  || variant == "combined";
has_clip = variant == "clip" || variant == "combined";

// Side-by-side placement, derived from the radios rather than typed.
// These come first because the land radius below depends on them.
combined_sep = sds_body_w / 2 + thd_body_w / 2 + combined_gap;
sds_cx  = variant == "combined" ? -combined_sep / 2 : 0;
clip_cx = variant == "combined" ?  combined_sep / 2 : 0;

// Width the pedestal needs.  With the channel on this is the channel;
// with it off it is still the width the pad must span so the pedestal
// lands fully rather than overhanging an edge and rocking.
sds_guide_w = boss_w + 2 * sds_guide_clr;

// How far each screw column sits from the pedestal channel's wall plane.
sds_land_gaps = [for (sx = [-1, 1])
    abs(sx * amps_x / 2 - sds_cx) - sds_guide_w / 2];

// A land that stops just short of that wall is the worst possible case:
// it leaves a rib between the channel and its own scallop that is too
// thin to print.  inspect_stl.py measured 0.53 mm of exactly this on the
// first export of the landscape SDS plate.  So a land must either clear
// the wall by a full wall thickness or cut cleanly through it - never
// land in between.  Where it would, open it up until it goes through.
//
// Only the CHANNEL creates that inner boundary.  With the channel off the
// pad has no inside edge for a land to strand material against - the land
// simply bites its outer edge - so the correction is not applied, and the
// lands stay at their nominal radius instead of eating pad for nothing.
sds_land_grazing = [for (g = sds_land_gaps)
    if (g >= amps_land_r_nom && g < amps_land_r_nom + sds_min_wall) g];

amps_land_r = (has_sds && sds_guide && len(sds_land_grazing) > 0)
    ? min(sds_land_grazing) + sds_min_wall
    : amps_land_r_nom;

// SDS150 keyhole, from the shared stud file with this model's fit.
sds_ledge_t    = gravity_ledge_t(standoff_preload, standoff_ledge_scale);
sds_total_depth = gravity_total_depth(standoff_preload, proclip_head_clr_z);
sds_head_ch_h  = sds_total_depth - sds_ledge_t;
sds_stud_depth = sds_total_depth;
sds_entry_d    = gravity_entry_d(standoff_clr_slide, standoff_hole_comp);
sds_neck_w     = gravity_neck_w(standoff_clr_slide);
sds_head_w     = gravity_head_w(standoff_clr_slide);
sds_min_travel = gravity_min_travel(standoff_clr_slide, standoff_hole_comp);

// Centre the keyhole's own extent on the AMPS pattern, so the radio's
// weight acts through the screws rather than off one end of them.
sds_locked_z = -sds_travel / 2;
sds_entry_z  = sds_locked_z + sds_travel;
sds_ped_ctr_z = sds_locked_z - boss_stud_off_l;
sds_ped_z0   = sds_ped_ctr_z - boss_l / 2;
sds_ped_z1   = sds_ped_ctr_z + boss_l / 2;

// Pad height is whatever the keyhole needs and no more.  The channel
// floor - not the pad rim - is the face the pedestal bears on.
sds_guide_d  = sds_guide ? sds_guide_h : 0;
sds_pad_h    = sds_stud_depth + sds_roof_min + sds_guide_d - plate_t;
sds_pad_face_y = plate_t + sds_pad_h;       // the rim
sds_face_y     = sds_pad_face_y - sds_guide_d;  // pedestal bearing face
sds_roof_t     = sds_face_y - sds_stud_depth;

sds_pad_w    = max(sds_entry_d, sds_guide_w) + 2 * sds_pad_wall;

// With the channel on, the pad cannot simply borrow the plate's corner
// radius: the channel is straight and the pad's corner curves in behind
// it, so past the point where the corner crosses the channel wall there
// is no wall left - it feathers to nothing and leaves a knife edge.
// Round only as far as the wall can afford.  With the channel off there
// is no wall to feather, so the pad rounds freely.
sds_pad_corner_r = sds_guide
    ? min(plate_corner_r, sds_pad_w / 2 - sds_guide_w / 2 - sds_min_wall)
    : plate_corner_r;
sds_pad_z0   = sds_locked_z - sds_entry_d / 2 - sds_pad_wall;
sds_pad_z1   = sds_entry_z + sds_entry_d / 2 + sds_pad_wall;
sds_pad_cz   = (sds_pad_z0 + sds_pad_z1) / 2;
sds_pad_zh   = sds_pad_z1 - sds_pad_z0;

// Belt-clip bridge.  Sits above the AMPS pattern so its end supports
// never land on a countersink.
clip_bar_y_in  = plate_t + clip_back_gap;
clip_bar_y_out = clip_bar_y_in + clip_bar_t;
clip_bar_z0    = amps_z / 2 + amps_land_r + clip_amps_gap;
clip_bar_z1    = clip_bar_z0 + clip_bar_h;
clip_bar_cz    = (clip_bar_z0 + clip_bar_z1) / 2;
clip_span_w    = clip_outer_clear + 2 * clip_support_w;
clip_support_x = clip_outer_clear / 2 + clip_support_w / 2;

// Plate outline: the convex hull of one region per thing it must hold.
// Move a feature and the outline follows, which is the whole point.
amps_region = [0, 0,
               amps_x + 2 * amps_pad_r,
               amps_z + 2 * amps_pad_r, plate_corner_r];
sds_region  = [sds_cx, sds_pad_cz,
               sds_pad_w + 2 * plate_edge_wall,
               sds_pad_zh + 2 * plate_edge_wall, plate_corner_r];
clip_region = [clip_cx, clip_bar_cz,
               clip_span_w + 2 * plate_edge_wall,
               clip_bar_h + 2 * plate_edge_wall, plate_corner_r];

plate_regions = concat([amps_region],
                       has_sds  ? [sds_region]  : [],
                       has_clip ? [clip_region] : []);

// Clearance between the AMPS keep-out and the keyhole's entry hole.  The
// most likely place for this design to have quietly collided with
// itself, so it is measured rather than eyeballed.
amps_entry_clr = min([for (sx = [-1, 1], sz = [-1, 1])
    sqrt(pow(sx * amps_x / 2 - sds_cx, 2)
       + pow(sz * amps_z / 2 - sds_entry_z, 2))
    - amps_land_r - sds_entry_d / 2]);

amps_locked_clr = min([for (sx = [-1, 1], sz = [-1, 1])
    sqrt(pow(sx * amps_x / 2 - sds_cx, 2)
       + pow(sz * amps_z / 2 - sds_locked_z, 2))
    - amps_land_r - sds_head_w / 2]);

// How much of the seated pedestal still has channel wall beside it after
// the lands have taken their bite.  All FOUR screws are walked: the first
// version of this only looked at the +X column and reported a clean zero
// for the combined plates, where it is the -X column that does the biting.
amps_wall_bite = max([for (i = [0 : 1], sz = [-1, 1])
    let (dx = sds_land_gaps[i],
         reach = dx < amps_land_r ? sqrt(pow(amps_land_r, 2) - pow(dx, 2))
                                  : 0)
    reach == 0 ? 0
        : max(0, min(sds_ped_z1, sz * amps_z / 2 + reach)
                 - max(sds_ped_z0, sz * amps_z / 2 - reach))]);
sds_wall_engaged = boss_l - amps_wall_bite;

// Load numbers, reported so the plate is never printed on a guess.
sds_arm_y  = sds_face_y + boss_h + sds_body_d / 2;
clip_arm_y = clip_bar_y_out + clip_rail_h + thd_body_d / 2;

// =====================================================================
//  6. ASSERTS - confirmations of 1-5
// =====================================================================

assert(variant == "sds" || variant == "clip" || variant == "combined",
    str("unknown variant: ", variant));
assert(is_landscape || amps_orientation == "portrait",
    str("unknown amps_orientation: ", amps_orientation));

assert(m4_cs_land >= 2.5,
    str("only ", m4_cs_land, "mm of plate under the countersunk head; ",
        "thicken plate_t"));
assert(m4_cs_depth < plate_t,
    "the countersink is deeper than the plate");

assert(sds_travel >= sds_min_travel,
    str("SDS travel ", sds_travel, " is below minimum ", sds_min_travel));
assert(!has_sds || sds_roof_t >= sds_roof_min - 0.001,
    str("only ", sds_roof_t, "mm behind the head channel"));
assert(!has_sds || sds_pad_h > 0,
    "the SDS pad has collapsed; plate_t already exceeds the keyhole depth");
assert(!has_sds || amps_entry_clr > 1.6,
    str("the AMPS land comes within ", amps_entry_clr,
        "mm of the entry hole"));
assert(!has_sds || amps_locked_clr > 1.6,
    str("the AMPS land comes within ", amps_locked_clr,
        "mm of the seated head channel"));

assert(!has_clip || clip_bar_t < thd_clip_gap,
    "clip bridge is thicker than the measured Kenwood gap");
assert(!has_clip || clip_bar_h < clip_clear_below,
    "the bridge leaves no room for the spring clip to close below it");
assert(!has_clip || clip_bar_z0 > amps_z / 2 + amps_land_r,
    "the bridge supports land on the AMPS countersinks");
// The next four exist only to keep the pedestal channel honest.  They are
// gated on sds_guide rather than deleted, because the channel is still a
// supported option and these are the things that went wrong when it was
// the default.
assert(!has_sds || !sds_guide || sds_pad_corner_r >= 1.0,
    str("the pad corner radius has collapsed to ", sds_pad_corner_r,
        "; widen sds_pad_wall"));
assert(!has_sds || !sds_guide
       || sds_pad_w / 2 - sds_pad_corner_r - sds_guide_w / 2
          >= sds_min_wall - 0.001,
    "the pedestal channel feathers out through the pad's rounded corner");
// Either clear of the channel wall by a printable margin, or through it.
// Never resting on the boundary, which is what makes a knife edge.
assert(!has_sds || !sds_guide || len([for (g = sds_land_gaps)
        if (g >= amps_land_r && g < amps_land_r + sds_min_wall) g]) == 0,
    str("an AMPS land stops short of the pedestal channel wall and leaves ",
        "an unprintable rib; gaps ", sds_land_gaps,
        " against land radius ", amps_land_r));
assert(!has_sds || !sds_guide || sds_wall_engaged >= 15.0,
    str("only ", sds_wall_engaged, "mm of pedestal has channel wall ",
        "beside it; the AMPS lands have eaten the anti-rotation"));

// With no channel, the pad IS the bearing face, so it has to be wide
// enough that the pedestal lands fully instead of overhanging an edge.
assert(!has_sds || sds_pad_w >= boss_w + 2 * sds_min_wall,
    str("the pad is only ", sds_pad_w, "mm wide; the ", boss_w,
        "mm pedestal would overhang it"));
assert(!has_clip || clip_back_gap > clip_check_plate_t + 1.5,
    str("only ", clip_back_gap, "mm behind the bridge for the spring plate"));
assert(!has_clip || clip_inner_clear > thd_clip_w_max,
    "inner centring rails pinch the Kenwood clip");
assert(!has_clip || clip_outer_clear > clip_inner_clear,
    "outer end stops must sit beyond the Kenwood centring collars");
assert(!has_clip || clip_bar_t + clip_rail_h < thd_clip_gap,
    "bridge plus centring rail exceeds the measured Kenwood gap");

assert(variant != "combined" || combined_sep > (sds_body_w + thd_body_w) / 2,
    "the two radios overlap on the combined plate");

// =====================================================================
//  7. PRIMITIVES
// =====================================================================

module rounded_rect_2d(w, d, r) {
    offset(r = r)
        square([w - 2 * r, d - 2 * r], center = true);
}

module rounded_box(w, d, h, r) {
    linear_extrude(height = h)
        rounded_rect_2d(w, d, min(r, min(w, d) / 2 - 0.01));
}

// The plate outline lives in XZ and its thickness runs along +Y, so the
// 2D work is done in the natural plane and then stood up.
module extrude_y(t) {
    rotate([90, 0, 0])
        translate([0, 0, -t])
            linear_extrude(height = t)
                children();
}

// A cylinder whose axis is +Y, starting at y0.
module cyl_y(y0, d, h, fn = 48) {
    translate([0, y0, 0])
        rotate([-90, 0, 0])
            cylinder(d = d, h = h, $fn = fn);
}

module plate_outline_2d() {
    hull()
        for (r = plate_regions)
            translate([r[0], r[1]])
                rounded_rect_2d(r[2], r[3], r[4]);
}

// =====================================================================
//  8. INTERFACE GEOMETRY
// =====================================================================

module amps_positions() {
    for (sx = [-1, 1], sz = [-1, 1])
        translate([sx * amps_x / 2, 0, sz * amps_z / 2])
            children();
}

// Flat, full-depth land at every screw.  Subtracted from raised features
// only - never from the plate itself.
module amps_keepout() {
    amps_positions()
        cyl_y(plate_t, 2 * amps_land_r * amps_keepout_scale, 400, 72);
}

module amps_screw_voids() {
    amps_positions() {
        cyl_y(-1.0, m4_clear_d, plate_t + 2.0);

        // 90 degree countersink, opening on the front face.
        translate([0, plate_t - m4_cs_depth, 0])
            rotate([-90, 0, 0])
                cylinder(d1 = m4_clear_d, d2 = m4_cs_head_d,
                         h = m4_cs_depth + 0.01, $fn = 48);

        // A hair of straight bore above the face, so a head that sits a
        // fraction proud of nominal still finishes flush.
        cyl_y(plate_t - 0.01, m4_cs_head_d, 0.4);
    }
}

// Map the shared stud frame onto the +Y face:
//   local X (travel) -> global +Z     local Y -> global +X
//   local Z (outward) -> global +Y
module sds_frame(cx = 0, z0 = 0) {
    multmatrix([
        [0, 1, 0, cx],
        [0, 0, 1, sds_face_y],
        [1, 0, 0, z0],
        [0, 0, 0, 1]
    ]) children();
}

module sds_pad(cx = 0) {
    translate([cx, 0, sds_pad_cz])
        rotate([90, 0, 0])
            translate([0, 0, -sds_pad_face_y])
                linear_extrude(height = sds_pad_face_y)
                    rounded_rect_2d(sds_pad_w, sds_pad_zh,
                                    sds_pad_corner_r);
}

// The pedestal channel: open at the front and open at the top, so the
// 6mm pedestal drops in from above and then cannot rotate.
module sds_guide_void(cx = 0) {
    if (sds_guide)
        translate([cx - sds_guide_w / 2,
                   sds_face_y,
                   sds_pad_z0 - 1.0])
            cube([sds_guide_w,
                  sds_pad_h + 20.0,
                  sds_pad_zh + 40.0]);
}

module sds_voids(cx = 0,
                 fit_preload = standoff_preload,
                 fit_slide = standoff_clr_slide) {
    sds_guide_void(cx);
    sds_frame(cx, sds_locked_z) {
        gravity_keyhole_void(sds_travel, 1.5, fit_preload, fit_slide,
                             standoff_ledge_scale, standoff_hole_comp);
        gravity_head_channel(sds_travel, fit_preload, fit_slide,
                             standoff_ledge_scale, proclip_head_clr_z);
    }
}

module clip_bridge(cx = 0) {
    // 35 x 25 x 3 plate with rounded top and bottom edges, so neither the
    // clip's hinge nor its spring tip catches a printed corner.
    translate([cx - clip_bar_w / 2, clip_bar_y_in,
               clip_bar_z0 + clip_bar_t / 2])
        cube([clip_bar_w, clip_bar_t, clip_bar_h - clip_bar_t]);
    for (z = [clip_bar_z0 + clip_bar_t / 2, clip_bar_z1 - clip_bar_t / 2])
        translate([cx, clip_bar_y_in + clip_bar_t / 2, z])
            rotate([0, 90, 0])
                cylinder(d = clip_bar_t, h = clip_bar_w,
                         center = true, $fn = 64);

    // End supports run from the plate face right through the bar, so the
    // bar is fused to them rather than merely touching.
    for (sx = [-1, 1])
        translate([cx + sx * clip_support_x,
                   plate_t + (clip_back_gap + clip_bar_t) / 2,
                   clip_bar_z0 + clip_bar_t / 2])
            rounded_box(clip_support_w, clip_back_gap + clip_bar_t,
                        clip_bar_h - clip_bar_t, 0.6);
}

module clip_centering_rails(cx = 0) {
    // Shallow rises that centre the measured 21.3mm hinge.  A wider clip
    // rides over them and stops at the end supports instead.
    for (sx = [-1, 1])
        translate([cx + sx * (clip_inner_clear / 2 + clip_collar_w / 2),
                   clip_bar_y_out + clip_rail_h / 2 - 0.05,
                   clip_bar_z0 + clip_bar_t / 2])
            rounded_box(clip_collar_w, clip_rail_h + 0.1,
                        clip_bar_h - clip_bar_t, 0.3);
}

// =====================================================================
//  9. BODY
// =====================================================================

module plate_slab() {
    // Only the front edge rolls in.  Chamfering the bearing face would
    // throw away contact area against the ProClip for nothing.
    hull() {
        extrude_y(plate_t - plate_edge_ch) plate_outline_2d();
        translate([0, plate_t - plate_edge_ch, 0])
            extrude_y(plate_edge_ch)
                offset(r = -plate_edge_ch) plate_outline_2d();
    }
}

module raised_features() {
    if (has_sds)  sds_pad(sds_cx);
    if (has_clip) {
        clip_bridge(clip_cx);
        clip_centering_rails(clip_cx);
    }
}

module plate_body(fit_preload = standoff_preload,
                  fit_slide = standoff_clr_slide) {
    difference() {
        union() {
            plate_slab();
            difference() {
                raised_features();
                amps_keepout();
            }
        }
        amps_screw_voids();
        if (has_sds)
            sds_voids(sds_cx, fit_preload, fit_slide);
    }
}

// =====================================================================
//  10. COUPONS
// =====================================================================

// The real keyhole, its real pad and channel, cropped out of the real
// plate.  Print these before committing to a full plate.
module sds_coupon(fit_preload = standoff_preload,
                  fit_slide = standoff_clr_slide) {
    w = sds_pad_w + 2 * plate_edge_wall;
    translate([-sds_cx, 0, -sds_pad_z0 + plate_edge_wall])
        intersection() {
            plate_body(fit_preload, fit_slide);
            translate([sds_cx - w / 2, -1, sds_pad_z0 - plate_edge_wall])
                cube([w, sds_pad_face_y + 2,
                      sds_pad_zh + 2 * plate_edge_wall]);
        }
}

module clip_coupon() {
    w = clip_span_w + 2 * plate_edge_wall;
    translate([-clip_cx, 0, -clip_bar_z0 + plate_edge_wall])
        intersection() {
            plate_body();
            translate([clip_cx - w / 2, -1,
                       clip_bar_z0 - plate_edge_wall])
                cube([w, clip_bar_y_out + 4,
                      clip_bar_h + 2 * plate_edge_wall]);
        }
}

// The AMPS pattern on its own.  This is the part that answers what no
// amount of searching would: whether the pattern really is AMPS, which
// way round it sits, and what diameter the ProClip's own holes are.
// Print one per orientation and offer them up before printing a plate.
module amps_gauge() {
    pin_row_w = len(gauge_pin_d) * gauge_pin_pitch;
    w = max(amps_x + 2 * amps_pad_r + 2 * gauge_margin, pin_row_w + 10);
    h = amps_z + 2 * amps_pad_r + 2 * gauge_margin + gauge_pin_pitch;
    // Centre the AMPS holes in the upper part; the pin row takes the strip
    // below, so a pin can never foul a hole being tested.
    amps_dz = gauge_pin_pitch / 2;
    win_w = amps_x - 2 * amps_pad_r;
    win_h = amps_z - 2 * amps_pad_r;

    difference() {
        union() {
            extrude_y(gauge_t) rounded_rect_2d(w, h, 4.0);

            // Graded pins.  The largest that enters a ProClip hole without
            // force is that hole's diameter.
            for (i = [0 : len(gauge_pin_d) - 1])
                translate([-pin_row_w / 2 + gauge_pin_pitch * (i + 0.5),
                           0,
                           -h / 2 + gauge_pin_pitch / 2])
                    cyl_y(gauge_t - 0.01, gauge_pin_d[i],
                          gauge_pin_h + 0.01, 48);
        }

        translate([0, 0, amps_dz])
            amps_positions()
                cyl_y(-1, m4_clear_d, gauge_t + 2);

        // Window onto the middle of the ProClip plate, so Brodit's two
        // undocumented double-hole pairs can be seen and measured while
        // the AMPS holes are held registered.
        if (win_w > 6 && win_h > 6)
            translate([0, -1, amps_dz])
                extrude_y(gauge_t + 2)
                    rounded_rect_2d(win_w, win_h, 2.0);
    }
}

// =====================================================================
//  11. DIAGNOSTIC SOLIDS
// =====================================================================

module sds_check_solid() {
    sds_frame(sds_cx, sds_locked_z)
        stud_solid(pos = check_pos, extra = check_extra, lift = check_lift);
}

// The keyhole and channel as a solid, so a check can ask whether the
// screws come near them without relying on a boolean that has already
// removed both.
module sds_void_solid() {
    sds_frame(sds_cx, sds_locked_z) {
        gravity_keyhole_void(sds_travel, 1.5, standoff_preload,
                             standoff_clr_slide, standoff_ledge_scale,
                             standoff_hole_comp);
        gravity_head_channel(sds_travel, standoff_preload,
                             standoff_clr_slide, standoff_ledge_scale,
                             proclip_head_clr_z);
    }
}

module screw_clearance_solid() {
    amps_positions()
        cyl_y(-2, m4_cs_head_d + 2 * screw_check_grow, plate_t + 4, 48);
}

// A thin disc on the front face at each screw.  If it meets material,
// something raised is sitting on a countersink.
module amps_land_probe() {
    amps_positions()
        cyl_y(plate_t + 0.05, 2 * amps_land_r, 0.60, 72);
}

// The pedestal at its seated position, for checking the channel actually
// straddles it after the AMPS keep-out has taken its bite.  Rotating it
// about its own lug is how anti-rotation gets PROVEN rather than assumed:
// square it should be free, twisted it must hit the channel walls.
module sds_pedestal_solid(dz = 0, rot = 0) {
    translate([sds_cx, 0, sds_locked_z])
        rotate([0, rot, 0])
            translate([-boss_w / 2,
                       sds_face_y + 0.02,
                       sds_ped_z0 - sds_locked_z + dz])
                cube([boss_w, boss_h, boss_l]);
}

module clip_check_solid(width = clip_check_w,
                        tip_width = clip_check_tip_w,
                        gap = clip_check_gap,
                        top_z = clip_bar_z1 + 1.8) {
    // A rigid U that stands in for the working part of a belt clip: the
    // radio-side plate outside the bridge, the spring plate in the slot
    // behind it.  It stops above the real clip's flush tip so a straight
    // article does not invent a collision the bent one would not have.
    pt = clip_check_plate_t;
    rides = width > clip_inner_clear;
    radio_y = clip_bar_y_out + (rides ? clip_rail_h : 0) + 0.20;
    spring_y = radio_y - gap - pt;

    color([0.75, 0.35, 0.1, 0.65]) union() {
        hull() {
            translate([clip_cx - width / 2, radio_y, top_z - pt])
                cube([width, pt, pt]);
            translate([clip_cx - tip_width / 2, radio_y,
                       top_z - clip_clear_below])
                cube([tip_width, pt, pt]);
        }
        hull() {
            translate([clip_cx - width / 2, spring_y, top_z - pt])
                cube([width, pt, pt]);
            translate([clip_cx - tip_width / 2, spring_y,
                       top_z - clip_clear_below])
                cube([tip_width, pt, pt]);
        }
        translate([clip_cx - width / 2, spring_y, top_z - pt])
            cube([width, gap + 2 * pt, pt]);
    }
}

// Bare radio envelopes.  Kept separate from the coloured references so a
// check can intersect them; a coloured, unioned assembly cannot answer
// whether two radios foul each other.
module sds_envelope() {
    translate([sds_cx - sds_body_w / 2,
               sds_face_y + boss_h,
               sds_locked_z - sds_lug_from_bottom])
        cube([sds_body_w, sds_body_d, sds_body_h]);
    sds_pedestal_solid();
}

module thd_envelope() {
    translate([clip_cx - thd_body_w / 2,
               clip_bar_y_out + clip_rail_h + 0.2,
               clip_bar_z1 + thd_clip_clear_h - thd_body_h + clip_check_dz])
        cube([thd_body_w, thd_body_d, thd_body_h]);
}

module sds_reference() {
    color([0.15, 0.35, 0.65, 0.30]) sds_envelope();
}

module thd_reference() {
    color([0.25, 0.25, 0.28, 0.30]) thd_envelope();
}

// =====================================================================
//  12. REPORT
// =====================================================================

plate_w = amps_x + 2 * amps_pad_r;

echo(str("PROCLIP MOUNT variant=", variant,
         " orientation=", amps_orientation,
         " amps_x=", amps_x, " amps_z=", amps_z,
         " plate_t=", plate_t));
echo(str("  SCREW clear_d=", m4_clear_d,
         " cs_head_d=", m4_cs_head_d,
         " cs_depth=", m4_cs_depth,
         " cs_land=", m4_cs_land,
         " land_r=", amps_land_r,
         " pad_r=", amps_pad_r,
         " nyloc_t=", m4_nyloc_t,
         " plate_est=", proclip_plate_t_est,
         " min_screw_len=", plate_t + proclip_plate_t_est + m4_nyloc_t));
echo(str("  SDS locked_z=", sds_locked_z,
         " entry_z=", sds_entry_z,
         " travel=", sds_travel,
         " min=", sds_min_travel,
         " ledge_t=", sds_ledge_t,
         " entry_d=", sds_entry_d,
         " neck_w=", sds_neck_w,
         " head_w=", sds_head_w,
         " stud_depth=", sds_stud_depth,
         " head_clr_z=", proclip_head_clr_z));
echo(str("  SDSPAD pad_h=", sds_pad_h,
         " face_y=", sds_face_y,
         " rim_y=", sds_pad_face_y,
         " roof_t=", sds_roof_t,
         " guide_w=", sds_guide_w,
         " guide_h=", sds_guide_d,
         " pad_w=", sds_pad_w,
         " pad_z0=", sds_pad_z0,
         " pad_z1=", sds_pad_z1));
echo(str("  CLEAR amps_entry_clr=", amps_entry_clr,
         " amps_locked_clr=", amps_locked_clr,
         " guide=", sds_guide ? "on" : "off",
         // Only meaningful with the channel on; -1 rather than a
         // plausible-looking figure for something that does not exist.
         " wall_bite=", sds_guide ? max(0, amps_wall_bite) : -1,
         " wall_engaged=", sds_guide ? sds_wall_engaged : -1));
echo(str("  CLIP bar_w=", clip_bar_w,
         " bar_h=", clip_bar_h,
         " bar_t=", clip_bar_t,
         " bar_z0=", clip_bar_z0,
         " bar_top=", clip_bar_z1,
         " y_in=", clip_bar_y_in,
         " y_out=", clip_bar_y_out,
         " back_gap=", clip_back_gap,
         " plate_t_c=", clip_check_plate_t,
         " test_h=", clip_clear_below,
         " kenwood_w=", thd_clip_w_max,
         " kenwood_tip=", thd_clip_w_tip,
         " kenwood_gap=", thd_clip_gap,
         " generic_w=", uv5r_clip_env_w,
         " inner=", clip_inner_clear,
         " outer=", clip_outer_clear));
echo(str("  LAYOUT sds_cx=", sds_cx,
         " clip_cx=", clip_cx,
         " sep=", combined_sep,
         " sds_arm_y=", sds_arm_y,
         " clip_arm_y=", clip_arm_y,
         " sds_mass_g=", sds_mass_g,
         " thd_mass_g=", thd_mass_g));

// =====================================================================
//  13. ENTRY POINT
// =====================================================================

variant_render_mode = "plate";

if (variant_render_mode == "plate") {
    plate_body();
} else if (variant_render_mode == "gauge") {
    amps_gauge();
} else if (variant_render_mode == "coupon") {
    if (coupon_fit == "easy")         sds_coupon(0.00, 0.40);
    else if (coupon_fit == "nominal") sds_coupon(0.05, 0.35);
    else if (coupon_fit == "firm")    sds_coupon(0.10, 0.30);
    else assert(false, str("unknown coupon_fit: ", coupon_fit));
} else if (variant_render_mode == "clip_coupon") {
    clip_coupon();
} else if (variant_render_mode == "sds_check") {
    sds_check_solid();
} else if (variant_render_mode == "sds_void") {
    sds_void_solid();
} else if (variant_render_mode == "screw_clearance") {
    screw_clearance_solid();
} else if (variant_render_mode == "amps_land_probe") {
    amps_land_probe();
} else if (variant_render_mode == "pedestal") {
    sds_pedestal_solid(check_pos, check_rot);
} else if (variant_render_mode == "clip_check") {
    clip_check_solid();
} else if (variant_render_mode == "sds_envelope") {
    sds_envelope();
} else if (variant_render_mode == "thd_envelope") {
    thd_envelope();
} else if (variant_render_mode == "assembly") {
    color([0.16, 0.16, 0.19]) plate_body();
    if (has_sds)  sds_reference();
    if (has_clip) thd_reference();
} else if (variant_render_mode == "none") {
    // Included as a library by the verification wrappers.
} else {
    assert(false, str("unknown variant_render_mode: ", variant_render_mode));
}
