// =====================================================================
//  Peak Design opposed-face radio standoff
// =====================================================================
//
//  Two upright, support-free printed parts joined by one M6x30 bolt:
//    fixed stalk  Peak Design 1/4"-20 interface and M6 fork
//    moving head  continuously adjustable -45..+45 degrees
//    +Y face  Uniden SDS150, gravity keyhole
//    -Y face  Kenwood TH-D75A / generic belt-clip bridge
//
//  The Peak Design Standard Plate bears on z=0.  Both radios are upright,
//  displays outward, antennas up.  The SDS150 entry is above its seated
//  position so gravity retains it without a latch.
//
//  Print both parts as exported on their flat lower faces.  Units are mm.
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

// The fixed stalk and adjustable head are separate printable solids.  Both
// are sequences of rounded sections, so the seam reads as an intentional
// circular joint rather than a rectangular block bolted to a post.
stalk_sections = [
    // z,    width X, depth Y, corner radius
    [  8.5,  37.0,    29.0,    5.0],
    [ 20.0,  33.0,    21.0,    5.0],
    [ 50.0,  25.0,    14.0,    4.0],
    [ 82.0,  23.0,    13.0,    4.0],
    [ 92.0,  24.0,    15.0,    4.0]
];

head_sections = [
    [116.0,  11.8,     8.0,    3.0],
    [124.0,  11.8,    10.0,    3.0],
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
waist_cut_z1       = 84.0;

// Continuous pitch joint.  One M6x30 bolt crosses a fork on the stalk and
// the central tongue of the head.  The M6 nut is captive in the right ear;
// the bolt head remains exposed so any normal hex/socket/button head works.
head_angle          = 0.0;  // -45..+45; + presents the SDS display upward
pivot_z             = 108.0;
joint_r             = 13.0;
joint_flat          = 10.0; // lower chord: both parts print on a real flat
joint_ear_t         = 6.6;
joint_gap           = 12.2;
joint_tongue_t      = 11.8;
joint_clearance     = (joint_gap - joint_tongue_t) / 2;
joint_bolt_d        = 6.6;
m6_nut_af           = 10.0;
m6_nut_t            = 5.2;
m6_nut_ac           = m6_nut_af / cos(30);
joint_outer_w       = joint_gap + 2 * joint_ear_t;
joint_root_z        = pivot_z - joint_flat;

// Belt-clip plate: the full-width style shown in the user's final marked-up
// image, shortened to 25mm vertically and moved upward.  Its lower edge is
// z=132, safely above the M6 fork, and the measured 30mm clip section extends
// 5mm below it so the spring tip can close flush against the radio.
clip_bar_top_z     = 157.0;
clip_bar_h         = 25.0;
clip_bar_w         = 35.0;
clip_bar_t         = 3.0;
clip_back_gap      = 7.0;  // clears the M6 fork ears below the clip plate
clip_rail_h        = 0.65;
clip_collar_w      = 1.4;
clip_support_w     = 2.8;
clip_inner_clear   = thd_clip_w_max + 1.0;
clip_outer_clear   = uv5r_clip_env_w + 1.0;
clip_clear_below   = 30.0;

// Diagnostic drivers.  Verification wrappers override these after include.
check_pos          = 0.0;
check_lift         = 0.0;
check_extra        = 0.0;
check_angle        = head_angle;
clip_check_w       = thd_clip_w_max;
clip_check_tip_w   = thd_clip_w_tip;
clip_check_gap     = thd_clip_gap;
clip_check_top_z   = clip_bar_top_z + 1.8;
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

stalk_top_z  = pivot_z + joint_r;
head_top_z   = head_sections[len(head_sections) - 1][0] + section_h;
head_core_face_y = head_sections[len(head_sections) - 1][2] / 2;
front_face_y = head_core_face_y + 5.0;
rear_face_y  = -head_core_face_y;

clip_bar_y1  = rear_face_y - clip_back_gap;     // face nearest spine
clip_bar_y0  = clip_bar_y1 - clip_bar_t;        // face nearest radio
clip_bar_z1  = clip_bar_top_z;
clip_bar_z0  = clip_bar_z1 - clip_bar_h;
clip_bar_z   = (clip_bar_z0 + clip_bar_z1) / 2;
thd_body_z0  = clip_bar_z1 + thd_clip_clear_h - thd_body_h;

head_print_z0 = pivot_z - joint_flat;
head_print_h  = head_top_z - head_print_z0;
joint_ear_x   = joint_gap / 2 + joint_ear_t / 2;
joint_nut_x0  = joint_outer_w / 2 - m6_nut_t;

// =====================================================================
//  5. ASSERTS - confirmations, not the primary design method
// =====================================================================

assert(pd_plate_size == 39.0, "base assumptions require Standard Plate");
assert(base_corner_r < pd_plate_size / 2, "base radius consumes the plate");
assert(sds_travel >= sds_min_travel,
    str("SDS travel ", sds_travel, " is below minimum ", sds_min_travel));
assert(sds_bottom_z >= 20.0,
       str("SDS bottom only clears by ", sds_bottom_z, "mm"));
assert(sds_entry_z + sds_entry_d / 2 < head_top_z,
       "SDS entry hole breaks through the top of the standoff");
assert(front_face_y > sds_stud_depth,
       str("top section is only ", front_face_y,
           "mm deep but SDS channel needs ", sds_stud_depth));
assert(clip_bar_t < thd_clip_gap,
       "clip bridge is thicker than the measured Kenwood gap");
assert(clip_bar_h < clip_clear_below,
    "shortened plate leaves no room for the spring clip to close below it");
assert(clip_bar_z0 > pivot_z + joint_r,
    "clip plate runs into the M6 fork instead of floating above it");
assert(clip_inner_clear > thd_clip_w_max,
       "inner centering rails pinch the Kenwood clip");
assert(clip_outer_clear > uv5r_clip_env_w,
    "bar end supports pinch the conservative 32mm clip envelope");
assert(clip_outer_clear > clip_inner_clear,
    "outer end stops must sit beyond the Kenwood centering collars");
assert(socket_floor >= 1.5,
       str("only ", socket_floor, "mm above the tripod socket"));
assert(head_angle >= -45 && head_angle <= 45,
    str("head angle ", head_angle, " is outside -45..45 degrees"));
assert(joint_clearance >= 0.15 && joint_clearance <= 0.30,
    str("joint side clearance is ", joint_clearance,
        "mm; it must slide before the M6 clamp closes it"));
assert(joint_outer_w <= 26,
    str("M6x30 cannot span a ", joint_outer_w, "mm clevis with margin"));
assert(joint_ear_t >= m6_nut_t + 1.0,
    "the captive M6 nut leaves less than 1mm at the inner friction face");
assert(clip_bar_w <= 40,
    "the belt bar overhangs the adjustable head");
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

module loft_sections(sections) {
    union() {
        for (i = [0 : len(sections) - 2])
            hull() {
                section_node(sections[i]);
                section_node(sections[i + 1]);
            }
    }
}

module head_transform(angle = head_angle) {
    translate([0, 0, pivot_z])
        rotate([angle, 0, 0])
            translate([0, 0, -pivot_z])
                children();
}

// Joint side profile in YZ, centred at the M6 axis.  The circular upper
// region gives broad friction area; the clipped lower chord gives both the
// head and stalk a stable support-free print surface.
module joint_profile_2d() {
    intersection() {
        circle(r = joint_r, $fn = 96);
        // After rotate([0,90,0]), profile X maps to -global Z.  Limiting
        // X to +joint_flat therefore creates z >= pivot_z-joint_flat.
        translate([-joint_r - 1, -joint_r - 1])
            square([joint_r + joint_flat + 1, 2 * joint_r + 2]);
    }
}

module joint_disk_x(thickness) {
    translate([-thickness / 2, 0, pivot_z])
        rotate([0, 90, 0])
            linear_extrude(height = thickness)
                joint_profile_2d();
}

module pivot_hole_x(length, diameter = joint_bolt_d) {
    translate([-length / 2, 0, pivot_z])
        rotate([0, 90, 0])
            cylinder(d = diameter, h = length, $fn = 48);
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

module clip_bar() {
    // Full-width 35x25mm plate, with round top and bottom edges so neither
    // the hinge nor spring tip catches a square printed corner.
    translate([-clip_bar_w / 2, clip_bar_y0,
               clip_bar_z0 + clip_bar_t / 2])
        cube([clip_bar_w, clip_bar_t, clip_bar_h - clip_bar_t]);
    for (z = [clip_bar_z0 + clip_bar_t / 2,
              clip_bar_z1 - clip_bar_t / 2])
        translate([0, (clip_bar_y0 + clip_bar_y1) / 2, z])
            rotate([0, 90, 0])
                cylinder(d = clip_bar_t, h = clip_bar_w,
                         center = true, $fn = 64);

    for (sx = [-1, 1]) {
        x0 = sx * (clip_outer_clear / 2 + clip_support_w / 2);
        translate([x0, (rear_face_y + clip_bar_y1) / 2 + 0.2,
                    clip_bar_z0 + clip_bar_t / 2])
            rounded_box(clip_support_w,
                        rear_face_y - clip_bar_y1 + 0.8,
                        clip_bar_h - clip_bar_t, 0.6);
    }
}

module clip_centering_rails() {
    // Shallow vertical rails centre the measured 21.3mm hinge. Wider clips
    // ride over the 0.65mm rise and stop at 33mm. The local 3.65mm thickness
    // stays inside the measured 4.5mm gap.
    for (sx = [-1, 1])
        translate([sx * (clip_inner_clear / 2 + clip_collar_w / 2),
                   clip_bar_y0 - clip_rail_h / 2 + 0.05,
                   clip_bar_z0 + clip_bar_t / 2])
            rounded_box(clip_collar_w, clip_rail_h + 0.1,
                        clip_bar_h - clip_bar_t, 0.3);
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

module fork_ear(sx) {
    x = sx * joint_ear_x;
    hull() {
        translate([x, 0, 0])
            joint_disk_x(joint_ear_t);
        translate([x, 0, 91.0])
            rounded_box(joint_ear_t, 13.0, 5.0, 2.0);
    }
}

module fork_outer() {
    union() {
        fork_ear(-1);
        fork_ear(1);
    }
}

module fork_voids() {
    pivot_hole_x(joint_outer_w + 2.0);

    // Captive ISO-style M6 nut, inserted from the right.  A 1.4mm inner
    // wall remains as the friction face; the nut cannot spin when the
    // exposed bolt head is tightened.
    translate([joint_nut_x0, 0, pivot_z])
        rotate([0, 90, 0])
            cylinder(d = m6_nut_ac, h = m6_nut_t + 0.2, $fn = 6);
}

module stalk_body() {
    difference() {
        union() {
            base_outer();
            loft_sections(stalk_sections);
            fork_outer();
        }

        tripod_socket_void();
        fork_voids();

        if (waist_cut)
            waist_void();
    }
}

module head_neutral(fit_preload = standoff_preload,
                    fit_slide = standoff_clr_slide) {
    difference() {
        union() {
            joint_disk_x(joint_tongue_t);
            loft_sections(head_sections);
            // Broad bearing pad clears the fork ears and supports the
            // SDS pedestal without the side guides the user rejected.
            translate([0, 9.2, pivot_z + joint_r + 0.2])
                rounded_box(34.0, 9.6,
                            head_top_z - (pivot_z + joint_r + 0.2), 3.0);
            clip_bar();
            clip_centering_rails();
        }

        sds_voids(fit_preload = fit_preload, fit_slide = fit_slide);
        pivot_hole_x(joint_tongue_t + 2.0);
    }
}

module head_body(angle = head_angle,
                 fit_preload = standoff_preload,
                 fit_slide = standoff_clr_slide) {
    head_transform(angle)
        render(convexity = 12)
            head_neutral(fit_preload = fit_preload, fit_slide = fit_slide);
}

module head_print_oriented(fit_preload = standoff_preload,
                           fit_slide = standoff_clr_slide) {
    translate([0, 0, -head_print_z0])
        head_neutral(fit_preload = fit_preload, fit_slide = fit_slide);
}

module articulated_assembly(angle = head_angle) {
    stalk_body();
    head_body(angle);
}

module joint_hardware_reference() {
    // M6x30 bolt axis and captive nut, diagnostic only.
    color([0.65, 0.67, 0.70])
        pivot_hole_x(30.0, 6.0);
    color([0.45, 0.46, 0.48])
        translate([joint_nut_x0, 0, pivot_z])
            rotate([0, 90, 0])
                cylinder(d = m6_nut_ac, h = m6_nut_t, $fn = 6);
}

module stalk_head_intersection(angle = head_angle) {
    intersection() {
        stalk_body();
        head_body(angle);
    }
}

module sds_reference(pos = check_pos, angle = check_angle) {
    // Back panel is 6mm outward from the bearing face because the measured
    // pedestal stands 6mm proud.  Transparent in assembly render only.
    head_transform(angle)
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

module thd_reference(dz = clip_check_dz, angle = check_angle) {
    // The body's rear plane rests on the outer face of the clip bar.
    head_transform(angle) {
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
}

module sds_check_solid() {
    head_transform(check_angle)
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
    test_h = clip_clear_below;
    rides_rails = width > clip_inner_clear;
    radio_y = clip_bar_y0 - (rides_rails ? clip_rail_h : 0) - 0.20;
    clip_inner_y = radio_y + gap;

        head_transform(check_angle)
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
    // Crop the real rear interface, preserving its shortened plate, rails,
    // gap, and end supports.  The head supplies a flat backing section.
    translate([0, 0, -(clip_bar_z0 - 2.0)])
        intersection() {
            head_neutral();
            translate([-23, -24, clip_bar_z0 - 2.0])
                cube([46, 30, clip_bar_h + 4.0]);
        }
}

module joint_coupon_stalk() {
    union() {
        translate([0, 0, -joint_root_z])
            intersection() {
                stalk_body();
                translate([-16, -15, joint_root_z]) cube([32, 30, 24]);
            }
        // Test-only bridge; the full stalk connects the ears below this
        // crop, so the coupon needs an equivalent printable connection.
        rounded_box(joint_outer_w, 18.0, 3.0, 2.0);
    }
}

module joint_coupon_head() {
    translate([0, 0, -joint_root_z])
        intersection() {
            head_neutral();
            translate([-16, -15, joint_root_z])
                cube([32, 30, joint_r + joint_flat]);
        }
}

// =====================================================================
//  8. REPORT AND ENTRY POINT
// =====================================================================

echo(str("RADIO STANDOFF  style=", thread_style,
         " base=", pd_plate_size, "x", pd_plate_size,
         " pivot_z=", pivot_z,
         " neutral_height=", head_top_z));
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
echo(str("  CLIP bar_w=", clip_bar_w,
         " bar_h=", clip_bar_h,
         " bar_t=", clip_bar_t,
         " bar_z=", clip_bar_z,
         " clear_below=", clip_clear_below,
         " gap=", clip_back_gap,
         " clear=", clip_inner_clear, "..", clip_outer_clear));
echo(str("  CLIPCHECK bar_t=", clip_bar_t,
         " bar_top=", clip_bar_z1,
         " plate_t=", clip_check_plate_t,
         " test_h=", clip_clear_below,
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
echo(str("  JOINT angle=", head_angle,
         " r=", joint_r,
         " outer_w=", joint_outer_w,
         " ear_t=", joint_ear_t,
         " ear_free=", pivot_z - 91.0,
         " tongue=", joint_tongue_t,
         " gap=", joint_gap,
         " side_clr=", joint_clearance,
         " bolt_d=", joint_bolt_d,
         " nut_af=", m6_nut_af,
         " nut_t=", m6_nut_t));
for (s = stalk_sections)
    echo(str("  SECTION z=", s[0], " w=", s[1], " d=", s[2]));
for (s = head_sections)
    echo(str("  HEADSECTION z=", s[0], " w=", s[1], " d=", s[2]));

variant_render_mode = "assembly";

if (variant_render_mode == "stalk") {
    stalk_body();
} else if (variant_render_mode == "head") {
    head_print_oriented(standoff_preload, standoff_clr_slide);
} else if (variant_render_mode == "head_neutral") {
    head_neutral(standoff_preload, standoff_clr_slide);
} else if (variant_render_mode == "head_positioned") {
    head_body(head_angle, standoff_preload, standoff_clr_slide);
} else if (variant_render_mode == "body") {
    articulated_assembly(head_angle); // compatibility/preview alias
} else if (variant_render_mode == "assembly") {
    color([0.12, 0.12, 0.14]) stalk_body();
    color([0.18, 0.18, 0.21]) head_body(head_angle);
    joint_hardware_reference();
    sds_reference(angle = head_angle);
    thd_reference(angle = head_angle);
} else if (variant_render_mode == "assembly_parts") {
    articulated_assembly(head_angle);
} else if (variant_render_mode == "joint_intersection") {
    stalk_head_intersection(head_angle);
} else if (variant_render_mode == "sds_reference") {
    sds_reference(angle = check_angle);
} else if (variant_render_mode == "thd_reference") {
    thd_reference(angle = check_angle);
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
} else if (variant_render_mode == "joint_coupon_stalk") {
    joint_coupon_stalk();
} else if (variant_render_mode == "joint_coupon_head") {
    joint_coupon_head();
} else if (variant_render_mode == "sds_check") {
    sds_check_solid();
} else if (variant_render_mode == "clip_check") {
    clip_check_solid();
} else if (variant_render_mode == "section") {
    intersection() {
        articulated_assembly(head_angle);
        translate([-100, -100, -5]) cube([200, 100, 220]);
    }
} else if (variant_render_mode == "none") {
    // Included as a library by verification wrappers.
} else {
    assert(false, str("unknown variant_render_mode: ", variant_render_mode));
}
