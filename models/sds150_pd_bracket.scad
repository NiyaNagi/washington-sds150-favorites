// =====================================================================
//  SDS150 -> Peak Design Capture bracket
// =====================================================================
//
//  A flat plate that captures the Uniden SDS150 by its belt-clip stud,
//  with a 1/4"-20 tripod socket for a Peak Design Capture plate.
//
//  Stud dimensions and keyhole clearances live in sds150_stud.scad,
//  shared with the visor mount.  Edit fit there, not here.
//
//
//  HOW IT WORKS
//  ------------
//  1. The stud's head passes through the round entry hole at the TOP.
//  2. Let the radio drop.  The head runs down a hidden channel; the neck
//     runs in the slot above it.  On the way the neck rides over a ramp
//     and pushes a sprung latch aside.
//  3. At the bottom the latch springs back above the neck, blocking it
//     from rising.  The radio is captive.
//  4. To remove: press the paddle on the right-hand edge, lift the radio,
//     and take it off through the entry hole.
//
//  Gravity does useful work here.  The entry hole is at the top and the
//  locked position at the bottom, so the radio's own weight holds the
//  stud AWAY from the only opening.  Escaping needs a deliberate lift
//  against gravity as well as a press on the latch, so the latch only has
//  to cope with knocks and with the bracket being inverted - much lighter
//  duty than a latch that has to carry the radio.
//
//
//  WHERE THE SCREW GOES, AND WHY
//  -----------------------------
//  The radio hangs BELOW the mounting point, so the tripod socket is at
//  the top of the plate and the keyhole below it.  That is the only
//  arrangement that puts the radio under a Capture clip rather than
//  standing it up past your shoulder.
//
//  Two things have to be true at once, and they pull against each other:
//
//    * The screw must be ABOVE the stud, or the radio does not hang from
//      the clip - it stands on it.
//    * The stud must still enter at the TOP of its slot and drop DOWN to
//      lock, or gravity stops helping and starts hurting: the radio's own
//      weight would work it back toward the opening.
//
//  So the keyhole keeps its internal sense - entry hole above, locked
//  position below - and the whole assembly moves down the plate, with the
//  socket taking the space above the entry hole.  The latch is NOT
//  reversed relative to the keyhole.  Reversing it would put the tooth
//  below the neck, where it blocks nothing: the stud escapes upward, so
//  the tooth has to sit above it whichever way round the plate is.
//
//  The screw stays on the x = 0 centreline.  Gravity acts along -Y and
//  the stud sits on that same line, so there is no lever arm for the
//  radio's weight and no twisting moment about the screw.  An offset in X
//  would not be free - it would hang the radio to one side of its own
//  support and try to rotate it.
//
//  An earlier version put the socket directly behind the stud.  That left
//  a 1.48mm membrane between the screw hole and the head channel with the
//  radio's whole weight on it in bending, and needed a 6mm boss to claw
//  back the thread depth - which is what made the part 15.75mm thick.
//  Clear of the keyhole the socket threads into the plate's full
//  thickness and needs no boss at all.
//
//
//  MAKING THE LATCH ACTUALLY MOVE
//  ------------------------------
//  The first version of this latch had a throw of 1.44mm at the paddle.
//  That is not enough to feel.  The pad of a thumb compresses further
//  than that, so pressing it seemed to do nothing at all even though the
//  tooth was clearing the neck properly.
//
//  Paddle travel is arm_tab * sin(theta), and flexure strain is
//  theta * t / (2 * L).  Travel can therefore be bought two ways, and
//  only one of them is cheap:
//
//    * A LONGER TAB ARM costs nothing in strain.  It lengthens the plate
//      downward, and nothing else.
//    * A LARGER ANGLE costs strain, and worse, swings the tooth further
//      ALONG the slot.  The tooth sits about 19mm from the pivot in X, so
//      it travels roughly that times sin(theta) in Y - push the angle and
//      the tooth's relief marches up the slot and eats into the entry
//      hole, which then has to move further away in turn.
//
//  Both routes make the plate bigger, in different directions, so the
//  numbers below sit near the middle: 8 degrees of rotation, a 21.6mm tab
//  arm, 3.0mm of paddle travel, and a flexure long enough to keep peak
//  strain under 0.8% even at the over-pressed angle the relief is cut for.
//  The press also got lighter on the way - a longer arm needs less force
//  for the same torque - while the shorter tooth arm HOLDS harder.
//
//
//  WHY THE LATCH FLEXES SIDEWAYS
//  -----------------------------
//  The visor mount's latch is a flat tongue underneath the head channel
//  that flexes downward, which costs tongue thickness plus a flex void
//  beneath it - about 6mm of extra plate.  Here the latch is a full-depth
//  bar beside the slot that flexes IN THE PLANE of the plate, so it needs
//  no room underneath at all.
//
//  It is a lever, not a simple cantilever.  A cantilever moves its tip
//  and its tooth in the SAME direction, so a push tab could only ever
//  drive the tooth further into the slot - that mistake cost a full
//  redesign on the visor mount.  Pivoting the bar reverses the sense:
//  press the paddle, and the tooth, on the far side of the pivot, swings
//  outward and frees the neck.
//
//  Rotation moves every point of the lever on a CIRCLE about the pivot.
//  A point at radius r moves r*sin(theta), and it moves in BOTH X and Y:
//  the X component comes from how far the point sits from the pivot in Y,
//  and the Y component from how far it sits in X.  The tooth is about
//  15mm from the pivot along X, so it sweeps a long way in Y even though
//  it only needs to retract about 1mm in X.  The relief has to allow for
//  both.
//
//  Getting this wrong is easy and quiet.  An earlier version sized the
//  tooth relief from the SLOT EDGE rather than the pivot, understating
//  the sweep by half, and the fit checks passed anyway - because the
//  relief and the lever were generated from the same outline, so the same
//  error appeared in both and they still seemed to fit.  The sweep is now
//  computed from the pivot, and check_pd_sweep.py verifies it against the
//  actual rotated solid rather than against the formula that produced it.
//
//
//  Coordinates: the bearing face - which the radio's raised pedestal
//  touches - is z = 0 and sits on the build plate.  Material runs upward.
//  The slot runs along Y with the entry hole at +Y.  That is already the
//  print orientation, so nothing is rotated on export.
//
// =====================================================================

include <sds150_stud.scad>

// Extra depth in the head channel, on top of the shared baseline.
//
// This part is a flat plate printed face-down, so the channel's roof is
// an unsupported bridge about 16mm across.  Bridged filament sags, and
// the sag eats into the very gap the stud head has to slide along - so
// the channel comes out shallower than modelled.  The visor mount runs
// the same nominal clearance and fits, because there the channel is
// buried in a solid block with no bridge to sag.
//
// Set here rather than in sds150_stud.scad precisely so the visor mount
// does NOT move: it is a snug but working fit and there is no reason to
// loosen it.  See the note beside head_ch_clr_z_base.
//
// If the head still binds, raise this before touching anything else -
// it is the only number here that is about the printer rather than the
// radio.  Every 0.05 costs 0.05mm of plate thickness and nothing else.
head_ch_clr_extra = 0.25;  // mm  -> channel 3.65mm, plate 10.00mm


// ---------------------------------------------------------------------
//  1. KEYHOLE
// ---------------------------------------------------------------------

// How far the radio drops to lock.
//
// Must exceed min_travel, computed in sds150_stud.scad as
// (entry_d + stud_head_d)/2 = 15.93mm.  Any shorter and part of the head
// still sits under the open entry hole when "locked", where it can lift
// and tilt free.  The build asserts this.
//
// Set above the minimum on purpose.  The latch tooth swings up the slot
// as it retracts - it sits ~19mm from the pivot in X, so a few degrees of
// rotation carries it several millimetres along Y - and its relief has to
// stay clear of the entry hole.  At the bare minimum travel the two run
// into each other.  The assert further down measures the wall that is
// actually left.
travel           = 21.0;   // mm

base_t           = 2.0;    // solid material behind the head channel, mm


// ---------------------------------------------------------------------
//  2. LATCH
// ---------------------------------------------------------------------

// Gap all round the moving parts.  Rather more than two extrusion widths
// at a 0.4mm nozzle, so the latch cannot fuse to the body in the print.
lever_clr        = 0.90;   // mm

// Material left between the stud's head channel and the latch's relief
// slot.
//
// This is not optional trim.  Set the latch hard against the channel and
// the two voids merge into one, so the head channel is open along its
// whole length into the latch slot - there is no wall at all, and the
// head has nothing holding it in sideways.
chan_wall        = 1.60;   // mm

lever_w          = 4.0;    // width of the lever bar, mm
bar_top          = 10.0;   // bar's upper end, mm from the locked stud
                           // The bar's lower end is not set here: it is
                           // exactly where the tab arm leaves it, since
                           // any bar below that carries no load and only
                           // pushes the relief - and the plate - further
                           // down.  See bar_bot under DERIVED.

// Flexural pivot: a short thin ligament joining the bar to the body, so
// the bar rotates about one known place instead of bending along its
// whole length.
//
// Long, because length is what buys rotation.  Strain is theta*t/(2*L),
// so a longer ligament lets the lever turn further before the plastic
// complains - and turning further is the whole point after the first
// version moved only 1.44mm at the paddle.  At 15mm the flexure still
// needs plate outboard of it to anchor into, which is what sets
// plate_x_hi.
pivot_y          = -1.9;   // mm
flex_len         = 15.0;   // free length of the ligament, mm
flex_t           = 1.25;   // its thickness, mm
                           // Also the thinnest material in the part, so
                           // it sets what the wall check reports.  Kept a
                           // little above the 1.2mm floor rather than on
                           // it, so a genuine thin wall elsewhere is not
                           // masked by the flexure sitting exactly at the
                           // limit.
flex_root        = 1.5;    // how far it is buried at each end, mm

// The tooth that blocks the neck from rising.  It reaches inward across
// the ledge to overlap the neck slot.
//
// tooth_y0 must clear the locked neck, whose top edge is at
// stud_neck_d/2 = 4.15mm, or the tooth would foul the stud when seated.
detent_bump      = 1.40;   // how far it intrudes into the slot, mm
tooth_y0         = 4.80;   // tooth's lower, blocking edge, mm
tooth_y1         = 7.20;   // its upper edge, mm
                           // Not free to grow.  The tooth's swept relief
                           // runs up alongside the neck slot, and the two
                           // pinch the ledge between them: at 7.6 the wall
                           // there drops to 1.14mm, under what a 0.4mm
                           // nozzle prints as a wall rather than a skin.
tooth_lead       = 1.80;   // ramp on the UPPER edge, so the neck coming
                           // down pushes the tooth aside, mm

// How far the tooth's RELIEF reaches into the neck slot.
//
// Just inside the edge.  Inboard of the edge the slot is already void, so
// relief there removes nothing - but it does swing, and the further
// inboard it starts the further it swings.  A relief taken right across
// the slot put its inboard corner 26mm from the pivot, which threw it 5mm
// up the plate and left it 0.2mm from the entry hole: the notch that
// showed up beside the keyhole in the first print.
//
// It has to overlap rather than just touch, or the two voids meet on a
// coincident face and leave a whisker of plastic a tenth of a millimetre
// thick between them.
tooth_relief_inset = 0.5;  // mm past the slot edge

// The thumb paddle.
//
// Sized to be pressed, not merely to exist.  The previous version ended
// the lever in a bare 4mm-wide bar with square corners: the contact patch
// was narrower than a fingertip, so all the force landed on two sharp
// edges.  This paddle is wide enough to find without looking, dished so
// the thumb settles into it instead of sliding off, and rounded on every
// face a finger can reach.
//
// It also sits FURTHER from the pivot than the tooth does, which is what
// makes the press feel like a press.  Lever displacement scales with
// distance from the pivot, so a paddle closer in than the tooth would
// move less than the 1.1mm the tooth has to retract - a throw too small
// to distinguish from flex in your own thumb.  At 21.6mm out against the
// tooth's 7.9mm it travels 3.0mm, and the longer arm lightens the push at
// the same time.
tab_y0           = -26.0;  // tab arm's lower edge, mm
tab_y1           = -21.0;  // its upper edge, mm

// The lever bar stops where the tab arm leaves it.  Bar below that point
// carries nothing, and its relief would only push the plate's bottom edge
// further down to keep a margin under it.
//
// Defined here rather than with the other derived values because those
// are computed further down the file, and OpenSCAD does not resolve a
// forward reference like this reliably - it evaluated to undef and took
// three other quantities with it.
bar_bot          = tab_y0;

// How far the paddle reaches past the plate edge.
//
// Long enough that the paddle clears the RADIO, not just the plate.  The
// radio hangs below the screw and its stud is roughly centred across its
// ~70mm width, so its right-hand edge sits about 35mm from the slot
// centreline.  A paddle inboard of that is tucked behind the radio and
// awkward to find, even though the two never actually touch - the radio
// sits in front of the bearing face and the paddle is inside the plate's
// thickness.
//
// This is not a fit constraint, it is a reach constraint, which is why no
// interference check catches it.  The assert below states it explicitly.
tab_protrude     = 11.0;   // mm
paddle_w         = 18.0;   // paddle height along Y, mm
paddle_t         = 3.4;    // paddle thickness in X, mm
paddle_r         = 1.5;    // rounding on its edges, mm
paddle_dish      = 0.9;    // depth of the thumb dish, mm

// Whether the latch is shown deflected, as if under a thumb.  false is
// the resting state, which is what gets exported; the fit checks set it
// true to measure that pressing really does free the stud.
//
// A boolean rather than an angle, because an including file cannot refer
// to values computed inside the include - the deflection is worked out
// below, from the geometry, so it always matches what the design needs.
lever_pressed    = false;

// Extra rotation allowed for over the angle strictly needed.  A latch
// that only just clears at the exact design angle has no margin for print
// tolerance, and a thumb will always push further than the minimum.
press_margin     = 1.35;


// ---------------------------------------------------------------------
//  3. PLATE
// ---------------------------------------------------------------------

// The plate's OUTLINE is not set here - it is derived, further down,
// from everything that has to fit inside it.  Hand-setting the edges is
// what let the Peak Design plate hang 9.5mm off the top: the number was
// written once, the socket moved later, and nothing connected the two.
// Only the shaping and the margins are choices.
plate_r          =   4.0;  // corner radius, mm
plate_edge_r     =   1.0;  // rounding on the outer edges, mm

pd_margin        =   2.5;  // plate kept this far beyond the PD plate, mm
latch_margin     =   2.0;  // and this far beyond the latch's relief, mm
keyhole_margin   =   3.0;  // and this far beyond the keyhole, mm
flex_anchor_wall =   1.5;  // body left outboard of the flexure, mm


// ---------------------------------------------------------------------
//  4. WHAT THE BRACKET HAS TO SUIT
// ---------------------------------------------------------------------
//
// Neither of these is under this model's control.  They are here because
// the plate is sized around them, and because if either turns out to be
// wrong it should be one number to correct, not a hunt through derived
// arithmetic.

// Peak Design Capture plate: square, with the 1/4"-20 hole at its centre.
// The whole square must land on solid bracket or the plate sits on its
// own edge and rocks, which no amount of screw torque fixes.
//
// Worth confirming with calipers against your own plate - it is the one
// dimension here taken from a spec rather than measured, and it drives
// the size of the whole part.  The Dual Plate is longer in one axis; set
// pd_plate_size to its LONGER dimension if you use one.
pd_plate_size    = 39.0;   // mm square

// The radio hangs in front of the bracket.  Nothing collides with it -
// it sits off the bearing face - but it does hide anything inboard of
// its edge, which is what the thumb paddle has to reach past.
radio_width      = 69.9;   // Uniden SDS150 body, mm


// ---------------------------------------------------------------------
//  4. TRIPOD SOCKET
// ---------------------------------------------------------------------

// Where the screw goes, measured from the locked stud.  Derived, not
// chosen: it sits on the x = 0 centreline with the stud, and just far
// enough above the ENTRY HOLE - the widest part of the keyhole - to clear
// it.  See the DERIVED section.
//
// Above the stud, so the radio hangs from the clip rather than standing
// on it.  On the centreline, because gravity acts along -Y: with stud and
// screw on one vertical line the radio's weight has no lever arm and
// produces no twisting moment about the screw.  Any offset in X would.
//
// Clear of the keyhole, because the socket is a deep blind hole - 8.25mm
// into a 9.75mm plate for the self-tapping version - so it would break
// straight through into the slot the stud runs in.
socket_clear     =   2.0;  // wall between socket and keyhole, mm

// 1/4"-20 UNC, the tripod standard.
thread_major     = 6.35;   // mm
thread_pitch     = 1.27;   // mm  (20 threads per inch)

// How the socket is made:
//
//   "self_tap"  a plain undersize hole that the steel screw cuts its own
//               thread into.  Prints perfectly, and usually holds BETTER
//               than a printed thread because the formed thread comes out
//               full depth.  The default, and the one to try first.
//
//   "insert"    a counterbore for a 1/4"-20 brass heat-set insert.
//               Strongest by a wide margin.  Needs a soldering iron.
//               Worth it if the plate comes on and off often, since a
//               thread formed in PLA wears with repeated cycles.
//
//   "nut"       a hex pocket for a captive 1/4"-20 nut, dropped in from
//               the back before the plate goes on.
//
// There is deliberately no modelled-helix option.  At a 0.4mm nozzle a
// 1/4"-20 thread form is only 0.69mm deep and its crests come to a knife
// edge - wall checks measured 0.004mm - so it prints mushy and holds
// worse than simply letting the screw tap the plastic itself.  It was
// tried, measured, and dropped rather than left in as a trap.
//
// The radio's weight is not what threatens this joint: with the socket in
// solid plate the shear area is far beyond what ~400g demands.  The real
// risk is over-torquing while fitting the plate.
thread_style     = "self_tap";

self_tap_d       = 5.40;   // hole the screw forms its own thread in, mm
insert_d         = 7.60;   // heat-set insert outside diameter, mm
insert_depth     = 6.00;   // how deep it seats, mm
nut_af           = 11.15;  // 1/4" nut across the flats, mm
nut_t            = 5.60;   // its thickness, mm

// Optional shallow recess in the back face, keyed to the Peak Design
// plate so a single screw cannot let it rotate.  Left off because the
// plate has not been measured - a flat back works with any 1/4"-20 plate
// meanwhile, and PD's rubber pad normally stops rotation on its own.
plate_recess      = false;
plate_recess_size = 39.0;  // mm square
plate_recess_d    = 1.0;   // depth, mm


// ---------------------------------------------------------------------
//  5. PEDESTAL POCKET  (anti-rotation, off by default)
// ---------------------------------------------------------------------

// A round stud in a round slot does not resist rotation - only friction
// from the ledge preload does.
//
// It is off here because those walls rise from the bearing face, which is
// the face resting on the build plate: they would print into thin air and
// need supports right through the latch.
//
// If the radio does rotate in use, raise `preload` in sds150_stud.scad
// first - that is what generates the friction holding it still.
capture_pedestal  = false;
skirt_h           = 3.0;   // pocket depth if enabled, mm

$fa = 2;
$fs = 0.4;


// =====================================================================
//  DERIVED - computed, not edited
// =====================================================================

// Z stack, measured up from the bearing face on the build plate.
z_ledge_top = ledge_t;                   // top of the ledge
z_chan_top  = z_ledge_top + head_ch_h;   // top of the head channel
plate_t     = z_chan_top + base_t;       // back face of the plate

// The latch bar sits outside the head channel, with a real wall between
// the two, so it never fouls the stud head.  Only its tooth reaches
// inward, and only through the ledge, where the slot is narrower.
//
// lever_clr is subtracted back off because the relief is generated by
// growing the bar's outline by that clearance - so the relief's inner
// face lands exactly chan_wall clear of the channel.
lever_x0    = head_ch_w / 2 + chan_wall + lever_clr;
lever_x1    = lever_x0 + lever_w;
tooth_x     = neck_w / 2 - detent_bump;  // how far the tooth reaches in

// How far the tooth must retract for the neck to pass.  Less than
// detent_bump, because the slot is already wider than the neck.
tooth_retract = stud_neck_d / 2 - tooth_x;

// Where the lever turns.  Pressing the paddle inward (-X) has to swing
// the tooth outward (+X); since paddle and tooth sit on opposite sides of
// this point, one rotation does both.
pivot_x     = lever_x1 + flex_len / 2;
pivot_ctr   = [pivot_x, pivot_y];

// Lever arms about the pivot, measured along Y, since that is the
// direction the tooth and paddle are offset from it.
arm_tooth   = (tooth_y0 + tooth_y1) / 2 - pivot_y;
arm_tab     = pivot_y - (tab_y0 + tab_y1) / 2;
lever_gain  = arm_tooth / arm_tab;
tab_travel  = tooth_retract / lever_gain;
lever_angle = asin(tooth_retract / arm_tooth);          // degrees
flex_strain = (lever_angle * PI / 180 / flex_len) * (flex_t / 2);

// Deflection actually applied when the latch is drawn pressed.
lever_press = lever_pressed ? lever_angle * press_margin : 0;

// How far parts of the lever travel when it rotates.
//
// Rotation carries every point around the PIVOT, so the distances that
// matter are measured from there - not from the slot edge.  A point
// offset dx, dy from the pivot moves about dy*sin(a) in X and dx*sin(a)
// in Y.  The tooth's dx is large, so its Y sweep dominates.
//
// These figures are reported rather than used to inflate the relief: the
// relief is built by sweeping the real outline through the real rotation
// (see lever_swept_2d).  They are here so the echo shows how far things
// actually move, which is what made the earlier error visible.
sweep_ang     = lever_angle * press_margin;
tooth_dx      = pivot_x - tooth_x;
tooth_dy      = (tooth_y0 + tooth_y1) / 2 - pivot_y;
tooth_sweep_x = abs(tooth_dy) * sin(sweep_ang);
tooth_sweep_y = abs(tooth_dx) * sin(sweep_ang);

// The bar and its arm swing too, and their far ends sit further from the
// pivot than the tooth does.
bar_swing = max(abs(bar_top - pivot_y), abs(bar_bot - pivot_y))
            * sin(sweep_ang);

thread_minor = thread_major - 1.0825 * thread_pitch;   // for reference

// Depth of the socket, and the floor left under it.  The screw must not
// burst through the bearing face the radio sits against.
socket_depth = thread_style == "insert" ? insert_depth
             : thread_style == "nut"    ? nut_t
             :                            plate_t - 1.5;

// The hex nut's ACROSS-CORNERS size is what the pocket must swallow, not
// the across-flats figure quoted on the packet.  Getting this wrong left
// a 1.06mm wall on an earlier version.
nut_across_corners = nut_af / cos(30);

socket_widest = thread_style == "nut"    ? nut_across_corners
              : thread_style == "insert" ? insert_d
              :                            self_tap_d;

// The widest any style gets.  The socket is placed to suit THIS rather
// than whichever style is being built, so all three variants come out the
// same size and a plate fitted to one will fit another.
socket_widest_any = max(self_tap_d, insert_d, nut_across_corners);

// Diameter of the socket where it breaks the back face - the mouth
// chamfer, which is wider than any of the bores.  Named rather than
// written twice: the coverage check has to know how much of the back face
// is legitimately missing, and a second copy of "+ 1.6" would drift.
socket_mouth_d = thread_major + 1.6;

// What the socket actually opens as ON THE BACK FACE - the surface the
// Peak Design plate beds against.
//
// For the nut style that is the hex pocket, not the chamfer: the pocket
// is cut to the back face so the nut drops in flush, and it is far wider
// than the screw hole.  The plate still beds properly, on the nut's own
// face, but a coverage check that assumed the smaller opening counted the
// pocket as missing material and failed the nut variant on its own
// design.
socket_face_d = thread_style == "nut" ? nut_across_corners
                                      : socket_mouth_d;

// Where the tooth's relief stops on its inboard side - just inside the
// neck slot, which is void anyway.
relief_clip_x = neck_w / 2 - tooth_relief_inset;

// ---- where the screw ends up ------------------------------------------
socket_x = 0;
socket_y = travel + entry_d / 2 + socket_widest_any / 2 + socket_clear;

// ---- and therefore how big the plate has to be ------------------------
//
// Every edge is derived from something real:
//
//   right   the flexure needs body outboard of it to anchor into, and the
//           plate's rounded edge eats into that, so it counts.
//   left    the keyhole, or the PD plate - whichever reaches further.
//   top     the PD plate.  Nothing else is up there.
//   bottom  the latch's swept relief, or the PD plate.
//
// Derived rather than typed, because a typed edge does not move when the
// thing it was covering does.  That is exactly how the PD plate came to
// hang 9.5mm off the top: the number was written when the socket was
// somewhere else, and nothing connected the two.
//
// pd_need is the half-width the plate has to reach from the screw.  It
// includes plate_edge_r because the PD plate does not bear on the nominal
// outline - it bears on the BACK FACE, which the rounded outer edge insets
// by exactly that much.  Leave it out and the outermost millimetre of
// support is a chamfer the plate slides off.
pd_need = pd_plate_size / 2 + pd_margin + plate_edge_r;

plate_x_hi = max(lever_x1 + flex_len + plate_edge_r + flex_anchor_wall,
                 socket_x + pd_need);

plate_x_lo = min(-entry_d / 2 - keyhole_margin,
                 socket_x - pd_need);

plate_y_hi = socket_y + pd_need;

// Inner face of the thumb paddle.  The tab arm runs out to meet it.
paddle_x0 = plate_x_hi + tab_protrude - paddle_t;
paddle_yc = (tab_y0 + tab_y1) / 2;

// The paddle hangs lower than the bar, and swings lower still as the
// lever turns - it sits far out along X, and X offset from the pivot is
// what becomes Y movement.  Measuring the bottom from bar_bot alone
// understated this by 6.5mm and let the plate clip the paddle's relief
// into a feather edge.
paddle_drop  = (paddle_x0 - pivot_x) * sin(sweep_ang);
latch_bottom = min(bar_bot, paddle_yc - paddle_w / 2)
               - lever_clr - paddle_drop;

plate_y_lo = min(latch_bottom - latch_margin,
                 socket_y - pd_need);

echo(str("PD BRACKET  plate=", plate_x_hi - plate_x_lo, " x ",
         plate_y_hi - plate_y_lo, " x ", plate_t, "  (flat, no boss)",
         "  travel=", travel, " (min ", min_travel, ")"));
echo(str("  SOCKET  ", thread_style, " at (", socket_x, ",", socket_y,
         ") - above the keyhole, so the radio hangs below",
         "  depth=", socket_depth, " floor=", plate_t - socket_depth));
echo(str("  LATCH   retract=", tooth_retract,
         "  angle=", lever_angle, " deg",
         "  paddle travel=", tab_travel, " mm",
         "  strain=", flex_strain * 100, "% (",
         flex_strain * press_margin * 100, "% pressed)"));
echo(str("  SWEEP   tooth dx=", tooth_sweep_x, " dy=", tooth_sweep_y,
         "  bar=", bar_swing, "  at ", sweep_ang, " deg"));

assert(travel >= min_travel,
       str("travel is too short - the stud head would still overlap the ",
           "entry hole.  Needs at least ", min_travel, "mm."));

// ---- socket clearances -------------------------------------------------
//
// The screw must not break into the stud's slot.  This is the mistake an
// earlier version made: it sat the socket directly behind the head
// channel, leaving 1.48mm of plate between them with the radio's whole
// weight on it.
//
// Both tests below measure a real 2D distance.  Comparing a single axis
// has bitten this file twice - once claiming a clash between parts that
// never shared any X, once missing one that did - and now that the socket
// has moved from below the keyhole to above it, an axis-specific test
// would simply be measuring the wrong gap.

// Distance from a point to a vertical line segment running x = 0,
// y = ay .. by.
function dist_to_slot(px, py, ay, by) =
      py < ay ? sqrt(px * px + (py - ay) * (py - ay))
    : py > by ? sqrt(px * px + (py - by) * (py - by))
    :           abs(px);

// The keyhole in plan is the neck slot capsule unioned with the entry
// circle, so the clearance is whichever of the two is nearer.
keyhole_gap = min(
    dist_to_slot(socket_x, socket_y, 0, travel) - neck_w / 2,
    sqrt(pow(socket_x, 2) + pow(socket_y - travel, 2)) - entry_d / 2
) - socket_widest / 2;

// socket_y is derived to give exactly socket_clear here, so this is a
// confirmation rather than a constraint - but it is worth keeping, since
// it checks the finished arithmetic rather than the intent, and it is the
// derivation itself that would be wrong if this ever failed.
//
// Compared with a small tolerance because the two are equal by
// construction, and exact equality in floating point is a coin toss: the
// nut variant, whose socket IS the widest, came out at 1.99999999 and
// failed an assert against its own design value.
assert(keyhole_gap >= socket_clear - 1e-6,
       str("only ", keyhole_gap, "mm between the tripod socket at (",
           socket_x, ",", socket_y, ") and the keyhole - the screw would ",
           "break through into the slot the stud runs in"));

// And it must clear the latch, or the screw fouls the moving parts.
//
// The latch's relief is treated as one rectangle covering the bar, its
// swing, and the tab arm out to the paddle.  That is conservative, which
// is the right way round for a clearance test.
relief_x_lo = lever_x0 - lever_clr - bar_swing;
relief_x_hi = plate_x_hi + tab_protrude;
relief_y_lo = bar_bot - lever_clr - bar_swing;
relief_y_hi = bar_top + lever_clr + bar_swing;

socket_dx = max(relief_x_lo - socket_x, socket_x - relief_x_hi, 0);
socket_dy = max(relief_y_lo - socket_y, socket_y - relief_y_hi, 0);

latch_gap = sqrt(pow(socket_dx, 2) + pow(socket_dy, 2))
            - socket_widest / 2;

assert(latch_gap >= 2.0,
       str("only ", latch_gap, "mm between the tripod socket and the ",
           "latch relief - the screw would break into the mechanism"));

// It must sit inside the plate, with a margin to every edge.
assert(socket_y - socket_widest / 2 - 3.0 > plate_y_lo
       && socket_y + socket_widest / 2 + 3.0 < plate_y_hi,
       str("tripod socket at y=", socket_y, " is too close to a top or ",
           "bottom edge (plate spans ", plate_y_lo, " to ", plate_y_hi,
           ")"));

assert(socket_x - socket_widest / 2 - 3.0 > plate_x_lo
       && socket_x + socket_widest / 2 + 3.0 < plate_x_hi,
       str("tripod socket at x=", socket_x, " is too close to a side ",
           "edge (plate spans ", plate_x_lo, " to ", plate_x_hi, ")"));

assert(plate_t - socket_depth >= 1.2,
       str("only ", plate_t - socket_depth,
           "mm of floor under the socket - the screw would break through ",
           "the face the radio sits against"));

// ---- latch ------------------------------------------------------------

assert(tooth_retract > 0.4,
       "detent_bump is too small - the tooth barely overlaps the neck");

assert(tooth_y0 > stud_neck_d / 2 + 0.3,
       str("tooth_y0 fouls the locked neck, whose edge reaches ",
           stud_neck_d / 2, "mm"));

// The tooth does not retract straight out - it swings, and because it
// sits far from the pivot in X, most of that swing is along Y, up the
// slot toward the entry hole.  Its relief follows it, and the ledge
// between that relief and the hole is the thinnest place in the whole
// keyhole.  This is what sets `travel`: shorten the slot and the entry
// hole comes down to meet the swinging tooth.
//
// The corner that gets closest is the relief's INBOARD top one, not the
// tooth's own tip.  It is furthest from the pivot in X, so it swings
// furthest in Y.  Testing the tip instead understated the reach and let
// the relief scallop the entry hole down to a 0.2mm ledge.
tooth_tip_dx = relief_clip_x - pivot_x;
tooth_tip_dy = tooth_y1 - pivot_y;

tooth_tip_x = pivot_x + tooth_tip_dx * cos(sweep_ang)
                      + tooth_tip_dy * sin(sweep_ang);
tooth_tip_y = pivot_y - tooth_tip_dx * sin(sweep_ang)
                      + tooth_tip_dy * cos(sweep_ang);

entry_to_tooth = sqrt(pow(tooth_tip_x, 2) + pow(tooth_tip_y - travel, 2))
                 - entry_d / 2 - lever_clr;

assert(entry_to_tooth >= 1.5,
       str("only ", entry_to_tooth, "mm of ledge between the entry hole ",
           "and the tooth's swept relief.  Lengthen travel, lower ",
           "tooth_y1, or reduce tooth_relief_inset."));

// The clip only produces a straight inboard edge if every rotated copy of
// the relief outline still reaches PAST it.  If the outline ever stops
// short, its inboard boundary becomes an arc that crosses the slot wall
// at a glancing angle and strands a wedge of plastic between the two
// voids - measured at 0.18mm before the outline was widened back out.
//
// Checked at the outline's inboard-top corner, which travels furthest.
relief_in_swept_x = pivot_x + (-neck_w / 2 - pivot_x) * cos(sweep_ang)
                            + (tooth_y1 - pivot_y) * sin(sweep_ang);

assert(relief_in_swept_x <= relief_clip_x - 0.2,
       str("at full press the relief outline only reaches x=",
           relief_in_swept_x, ", short of the clip at ", relief_clip_x,
           " - its inboard edge would become an arc and strand a whisker ",
           "against the neck slot.  Widen the swept outline."));

// PLA is not a living-hinge material; keep the flexure well inside its
// elastic range or it takes a permanent set after a few releases.
assert(flex_strain < 0.012,
       str("flexure strain is ", flex_strain * 100,
           "% - too high for repeated use.  Lengthen flex_len, thin ",
           "flex_t, or move the pivot further from the tooth."));

assert(lever_clr >= 0.8,
       "lever_clr under 0.8mm risks the latch fusing to the body in print");

assert(chan_wall >= 1.2,
       str("wall between the head channel and the latch relief is only ",
           chan_wall, "mm - raise chan_wall to at least 1.2"));

// The flexure needs body to anchor into on its outboard side.  The
// plate's rounded outer edge takes a bite out of that strip, so it counts
// against the wall - measuring to the nominal edge overstated it.
flexure_anchor = plate_x_hi - plate_edge_r - (lever_x1 + flex_len);

assert(flexure_anchor >= 1.2,
       str("only ", flexure_anchor, "mm of plate outboard of the flexure ",
           "once the rounded edge is allowed for - it would break out ",
           "through the side.  Raise plate_x_hi."));

// There has to be real plate below the latch's relief.  Ending the plate
// just short of it leaves a thin crescent stranded between the relief and
// the outside edge: it exports as a second body and prints as a loose
// flake rattling around in the mechanism.  Grazing the rounded corner is
// just as bad in a quieter way - it shaves the fillet into a feather
// edge thinner than the nozzle can lay down.
//
// latch_bottom already accounts for the paddle hanging below the bar and
// for its swing; this only confirms the derived edge honoured it, since
// plate_y_lo may instead have been driven down by the PD plate.
plate_below_relief = latch_bottom - plate_y_lo;

assert(plate_below_relief >= 2.0,
       str("only ", plate_below_relief, "mm of plate below the latch ",
           "relief - a sliver would be stranded there as a separate ",
           "body.  Raise latch_margin."));

// The paddle has to be big enough to press comfortably.  A pad narrower
// than a fingertip concentrates the whole force on its edges.
assert(paddle_w >= 12.0,
       str("paddle is only ", paddle_w, "mm across - too narrow to press ",
           "comfortably with a thumb"));

assert(thread_style == "self_tap" || thread_style == "insert"
       || thread_style == "nut",
       str("unknown thread_style: ", thread_style));

// ---- what has to fit AROUND the bracket --------------------------------
//
// Neither of these is an interference: nothing collides in either case.
// They are about whether the finished thing is usable, which is why the
// geometric checks look straight past them and they need saying here.

// The Peak Design plate bolts to the back face and must be fully
// supported.  Overhang it and the plate rocks on its own edge, which no
// amount of screw torque fixes.
//
// The previous version of this test compared X only.  It never looked at
// Y, so it passed happily while the plate hung 9.5mm off the top of the
// bracket - which is exactly what turned up in the print.  A square has
// four sides and the test now checks all of them.
//
// The back face is a rounded rectangle: the outline inset by plate_edge_r,
// with corners of radius plate_r.  Equivalently it is that rectangle
// shrunk by plate_r and then grown by a disc of plate_r - so a point is
// inside it exactly when it lies within plate_r of the shrunken rectangle.
// Both shapes are convex, so testing the square's four corners tests the
// whole square.
function dist_to_rect(px, py, x0, y0, x1, y1) =
    sqrt(pow(max(x0 - px, px - x1, 0), 2)
       + pow(max(y0 - py, py - y1, 0), 2));

face_x0 = plate_x_lo + plate_edge_r + plate_r;
face_y0 = plate_y_lo + plate_edge_r + plate_r;
face_x1 = plate_x_hi - plate_edge_r - plate_r;
face_y1 = plate_y_hi - plate_edge_r - plate_r;

pd_x0 = socket_x - pd_plate_size / 2;
pd_x1 = socket_x + pd_plate_size / 2;
pd_y0 = socket_y - pd_plate_size / 2;
pd_y1 = socket_y + pd_plate_size / 2;

pd_worst = max(
    dist_to_rect(pd_x0, pd_y0, face_x0, face_y0, face_x1, face_y1),
    dist_to_rect(pd_x1, pd_y0, face_x0, face_y0, face_x1, face_y1),
    dist_to_rect(pd_x0, pd_y1, face_x0, face_y0, face_x1, face_y1),
    dist_to_rect(pd_x1, pd_y1, face_x0, face_y0, face_x1, face_y1)
);

assert(pd_worst <= plate_r,
       str("the ", pd_plate_size, "mm Peak Design plate hangs ",
           pd_worst - plate_r, "mm off the back face at its worst ",
           "corner - it would sit on its own edge and rock."));

// It must also land on SOLID back face.  The latch relief is cut clean
// through the plate, so a plate lapping over it would be bridging open
// slots - supported at the rim and hollow in the middle, which rocks the
// same way an overhang does and lets grit into the mechanism.
pd_above_latch = pd_y0 - relief_y_hi;

assert(pd_above_latch >= 1.0,
       str("the Peak Design plate laps ", -pd_above_latch, "mm over the ",
           "latch relief - it would be sitting on open slots.  Raise ",
           "socket_clear, or lower bar_top."));

// The paddle has to be reachable past the radio hanging in front of it.
paddle_past_radio = paddle_x0 - radio_width / 2;

assert(paddle_past_radio >= 2.0,
       str("the paddle reaches only ", paddle_past_radio, "mm past the ",
           "radio's edge - it would be tucked behind the body and hard ",
           "to find.  Raise tab_protrude, which costs nothing in lever ",
           "geometry since it acts along X and the arm is measured in Y."));


// =====================================================================
//  MODULES
// =====================================================================

// Rounded rectangle from two opposite corners.
module rounded_rect(x0, y0, x1, y1, r) {
    translate([(x0 + x1) / 2, (y0 + y1) / 2])
        offset(r = r) offset(r = -r)
            square([x1 - x0, y1 - y0], center = true);
}

module plate_outline(inset = 0) {
    rounded_rect(plate_x_lo + inset, plate_y_lo + inset,
                 plate_x_hi - inset, plate_y_hi - inset, plate_r);
}

// The plate, with its outer edges broken so it is pleasant to handle and
// does not print with a sharp lip.
module plate_body() {
    hull() {
        linear_extrude(height = 0.01)
            plate_outline(plate_edge_r);
        translate([0, 0, plate_edge_r])
            linear_extrude(height = plate_t - 2 * plate_edge_r)
                plate_outline();
        translate([0, 0, plate_t - 0.01])
            linear_extrude(height = 0.01)
                plate_outline(plate_edge_r);
    }
}

// Neck slot and entry hole, cut up through the ledge from below.
module neck_and_entry() {
    translate([0, 0, -1])
        rotate([0, 0, 90])
            capsule(travel, neck_w, ledge_t + 1);

    translate([0, travel, -1])
        cylinder(d = entry_d, h = ledge_t + 1);
}

// The hidden channel the stud head runs in.
module head_channel_void() {
    translate([0, 0, z_ledge_top])
        rotate([0, 0, 90])
            capsule(travel, head_ch_w, head_ch_h);
}

// 2D outline of the moving latch bar and its arm, excluding tooth and
// paddle.  Full plate depth, so the bar is stiff out of plane and bends
// only sideways.
//
// The arm runs all the way out to where the paddle begins, not merely to
// the plate edge: stopping at the edge leaves the paddle floating in
// space as a second, unconnected body.
module lever_body_2d() {
    translate([lever_x0, bar_bot])
        square([lever_w, bar_top - bar_bot]);

    translate([lever_x0, tab_y0])
        square([paddle_x0 + paddle_t - lever_x0, tab_y1 - tab_y0]);
}

// 2D outline of the tooth, which exists only within the ledge.  The ramp
// is on its UPPER edge: the stud comes DOWN from the entry hole, so that
// is the face it meets first and has to ride over.
//
// The outboard edge runs to lever_x1, INSIDE the bar, rather than stopping
// at lever_x0 where the bar's face is.  Ending it flush leaves the tooth's
// relief and the bar's relief as two voids that almost meet, with a
// 0.2mm knife edge of plastic trapped between them - too thin to print as
// anything but a loose whisker in the mechanism.  Overlapping into the bar
// costs nothing, since that space is already solid bar, and makes the two
// reliefs merge into one clean void.
module lever_tooth_2d() {
    polygon([
        [tooth_x,  tooth_y0],
        [lever_x1, tooth_y0],
        [lever_x1, tooth_y1 + tooth_lead],
        [tooth_x,  tooth_y1],
    ]);
}

// The thumb paddle: a rounded, dished pad on the end of the tab arm.
//
// Built by hulling four cylinders laid along X, which rounds the two long
// edges and both ends in one operation, then hollowing the face with a
// large sphere to leave a shallow dish.
module paddle_solid() {
    // Radius of a sphere that cuts a dish paddle_dish deep across the
    // paddle's width: r = (w^2/4 + d^2) / 2d.
    dish_r = (paddle_w * paddle_w / 4 + paddle_dish * paddle_dish)
             / (2 * paddle_dish);

    difference() {
        hull() {
            for (dz = [paddle_r, plate_t - paddle_r])
                for (dy = [paddle_yc - paddle_w / 2 + paddle_r,
                           paddle_yc + paddle_w / 2 - paddle_r])
                    translate([paddle_x0, dy, dz])
                        rotate([0, 90, 0])
                            cylinder(r = paddle_r, h = paddle_t);
        }

        translate([paddle_x0 + paddle_t + dish_r - paddle_dish,
                   paddle_yc, plate_t / 2])
            sphere(r = dish_r);
    }
}

// Rotate a 2D shape about the pivot, as the lever does.
module about_pivot(a) {
    translate([pivot_x, pivot_y])
        rotate(a)
            translate([-pivot_x, -pivot_y])
                children();
}

// The region the latch sweeps through over its whole stroke.
//
// This is the honest way to size the relief.  Growing the outline by a
// single figure - the largest swing anywhere on the lever - works, but it
// opens that same gap all the way round, including next to the pivot
// where nothing actually moves.  That wastes plate, looks sloppy, and
// lets grit into the mechanism.
//
// Sweeping the real outline through the real rotation instead gives a
// relief that is tight where the lever is still and generous only where
// it travels.  A handful of steps is ample: the stroke is a few degrees,
// so the arc is very nearly straight over it.
sweep_steps = 6;

module lever_swept_2d() {
    for (i = [0 : sweep_steps])
        about_pivot(-sweep_ang * i / sweep_steps)
            children();
}

// Everything hollowed out so the latch can move.
module lever_relief() {
    // Around the bar and the tab arm, full depth.
    translate([0, 0, -1])
        linear_extrude(height = plate_t + 2)
            offset(r = lever_clr)
                lever_swept_2d()
                    lever_body_2d();

    // A wider gap outboard of the bar.  This is the free length the
    // flexure bends over; without it the ligament would be only
    // lever_clr long and far too stiff to move.
    translate([lever_x1, bar_bot - lever_clr - bar_swing, -1])
        cube([flex_len,
              bar_top - bar_bot + 2 * (lever_clr + bar_swing),
              plate_t + 2]);

    // Around the tooth, within the ledge only.  The tooth sweeps furthest
    // of anything that has to pass through a narrow gap, so this is the
    // clearance that actually decides whether the latch can complete its
    // stroke.
    //
    // The outline swept here spans the WHOLE slot, and the result is then
    // clipped back to a straight line just inside the slot's edge.  Doing
    // it in that order matters, and both orders have already been tried:
    //
    //   sweep a narrow outline    the rotated copies drift outboard as
    //                             they turn, so the relief's inboard edge
    //                             is an arc that crosses the slot wall at
    //                             a glancing angle and strands a 0.18mm
    //                             wedge of plastic between the two voids
    //
    //   sweep the wide outline    every rotated copy still reaches past
    //                             the clip line, so clipping leaves a
    //                             straight vertical edge INSIDE the slot.
    //                             Relief and slot overlap at every height
    //                             and merge cleanly
    //
    // The clip is what stops the wide outline swinging on to scallop the
    // entry hole, which is the other half of the same problem.
    translate([0, 0, -1])
        linear_extrude(height = ledge_t + 1)
            intersection() {
                offset(r = lever_clr)
                    lever_swept_2d()
                        polygon([
                            [-neck_w / 2, tooth_y0],
                            [lever_x1,    tooth_y0],
                            [lever_x1,    tooth_y1 + tooth_lead],
                            [-neck_w / 2, tooth_y1],
                        ]);

                translate([relief_clip_x, -100])
                    square([200, 200]);
            }
}

// The latch itself, deflected by `lever_press` degrees about the pivot.
module lever_solid() {
    translate([pivot_ctr[0], pivot_ctr[1], 0])
    rotate([0, 0, -lever_press])
    translate([-pivot_ctr[0], -pivot_ctr[1], 0]) {
        // Bar and tab arm, full depth.
        linear_extrude(height = plate_t)
            lever_body_2d();

        // Tooth, through the ledge only, so it blocks the neck without
        // ever fouling the wider head running in the channel above.
        linear_extrude(height = ledge_t)
            lever_tooth_2d();

        paddle_solid();

        // The flexure, buried a little way into both the bar and the body
        // so the joint is solid rather than a knife edge.
        translate([lever_x1 - flex_root, pivot_y - flex_t / 2, 0])
            cube([flex_len + 2 * flex_root, flex_t, plate_t]);
    }
}

// Pocket that swallows the radio's raised pedestal, if enabled.
module pedestal_pocket_walls() {
    pocket_l = boss_l + travel + 2 * clr_boss;
    pocket_w = boss_w + 2 * clr_boss;

    difference() {
        translate([0, 0, plate_t - 0.01])
            linear_extrude(height = skirt_h)
                plate_outline();
        translate([0, travel / 2 - boss_stud_off_l, plate_t - 0.02])
            linear_extrude(height = skirt_h + 0.02)
                rounded_rect(-pocket_w / 2, -pocket_l / 2,
                              pocket_w / 2,  pocket_l / 2, 1.5);
    }
}

// The tripod socket, cut down into the plate from the back face.
//
// No boss: sitting clear of the keyhole, the socket has the plate's full
// thickness to thread into.
module tripod_socket() {
    translate([socket_x, socket_y, 0]) {
        if (thread_style == "self_tap") {
            translate([0, 0, plate_t - socket_depth])
                cylinder(d = self_tap_d, h = socket_depth + 0.01);

        } else if (thread_style == "insert") {
            translate([0, 0, plate_t - socket_depth - 1.0])
                cylinder(d = self_tap_d, h = socket_depth + 1.01);
            translate([0, 0, plate_t - insert_depth])
                cylinder(d = insert_d, h = insert_depth + 0.01);

        } else {
            translate([0, 0, plate_t - socket_depth - 1.5])
                cylinder(d = thread_major + 0.6, h = socket_depth + 1.51);
            translate([0, 0, plate_t - nut_t])
                cylinder(d = nut_across_corners, h = nut_t + 0.01,
                         $fn = 6);
        }

        // Chamfer at the mouth, so the plate seats flat and the first
        // thread is not a fragile knife edge.
        translate([0, 0, plate_t - 0.8])
            cylinder(d1 = thread_major, d2 = socket_mouth_d, h = 0.81);
    }
}

// Optional keyed recess for the Peak Design plate, centred on the screw.
module plate_recess_cut() {
    translate([socket_x, socket_y, plate_t - plate_recess_d])
        linear_extrude(height = plate_recess_d + 0.01)
            rounded_rect(-plate_recess_size / 2, -plate_recess_size / 2,
                          plate_recess_size / 2,  plate_recess_size / 2, 2);
}


// =====================================================================
//  ASSEMBLY
// =====================================================================

// Everything except the moving latch.
module bracket_body() {
    difference() {
        union() {
            plate_body();
            if (capture_pedestal) pedestal_pocket_walls();
        }

        if (plate_recess) plate_recess_cut();
        neck_and_entry();
        head_channel_void();
        lever_relief();
        tripod_socket();
    }
}

// The latch, trimmed clear of the stud head.  Built separately from the
// body so a check can measure whether the two overlap: at rest they share
// only the flexure, and pressing must not make them share more, or the
// latch would be grinding against the plate instead of moving.
//
// Note what is NOT cut away here.  The neck slot is deliberately left
// alone: the tooth's whole purpose is to intrude into that slot, so
// subtracting it erases the tooth completely and quietly turns the latch
// into decoration.  Only the head channel is cleared, so the wider head
// still runs freely above.
module bracket_lever() {
    difference() {
        lever_solid();
        head_channel_void();
    }
}

module bracket() {
    union() {
        bracket_body();
        bracket_lever();
    }
}

// There is deliberately no test coupon.
//
// A coupon is worth having when a small piece can prove the fiddly part
// of a design cheaply.  That does not apply here: the mechanism runs from
// the entry hole at the top to the paddle at the bottom, which is
// essentially the whole plate.  Every trim that saved a worthwhile amount
// of material either cut through the mechanism or sliced a corner fillet
// at a shallow angle, leaving a feather edge under 0.9mm - and the trims
// that kept the walls sound removed only 5%.
//
// The full bracket is 18 cm^3 and prints in well under an hour, so the
// honest answer is to print the real thing and check the fit on that.
// A "coupon" that is 95% of the part is a coupon in name only.

// The stud, for the fit checks.  Locked position is the origin; it
// approaches from below, since material runs upward here.
module bracket_stud(pos = 0, extra = 0, lift = 0) {
    translate([0, pos, -lift])
        mirror([0, 0, 1])
            stud_solid(0, extra, 0);
}


// =====================================================================
//  ENTRY POINT
// =====================================================================

// What to draw.  A file that includes this one can override it by
// assigning variant_render_mode AFTER the include; OpenSCAD resolves each
// variable to its last assignment in the scope, so the later value wins.
//
// Declared as a plain default rather than tested with is_undef(), which
// does not reliably see assignments made later in the scope - that quirk
// silently made every fit check render the whole bracket instead of the
// pose it asked for.
variant_render_mode = "assembly";

render_mode = variant_render_mode;

if (render_mode == "assembly") {
    bracket();

} else if (render_mode == "body") {
    bracket_body();

} else if (render_mode == "lever") {
    bracket_lever();

} else if (render_mode == "section") {
    difference() {
        bracket();
        translate([0, -200, -200]) cube([400, 400, 400]);
    }

} else if (render_mode == "none") {
    // Library only - the including file draws its own geometry.

} else {
    assert(false, str("unknown render_mode: ", render_mode));
}
