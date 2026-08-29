// =====================================================================
//  Peak Design opposed-face radio standoff
// =====================================================================
//
//  One upright, support-free body:
//    +Y face  Uniden SDS150, gravity keyhole
//    -Y face  Kenwood TH-D75A / generic belt-clip bridge
//
//  The Peak Design Standard Plate bears on z=0.  Both radios are upright,
//  displays outward, antennas up.  The SDS150 entry is above its seated
//  position so gravity retains it without a latch.
//
//  Print as modelled, base on the build plate.  Units are millimetres.
//

include <../sds150_stud.scad>

// =====================================================================
//  1. FIT - standoff-specific, do not change the shared visor mount
// =====================================================================

// Gravity does useful work here, so this can release more easily than the
// visor mount.  These drivers belong to THIS model.  The shared include
// owns the physical lug dimensions, but its modules close over their own
// fit variables; trying to override those produced three identical
// coupons.  Local fit geometry keeps the source measurements shared while
// making every coupon setting real and measurable.
standoff_preload    = 0.05;
standoff_clr_slide  = 0.35;
standoff_hole_comp  = 0.25;
standoff_head_clr_z = 0.40; // upright channel; no wide horizontal roof

sds_travel        = 19.0;
sds_boss_clr      = 0.50;
sds_guide_depth   = 3.0;
sds_guide_w       = 2.2;

// =====================================================================
//  2. MEASURED / CONFIRMED INTERFACES
// =====================================================================

pd_plate_size     = 39.0;
thread_major      = 6.35;   // 1/4 inch
thread_pitch      = 1.27;   // 20 TPI
thread_style      = "self_tap"; // self_tap | insert | nut

self_tap_d        = 5.40;
self_tap_depth    = 8.25;
insert_d          = 7.60;
insert_depth      = 6.00;
nut_af            = 11.15;
nut_t             = 5.60;
socket_mouth_d    = 8.0;

sds_body_h        = 153.0;
sds_body_w        = 69.9;   // conservative repo envelope; sketch says 57
sds_body_d        = 40.0;   // conservative diagnostic envelope
sds_lug_from_bottom = 108.0; // derived from the annotated physical sketch
sds_bottom_clear  = 20.0;
sds_mass_g        = 400.0;

thd_body_h        = 121.9;
thd_body_w        = 56.0;
thd_body_d        = 35.0;   // conservative diagnostic envelope
thd_clip_w_max    = 21.3;
thd_clip_w_tip    = 17.6;
thd_clip_gap      = 4.5;
thd_clip_clear_h  = 30.0;
thd_clip_tip_h    = 6.5;
thd_mass_g        = 400.0;  // conservative until weighed

uv5r_clip_env_w   = 32.0;   // published overall clip envelope, not jaw width

// =====================================================================
//  3. STRUCTURE AND VISUAL LANGUAGE
// =====================================================================

base_t            = 10.0;
base_corner_r     = 4.0;
base_edge_ch      = 0.8;

// The spine is a sequence of rounded sections.  Width and depth move in
// opposite directions through a narrow waist, then grow smoothly into the
// two radio interfaces.  Material is kept at the edges where it buys
// bending stiffness rather than filling the neutral axis.
spine_sections = [
    // z,    width X, depth Y, corner radius
    [  8.5,  37.0,    29.0,    5.0],
    [ 20.0,  33.0,    21.0,    5.0],
    [ 50.0,  25.0,    14.0,    4.0],
    [ 90.0,  23.0,    13.0,    4.0],
    [112.0,  29.0,    14.0,    4.0],
    [132.0,  38.0,    18.0,    4.0],
    [159.0,  40.0,    18.0,    4.0]
];
section_h         = 1.0;

// A shallow waist cut removes neutral-axis material without opening the
// outside ribs.  It is an organic lens, not a rectangular window.
waist_cut          = true;
waist_cut_w        = 12.0;
waist_cut_y        = 20.0;
waist_cut_z0       = 34.0;
waist_cut_z1       = 105.0;

// Belt-clip bridge.  The bar substitutes for a belt: the radio lies on its
// outside face while the clip descends in the gap between bar and spine.
clip_bar_z0        = 119.0;
clip_bar_h         = 29.0;
clip_bar_w         = 35.0;
clip_bar_t         = 3.0;
clip_back_gap      = 3.6;
clip_rail_h        = 0.65;
clip_inner_clear   = thd_clip_w_max + 1.0;
clip_outer_clear   = uv5r_clip_env_w + 1.0;
clip_lead_r        = 1.5;

// Diagnostic drivers.  Verification wrappers override these after include.
check_pos          = 0.0;
check_lift         = 0.0;
check_extra        = 0.0;
clip_check_w       = thd_clip_w_max;
clip_check_tip_w   = thd_clip_w_tip;
clip_check_gap     = thd_clip_gap;
clip_check_top_z   = clip_bar_z1 + clip_lead_r + 1.8;
clip_check_dz      = 0.0;
clip_check_plate_t = 1.6;
coupon_fit         = "nominal"; // easy | nominal | firm

// =====================================================================
//  4. DERIVED - computed, never edited
// =====================================================================

nut_across_corners = nut_af / cos(30);
socket_depth = thread_style == "self_tap" ? self_tap_depth
             : thread_style == "insert"   ? insert_depth
             :                              nut_t;
socket_floor = base_t - socket_depth;

sds_ledge_t   = (stud_neck_h - standoff_preload) * shrink_comp;
sds_head_ch_h = (stud_head_t + standoff_head_clr_z) * shrink_comp;
sds_entry_d   = (stud_head_d + 2 * standoff_clr_slide
                 + standoff_hole_comp) * shrink_comp;
sds_head_ch_w = (stud_head_d + 2 * standoff_clr_slide) * shrink_comp;
sds_neck_w    = (stud_neck_d + 2 * standoff_clr_slide) * shrink_comp;
sds_stud_depth = sds_ledge_t + sds_head_ch_h;
sds_min_travel = (sds_entry_d + stud_head_d) / 2;

sds_locked_z = sds_bottom_clear + sds_lug_from_bottom;
sds_entry_z  = sds_locked_z + sds_travel;
sds_bottom_z = sds_locked_z - sds_lug_from_bottom;
sds_ped_ctr_z = sds_locked_z - boss_stud_off_l;
sds_ped_z0   = sds_ped_ctr_z - boss_l / 2;
sds_ped_z1   = sds_ped_ctr_z + boss_l / 2;

spine_top_z  = spine_sections[len(spine_sections) - 1][0] + section_h;
front_face_y = spine_sections[len(spine_sections) - 1][2] / 2;
rear_face_y  = -front_face_y;

clip_bar_y1  = rear_face_y - clip_back_gap;     // face nearest spine
clip_bar_y0  = clip_bar_y1 - clip_bar_t;        // face nearest radio
clip_bar_z1  = clip_bar_z0 + clip_bar_h;
thd_body_z0  = clip_bar_z1 + 30.0 - thd_body_h;

// =====================================================================
//  5. ASSERTS - confirmations, not the primary design method
// =====================================================================

assert(pd_plate_size == 39.0, "base assumptions require Standard Plate");
assert(base_corner_r < pd_plate_size / 2, "base radius consumes the plate");
assert(sds_travel >= sds_min_travel,
    str("SDS travel ", sds_travel, " is below minimum ", sds_min_travel));
assert(sds_bottom_z >= 20.0,
       str("SDS bottom only clears by ", sds_bottom_z, "mm"));
assert(sds_entry_z + sds_entry_d / 2 < spine_top_z,
       "SDS entry hole breaks through the top of the standoff");
assert(front_face_y > sds_stud_depth,
       str("top section is only ", front_face_y,
           "mm deep but SDS channel needs ", sds_stud_depth));
assert(clip_bar_t < thd_clip_gap,
       "clip bridge is thicker than the measured Kenwood gap");
assert(clip_inner_clear > thd_clip_w_max,
       "inner centering rails pinch the Kenwood clip");
assert(clip_outer_clear > uv5r_clip_env_w,
       "outer rail envelope is narrower than the UV-5R published clip");
assert(socket_floor >= 1.5,
       str("only ", socket_floor, "mm above the tripod socket"));
assert(thread_style == "self_tap" || thread_style == "insert"
       || thread_style == "nut", str("unknown thread_style: ", thread_style));

// =====================================================================
//  6. PRIMITIVES
// =====================================================================

module rounded_rect_2d(w, d, r) {
    offset(r = r)
        square([w - 2 * r, d - 2 * r], center = true);
}

module rounded_box(w, d, h, r) {
    linear_extrude(height = h)
        rounded_rect_2d(w, d, min(r, min(w, d) / 2 - 0.01));
}

module section_node(s) {
    translate([0, 0, s[0]])
        rounded_box(s[1], s[2], section_h, s[3]);
}

module organic_spine() {
    union() {
        for (i = [0 : len(spine_sections) - 2])
            hull() {
                section_node(spine_sections[i]);
                section_node(spine_sections[i + 1]);
            }
    }
}

module base_outer() {
    // The complete 39mm lower face bears on Peak Design's rubber pad.
    // Only the TOP edge rolls inward; chamfering the bottom would throw
    // away the anti-rotation area this base exists to provide.
    hull() {
        translate([0, 0, 0])
            rounded_box(pd_plate_size, pd_plate_size,
                        0.8, base_corner_r);
        translate([0, 0, base_edge_ch])
            rounded_box(pd_plate_size, pd_plate_size,
                        base_t - 2 * base_edge_ch,
                        base_corner_r);
        translate([0, 0, base_t - base_edge_ch])
            rounded_box(pd_plate_size - 2 * base_edge_ch,
                        pd_plate_size - 2 * base_edge_ch,
                        base_edge_ch, base_corner_r - base_edge_ch);
    }
}

module waist_void() {
    // Lens in the XZ plane, extruded through Y.  It leaves edge ribs and
    // follows the spine's load path instead of punching a square window.
    translate([0, waist_cut_y / 2, 0])
        rotate([90, 0, 0])
            linear_extrude(height = waist_cut_y)
                hull() {
                    translate([0, waist_cut_z0]) circle(d = waist_cut_w);
                    translate([0, waist_cut_z1]) circle(d = waist_cut_w);
                }
}

// Map the shared stud frame to the +Y radio face:
//   local X (travel) -> global +Z
//   local Y          -> global +X
//   local Z (outward)-> global +Y
module sds_frame(z0 = sds_locked_z) {
    multmatrix([
        [0, 1, 0, 0],
        [0, 0, 1, front_face_y],
        [1, 0, 0, z0],
        [0, 0, 0, 1]
    ]) children();
}

module standoff_keyhole_void(travel, above = 1.0,
                             fit_preload = standoff_preload,
                             fit_slide = standoff_clr_slide) {
    ledge_v = (stud_neck_h - fit_preload) * shrink_comp;
    neck_v = (stud_neck_d + 2 * fit_slide) * shrink_comp;
    entry_v = (stud_head_d + 2 * fit_slide
               + standoff_hole_comp) * shrink_comp;

    translate([0, 0, -ledge_v - 0.01])
        capsule(travel, neck_v, ledge_v + above + 0.02);
    translate([travel, 0, -ledge_v - 0.01])
        cylinder(d = entry_v, h = ledge_v + above + 0.02);
}

module standoff_head_channel(travel,
                             fit_preload = standoff_preload,
                             fit_slide = standoff_clr_slide) {
    ledge_v = (stud_neck_h - fit_preload) * shrink_comp;
    channel_h_v = (stud_head_t + standoff_head_clr_z) * shrink_comp;
    channel_w_v = (stud_head_d + 2 * fit_slide) * shrink_comp;

    translate([0, 0, -ledge_v - channel_h_v])
        capsule(travel, channel_w_v, channel_h_v);
}

module sds_voids(fit_preload = standoff_preload,
                 fit_slide = standoff_clr_slide) {
    sds_frame() {
        standoff_keyhole_void(sds_travel, above = 1.5,
                              fit_preload = fit_preload,
                              fit_slide = fit_slide);
        standoff_head_channel(sds_travel,
                              fit_preload = fit_preload,
                              fit_slide = fit_slide);
    }
}

module sds_guides() {
    guide_x = boss_w / 2 + sds_boss_clr + sds_guide_w / 2;
    guide_z0 = sds_ped_z0 - 1.0;
    guide_z1 = spine_top_z - 1.0;

    for (sx = [-1, 1])
        translate([sx * guide_x,
                   front_face_y + sds_guide_depth / 2 - 0.2,
                   guide_z0])
            rounded_box(sds_guide_w, sds_guide_depth + 0.4,
                        guide_z1 - guide_z0, 0.8);
}

module clip_bar() {
    // Broad bar, offset from the rear face.  Short side bridges are only
    // 3.2mm and print as routine horizontal bridges; lower haunches make
    // the loaded direction self-supporting.
    translate([-clip_bar_w / 2, clip_bar_y0, clip_bar_z0])
        cube([clip_bar_w, clip_bar_t, clip_bar_h]);

    // End bridges and 45-degree lower haunches.
    for (sx = [-1, 1]) {
        x0 = sx < 0 ? -clip_bar_w / 2 : clip_bar_w / 2 - 2.4;
        translate([x0, clip_bar_y1 - 0.3, clip_bar_z0 + 3.0])
            cube([2.4, clip_back_gap + 0.6, clip_bar_h - 3.0]);

        hull() {
            translate([x0, rear_face_y - 0.2, clip_bar_z0 - 4.0])
                cube([2.4, 0.8, 4.0]);
            translate([x0, clip_bar_y1, clip_bar_z0])
                cube([2.4, 0.8, 4.0]);
        }
    }

    // Rounded top lead-in on the radio-facing edge.
    translate([0, (clip_bar_y0 + clip_bar_y1) / 2, clip_bar_z1])
        rotate([0, 90, 0])
            cylinder(r = clip_lead_r, h = clip_bar_w,
                     center = true, $fn = 64);
}

module clip_centering_rails() {
    // Gravity-centering funnel.  The clear width narrows from the generic
    // 33mm envelope to the measured Kenwood width.  A wider clip seats
    // higher; a Kenwood descends farther.  The rails are shallow enough
    // to remain inside the measured 4.5mm clip gap.
    for (sx = [-1, 1])
        hull() {
            translate([sx * clip_outer_clear / 2,
                      clip_bar_y0 - clip_rail_h / 2 + 0.1,
                       clip_bar_z1 - 2.0])
                rounded_box(1.2, clip_rail_h, 2.0, 0.3);
            translate([sx * clip_inner_clear / 2,
                      clip_bar_y0 - clip_rail_h / 2 + 0.1,
                       clip_bar_z0 + 2.0])
                rounded_box(1.2, clip_rail_h, 2.0, 0.3);
        }
}

module tripod_socket_void() {
    if (thread_style == "self_tap") {
        translate([0, 0, -0.01])
            cylinder(d = self_tap_d, h = self_tap_depth + 0.02);

    } else if (thread_style == "insert") {
        translate([0, 0, -0.01])
            cylinder(d = insert_d, h = insert_depth + 0.02);
        translate([0, 0, insert_depth - 0.01])
            cylinder(d = self_tap_d,
                     h = base_t - insert_depth - 1.0 + 0.02);

    } else {
        translate([0, 0, -0.01])
            cylinder(d = nut_across_corners, h = nut_t + 0.02, $fn = 6);
        translate([0, 0, nut_t - 0.01])
            cylinder(d = thread_major + 0.6,
                     h = base_t - nut_t - 1.0 + 0.02);
    }

    // Mouth chamfer prevents a raised first layer and lets the PD plate
    // sit flat against the full bearing face.
    translate([0, 0, -0.01])
        cylinder(d1 = socket_mouth_d, d2 = thread_major,
                 h = 0.81, $fn = 64);
}

// =====================================================================
//  7. BODY AND DIAGNOSTIC SOLIDS
// =====================================================================

module standoff_body(fit_preload = standoff_preload,
                     fit_slide = standoff_clr_slide) {
    difference() {
        union() {
            base_outer();
            organic_spine();
            sds_guides();
            clip_bar();
            clip_centering_rails();
        }

        tripod_socket_void();
        sds_voids(fit_preload = fit_preload, fit_slide = fit_slide);

        if (waist_cut)
            waist_void();
    }
}

module sds_reference(pos = check_pos) {
    // Back panel is 6mm outward from the bearing face because the measured
    // pedestal stands 6mm proud.  Transparent in assembly render only.
    color([0.15, 0.35, 0.65, 0.35]) {
        translate([-sds_body_w / 2,
                   front_face_y + boss_h,
                 sds_bottom_z + pos])
            cube([sds_body_w, sds_body_d, sds_body_h]);

        // Pedestal and exact lug at the seated datum.
        translate([-boss_w / 2, front_face_y,
                   sds_ped_ctr_z - boss_l / 2 + pos])
            cube([boss_w, boss_h, boss_l]);

        sds_frame() stud_solid(pos = pos);
    }
}

module thd_reference(dz = clip_check_dz) {
    // The body's rear plane rests on the outer face of the clip bar.
    color([0.25, 0.25, 0.28, 0.35])
        translate([-thd_body_w / 2,
                   clip_bar_y0 - clip_rail_h - 0.2 - thd_body_d,
                 thd_body_z0 + dz])
            cube([thd_body_w, thd_body_d, thd_body_h]);

    // Simplified tapered clip plate in the gap behind the bridge.
    color([0.1, 0.1, 0.1, 0.5])
        hull() {
            translate([-thd_clip_w_max / 2,
                       clip_bar_y1 + 0.4,
                      clip_bar_z1 - 2.0 + dz])
                cube([thd_clip_w_max, 1.8, 2.0]);
            translate([-thd_clip_w_tip / 2,
                       clip_bar_y1 + 0.4,
                      clip_bar_z1 - 2.0 - 66.5 + dz])
                cube([thd_clip_w_tip, 1.8, 2.0]);
        }
}

module sds_check_solid() {
    sds_frame()
        stud_solid(pos = check_pos, extra = check_extra, lift = check_lift);
}

module clip_check_solid(width = clip_check_w,
                        tip_width = clip_check_tip_w,
                        gap = clip_check_gap,
                        top_z = clip_check_top_z) {
    // A short, rigid U-section that represents the working part of a belt
    // clip.  The radio-side plate is outside the bar; the spring plate is
    // in the open slot behind it.  It deliberately stops above the real
    // clip's flush tip so the straight diagnostic solid does not invent a
    // collision where the physical clip bends back toward the radio.
    plate_t = clip_check_plate_t;
    test_h = 22.0;
    radio_y = clip_bar_y0 - 0.20;
    clip_inner_y = radio_y + gap;

    color([0.75, 0.35, 0.1, 0.65]) union() {
        hull() {
            translate([-width / 2, radio_y - plate_t, top_z - plate_t])
                cube([width, plate_t, plate_t]);
            translate([-tip_width / 2, radio_y - plate_t, top_z - test_h])
                cube([tip_width, plate_t, plate_t]);
        }
        hull() {
            translate([-width / 2, clip_inner_y, top_z - plate_t])
                cube([width, plate_t, plate_t]);
            translate([-tip_width / 2, clip_inner_y, top_z - test_h])
                cube([tip_width, plate_t, plate_t]);
        }
        translate([-width / 2, radio_y - plate_t, top_z - plate_t])
            cube([width, gap + 2 * plate_t, plate_t]);
    }
}

// Fit coupon: three SDS settings are generated by the exporter as separate
// wrappers.  This mode supplies the real keyhole and one clip bridge slice.
module fit_coupon(fit_preload = standoff_preload,
                  fit_slide = standoff_clr_slide) {
    coupon_w = 58;
    coupon_h = 42;
    coupon_entry_d = (stud_head_d + 2 * fit_slide
             + standoff_hole_comp) * shrink_comp;
    coupon_depth = (stud_neck_h - fit_preload
              + stud_head_t + standoff_head_clr_z) * shrink_comp;

    assert(sds_travel >= (coupon_entry_d + stud_head_d) / 2,
        str("coupon travel is too short for fit ", coupon_fit));
    assert(8 > coupon_depth,
        str("coupon body is too shallow for fit ", coupon_fit));

    difference() {
        rounded_box(coupon_w, 16, coupon_h, 4);

        // Local frame with locked lug at z=8 and entry above it.
        multmatrix([
            [0, 1, 0, 0],
            [0, 0, 1, 8],
            [1, 0, 0, 8],
            [0, 0, 0, 1]
        ]) {
            standoff_keyhole_void(sds_travel, above = 1.5,
                                  fit_preload = fit_preload,
                                  fit_slide = fit_slide);
            standoff_head_channel(sds_travel,
                                  fit_preload = fit_preload,
                                  fit_slide = fit_slide);
        }
    }
}

module clip_coupon() {
    // Crop the real rear interface, preserving its bar, rail taper, gap,
    // end bridges and lower haunches.  The crop plane is below every load
    // path and therefore leaves one printable body with a flat bottom.
    translate([0, 0, -(clip_bar_z0 - 5.0)])
        intersection() {
            standoff_body();
            translate([-23, -18, clip_bar_z0 - 5.0])
                cube([46, 21, clip_bar_h + 10.0]);
        }
}

// =====================================================================
//  8. REPORT AND ENTRY POINT
// =====================================================================

echo(str("RADIO STANDOFF  style=", thread_style,
         " base=", pd_plate_size, "x", pd_plate_size,
         " height=", spine_top_z));
echo(str("  SDS locked_z=", sds_locked_z,
         " entry_z=", sds_entry_z,
         " bottom_z=", sds_bottom_z,
         " travel=", sds_travel,
         " min=", sds_min_travel));
echo(str("  FIT preload=", standoff_preload,
         " slide=", standoff_clr_slide,
         " entry_d=", sds_entry_d,
         " neck_w=", sds_neck_w,
         " stud_depth=", sds_stud_depth));
echo(str("  CLIP bar=", clip_bar_w, "x", clip_bar_h,
         "x", clip_bar_t, " gap=", clip_back_gap,
         " clear=", clip_inner_clear, "..", clip_outer_clear));
echo(str("  CLIPCHECK bar_t=", clip_bar_t,
         " bar_top=", clip_bar_z1,
         " lead_r=", clip_lead_r,
         " plate_t=", clip_check_plate_t,
         " kenwood_w=", thd_clip_w_max,
         " kenwood_tip=", thd_clip_w_tip,
         " kenwood_gap=", thd_clip_gap,
         " generic_w=", uv5r_clip_env_w));
echo(str("  SOCKET depth=", socket_depth,
         " floor=", socket_floor,
         " nut_ac=", nut_across_corners));
echo(str("  LOAD sds_mass_g=", sds_mass_g,
         " thd_mass_g=", thd_mass_g,
         " sds_com_z=", sds_bottom_z + sds_body_h / 2,
         " thd_com_z=", thd_body_z0 + thd_body_h / 2,
         " front_y=", front_face_y + boss_h + sds_body_d / 2,
         " rear_y=", clip_bar_y0 - clip_rail_h - 0.2 - thd_body_d / 2,
         " cut_w=", waist_cut_w,
         " cut_z0=", waist_cut_z0,
         " cut_z1=", waist_cut_z1));
for (s = spine_sections)
    echo(str("  SECTION z=", s[0], " w=", s[1], " d=", s[2]));

variant_render_mode = "body";

if (variant_render_mode == "body") {
    standoff_body(standoff_preload, standoff_clr_slide);
} else if (variant_render_mode == "assembly") {
    color([0.12, 0.12, 0.14])
        standoff_body(standoff_preload, standoff_clr_slide);
    sds_reference();
    thd_reference();
} else if (variant_render_mode == "sds_reference") {
    sds_reference();
} else if (variant_render_mode == "thd_reference") {
    thd_reference();
} else if (variant_render_mode == "coupon") {
    if (coupon_fit == "easy")
        fit_coupon(0.00, 0.40);
    else if (coupon_fit == "nominal")
        fit_coupon(0.05, 0.35);
    else if (coupon_fit == "firm")
        fit_coupon(0.10, 0.30);
    else
        assert(false, str("unknown coupon_fit: ", coupon_fit));
} else if (variant_render_mode == "clip_coupon") {
    clip_coupon();
} else if (variant_render_mode == "sds_check") {
    sds_check_solid();
} else if (variant_render_mode == "clip_check") {
    clip_check_solid();
} else if (variant_render_mode == "section") {
    intersection() {
        standoff_body();
        translate([-100, -100, -5]) cube([200, 100, 220]);
    }
} else if (variant_render_mode == "none") {
    // Included as a library by verification wrappers.
} else {
    assert(false, str("unknown variant_render_mode: ", variant_render_mode));
}
