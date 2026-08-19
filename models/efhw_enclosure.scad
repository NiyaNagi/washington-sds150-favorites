// =====================================================================
//  EFHW antenna enclosure - screw-top jar, drip-proof
// =====================================================================
//
//  A two-part cylindrical enclosure for an end-fed half-wave antenna
//  matching transformer.  Clear interior 120mm across and 70mm tall.
//
//  The outside is ONE UNBROKEN CYLINDER, 128mm across, from the bottom of
//  the base to the top of the lid.  Nothing stands proud of it but the
//  four carabiner ears.  Closed, the only evidence of a joint is a fine
//  parting line where the lid's skirt meets the body's shoulder.
//
//
//  THE LID WRAPS A STEPPED-IN NECK, like a jam jar.
//
//  This is the whole reason the part is as short as it is, and it took
//  two attempts to get right.  The obvious arrangement - a plug lid that
//  screws DOWN into the body - stacks its grip band on top of everything
//  else, so the band is pure height:
//
//      plug lid                    wrap-over lid
//      +------------+ 105          +------------+  89
//      | grip   10  |  <- dead     | skirt  10  |  <- grip AND thread
//      +------------+  95          +------------+  86     in the same
//      | thread 16  |              | neck   10  |          ten millimetres
//      | spigot  3  |              |            |
//      | interior70 |              | interior70 |
//      | floor   6  |              | floor   6  |
//      +------------+              +------------+
//
//  Sixteen millimetres, for nothing but rearranging the same features.
//
//  It also puts the joint in a better place.  On a plug lid the parting
//  line sits at the top, where rain lands on it.  Here the line is at the
//  BOTTOM of the skirt, facing down: water running off the lid crosses it
//  travelling downward and keeps going.  To get inside it would have to
//  climb ten millimetres up a helix, against gravity.
//
//
//  WHAT IT COSTS
//
//  The neck has to step inward to make room for the skirt, so the MOUTH
//  is narrower than the interior:
//
//      interior   120mm   (the full bore, for 70mm of height)
//      mouth      113mm   (what will actually pass through the opening)
//
//  Everything between the outside skin and the mouth is accounted for -
//  skirt wall, thread, neck wall - and it comes to 15mm of diameter.
//  There is no arrangement that avoids it; a wider mouth needs a wider
//  can.  See the assert on `item_d`.
//
//
//  COORDINATE SYSTEM
//
//  Z is up, and z = 0 is the bottom face - the one it stands on, and the
//  one that goes down on the build plate.  The axis is X = Y = 0.
//  The body prints as modelled.  The lid is modelled in place, screwed
//  onto the neck, and flipped for printing by its own render mode.
//
//
//  DRIP-PROOF, NOT WATERPROOF, and deliberately so.  The cable slots are
//  open and there are weep holes in the floor.  A sealed outdoor
//  enclosure still fills with water - air gets in warm and damp and
//  condenses when the sun goes off it - the water just cannot get back
//  out.  This one sheds rain and drains what forms inside, at any angle.
//
//  THERE IS NO GASKET, so the geometry does the work: the joint faces
//  down, there is a drip chamfer either side of it, an inner lip runs
//  down inside the neck as a labyrinth, and the thread itself is several
//  turns of tortuous path.
//
// =====================================================================

include <thread_lib.scad>

$fa = 2;
$fs = 0.4;


// ---------------------------------------------------------------------
//  1. WHAT IT HAS TO HOLD
// ---------------------------------------------------------------------

interior_d       = 120.0;  // clear diameter, mm
interior_h       =  70.0;  // clear height, mm

// The widest thing that has to pass through the OPENING, which is not
// the same as the widest thing that fits once it is inside.  Measured
// across the diagonal of the transformer.
//
// This is a checked requirement, not documentation - see the assert.  It
// is the number that decides whether the whole wrap-over arrangement is
// possible at this diameter at all, and the first estimate of it (114mm,
// which included some buffer) ruled it out entirely.
item_d           = 107.0;  // mm

// The floor is crowned so water runs to the edge at any hanging angle,
// which means the interior height is measured from the APEX of the floor
// in the centre.  Otherwise the middle of the box is shorter than
// advertised - which is exactly what happened to the first version.


// ---------------------------------------------------------------------
//  2. THREAD
// ---------------------------------------------------------------------
//
// Sized by scripts/cad/design_thread.py and proven as a pair by
// scripts/cad/check_thread_fit.py.
//
// Two starts is what makes it pleasant to use.  Strength comes from the
// number of crests in mesh; the number of TURNS to undo it comes from the
// lead.  With cold wet hands on a hillside, those are different things.

thread_pitch      =  4.00;  // mm
thread_starts     =  2;     // -> 8mm lead
thread_crest_flat =  1.00;  // mm, 2.4 extrusions - NOT a knife edge
thread_root_flat  =  1.00;  // mm
thread_flank_ang  = 60.0;   // degrees from the perpendicular to the axis

// Flank angle is measured from the perpendicular, so 60 degrees leans
// only 30 degrees off vertical when printed - well inside what prints
// unsupported.  Counter-intuitively STEEPER flanks are safer here, and
// they buy more depth per pitch.  A 45-degree trapezoidal form would
// overhang 45 degrees, right on the limit.
//
// The pitch is coarse on purpose, and NOT to make the thread strong -
// it is absurdly strong either way.  Two crests strip at about 31kN and
// the transformer weighs four newtons.  What the coarse pitch buys is
// depth: 1.73mm of engagement instead of 0.87mm at a 3mm pitch.  A
// 128mm PLA circle can warp half a millimetre off round, and half a
// millimetre is 29% of a deep thread but 57% of a shallow one.  Warp
// tolerance is the governing case, not load.

thread_clr        =  0.35;  // per face, mm
thread_lead_in    =  1.20;  // crest chamfer on the neck, mm


// ---------------------------------------------------------------------
//  3. STRUCTURE
// ---------------------------------------------------------------------

wall_t           =  4.00;  // main cylinder wall, mm -> 128 outside
floor_t          =  5.00;  // mm at the perimeter
floor_crown      =  1.00;  // how much higher the centre sits, mm

// The lid's skirt: the grip band, the thread, and the whole reason the
// enclosure is 89mm tall rather than 105.
//
// Its height is DERIVED from the thread engagement below, not chosen.
// Choosing it first left 2.07 crests in mesh - the lead-in chamfer and
// the headroom eat into the skirt, so the engagement is always less than
// the skirt is deep, and picking the skirt meant discovering the
// engagement afterwards rather than specifying it.
thread_crests    =  3;     // crests in mesh - what actually holds
skirt_w          =  3.00;  // mm thick - see the knurl assert
lid_disc_t       =  3.00;  // the flat top, mm

neck_wall        =  2.40;  // mm, between the thread root and the mouth
neck_headroom    =  0.50;  // gap above the neck, mm

// Without the headroom the neck's top rim and the lid's inner ceiling
// meet on a coincident face, and it becomes ambiguous which of the two
// stops the lid.  The stop is the shoulder, and only the shoulder.

edge_r           =  1.00;  // rounding on outside edges, mm
drip_ch          =  0.60;  // chamfer either side of the parting line, mm


// ---------------------------------------------------------------------
//  4. LABYRINTH LIP
// ---------------------------------------------------------------------
//
// An annular rib on the underside of the lid that runs down inside the
// neck's bore.  With no gasket this is the last line: a narrow gap, long
// in the direction water would have to travel, and pointing the wrong way
// for gravity.
//
// Length is set BY the ratio, not chosen and then justified by it.  An
// earlier version picked 5mm, worked out that the ratio came to 16.7, and
// then wrote an assert demanding 10 - which confirms a number already
// chosen rather than constraining anything, and cost 2mm of height for
// nothing.

lip_ratio        = 10.0;   // length : clearance
lip_clr          =  0.30;  // per face, mm
lip_wall         =  2.00;  // thickness of the rib itself, mm


// ---------------------------------------------------------------------
//  5. CARABINER EARS
// ---------------------------------------------------------------------
//
// Four ears blended into the base slab, rather than a flange under the
// whole part.  A flange makes the base the widest thing on the object and
// gives it a dinner-plate silhouette; ears keep the cylinder reading as a
// cylinder and put material only where the load is.
//
// They are part of the base slab, not fittings attached to it - the same
// 5mm of solid material simply reaches outward in four places, with a
// generous radius where it leaves the wall so there is no notch to start
// a crack from.

ear_hole_d       =  8.00;  // mm
ear_wall         =  3.00;  // material around the hole, mm
ear_blend_r      = 10.00;  // fillet where the ear meets the wall, mm
ear_count        =  4;


// ---------------------------------------------------------------------
//  6. CABLE EXITS AND DRAINAGE
// ---------------------------------------------------------------------
//
// Two slots, opposite each other: coax and counterpoise out of one, the
// antenna wire out of the other.
//
// OPEN AT THE TOP, so the cable is LAID IN from above rather than
// threaded through end-first.  That is the entire point of them.  A
// PL-259's coupling ring is about 20mm across, and no slot a 128mm can
// could carry would pass it - so the connector stays on the cable and
// never goes through anything at all.
//
// The slot runs DOWN into the wall far enough that the cable ends up
// below the shoulder, and the lid then screws down over the top of it
// without ever touching it.  That clearance is not a nicety: the lid
// turns one and a half times to close, so a cable pinched at the joint
// would be wound round the neck and chafed through.
//
// The walls taper - wider at the mouth, closing to just under the cable
// diameter at the bottom - so it starts easily by hand and then grips.

cable_d          =  5.00;  // RG-58 outside diameter, mm
cable_grip       =  0.20;  // slot narrower than the cable at the bottom
cable_mouth_flare =  0.60;  // and wider than it at the top, to start it
cable_lid_clr    =  2.00;  // air between the cable and the lid's landing
cable_slot_count =  2;     // opposite each other

// Four weep holes, evenly spaced, because this hangs at whatever angle
// the feedpoint pulls it to - with a single drain there is always an
// orientation that puts it at the top.  Four means one is always low.
weep_d           =  3.00;  // mm
weep_count       =  4;
weep_tilt        = 30.0;   // degrees from vertical


// ---------------------------------------------------------------------
//  7. LID FACE
// ---------------------------------------------------------------------

// Axial scallops around the skirt.  Every face is vertical, so it prints
// with no overhang anywhere, and it grips with wet gloves - which a
// diamond knurl, printed at this size, does not.
knurl_count      = 40;
knurl_d          =  4.00;  // scallop diameter, mm
knurl_depth      =  1.00;  // how far it bites into the skirt, mm

text_line1       = "KM7HKM";
text_line2       = "WA7DAM";
text_size        = 18.0;   // mm cap height
text_depth       =  1.00;  // mm cut into the 3mm disc, leaving 2mm
text_gap         =  3.0;   // between the two lines, mm

// Liberation Sans ships with OpenSCAD, so this renders identically
// anywhere.  A font taken from the system list would render differently,
// or not at all, on another machine.
text_font        = "Liberation Sans:style=Bold";

// Cut only 1mm deep, the letters have to be FAT to read.  A shallow
// recess with thin strokes looks like a scratch, and the walls between
// strokes get too thin to print cleanly.  This grows every glyph outward.
// check_text.py confirms the counters - the enclosed holes in A and D -
// survive it.
text_fatten      =  0.35;  // mm added to every stroke edge


// =====================================================================
//  DERIVED - computed, not edited
// =====================================================================

// ---- radial stack, from the OUTSIDE inward --------------------------
//
// This one is derived outside-in, which is the opposite of the first
// version and is the honest direction here: the outside diameter is
// fixed, and what is left over after the skirt, the thread and the neck
// wall have taken their share IS the mouth.  Deriving it the other way
// would make the outside grow silently whenever anything inboard of it
// changed.
interior_r   = interior_d / 2;                 // 60.0
body_or      = interior_r + wall_t;            // 64.0

thread_depth_v = thread_depth(thread_pitch, thread_crest_flat,
                              thread_root_flat, thread_flank_ang);

skirt_ir     = body_or - skirt_w;              // 61.0, female thread root
thread_r0    = skirt_ir - thread_depth_v - thread_clr;
neck_or      = thread_r0 + thread_depth_v;     // male crest
neck_ir      = thread_r0 - neck_wall;          // THE MOUTH

// The neck's core, which the thread is swept onto.
//
// Sunk slightly BELOW the thread's root, so the ribbon's buried tail
// lands inside solid material rather than exactly on its surface.
//
// thread_lib sweeps its profile from -overlap to the crest for precisely
// this reason, and a core drawn at thread_r0 puts the core's surface
// exactly on the profile's dr = 0 line: two solids meeting on a
// coincident cylinder, which is the one thing this project has learned
// never to do.  CGAL agreed, and refused the union outright -
// "assertion violation", no output at all.  The shell rendered fine on
// its own; it was only the union that failed.
neck_core_r  = thread_r0 - 0.4;

// The mouth is NARROWER than the bore - that is the price of the lid
// wrapping over - so something has to get from one to the other.
//
// It cannot be a flat ledge.  That would be a 3.5mm horizontal annulus
// hanging unsupported over the bore, and it would droop into the box.
// A 45 degree cone is self-supporting, and it doubles as a funnel that
// guides the transformer in past the step.
//
// It also has to exist at all: without it the neck's outer face (58.5)
// simply hangs over the bore (60.0) touching nothing, and the body
// exports as two separate solids.  A 2mm overlap did not help, because
// there was no material there to overlap with.
cone_h       = interior_r - neck_ir;
//
// A screw thread INTERLEAVES: the female's crest runs in the male's root
// groove, and the female's root clears the male's crest.  So this sits
// BELOW the neck's crest, not above it, and the two are meant to overlap
// in radius.  That is what makes it a thread rather than two tubes.
//
// female_thread_void produces a bore of r0 + clr, so this matches it by
// construction rather than by a second number that has to agree.
skirt_bore_r = thread_r0 + thread_clr;

mouth_d      = 2 * neck_ir;

// The annulus the lid's skirt lands on, which is what stops it.
shoulder_w   = body_or - neck_or;

// The labyrinth lip, hanging inside the neck.
lip_h        = lip_ratio * lip_clr;
lip_or       = neck_ir - lip_clr;
lip_ir       = lip_or - lip_wall;

// ---- axial stack, upward from the build plate ------------------------
//
// The floor sits ON the bottom face and the interior starts above it.
// Version one measured the floor from the plate while a solid base slab
// occupied the same space, and the whole floor - gutter, crown and all -
// vanished into the union: it came out dead flat, the box held water, and
// all four weep holes were blind pockets.
z_floor_top  = floor_t;                        // gutter, where water goes
z_floor_apex = z_floor_top + floor_crown;      // interior starts here

// The full 120mm bore ends here; the cone up to the mouth starts.
z_bore_top   = z_floor_apex + interior_h;
z_shoulder   = z_bore_top + cone_h;            // neck starts here

// The skirt is as tall as the thread needs, plus the lead-in that gets it
// started and the headroom above the neck's rim.
thread_engage = thread_crests * thread_pitch;
neck_h       = thread_engage + thread_lead_in;
skirt_h      = neck_h + neck_headroom;

z_neck_top   = z_shoulder + neck_h;

// The lid, modelled in place.
z_lid_inner  = z_shoulder + skirt_h;           // its inner ceiling
z_lid_top    = z_lid_inner + lid_disc_t;

overall_h    = z_lid_top;
body_h       = z_neck_top;

// Carabiner ears.
ear_hole_r   = body_or + ear_wall + ear_hole_d / 2;
ear_or       = ear_hole_r + ear_hole_d / 2 + ear_wall;

// The cable slots, derived from the cable rather than chosen.
//
// The slot is open at the top and its depth is set by what has to fit
// under the lid: the cable itself, plus air above it.  Pick the depth
// first and the clearance becomes whatever is left over, which is how a
// cable ends up pinched by a lid nobody meant to pinch it with.
cable_slot_w  = cable_d - cable_grip;          // at the bottom, grips
cable_mouth_w = cable_d + cable_mouth_flare;   // at the top, starts easily
cable_slot_d  = cable_d + cable_lid_clr;       // below the shoulder

z_cable_bot   = z_shoulder - cable_slot_d;
z_cable_ctr   = z_cable_bot + cable_slot_w / 2;
z_cable_top   = z_cable_ctr + cable_d / 2;

// How far inboard the slot is cut.  Past the neck bore rather than just
// past the can's bore, because the slot has to clear the NECK as well as
// the wall - see z_cable_slot_top below.
cable_reach_r = neck_ir - 1.0;

// And how far up.  This is the part that is easy to get wrong.
//
// A slot that stops at the shoulder is not open in any useful sense: the
// neck stands directly above it, so there is nothing to lower the cable
// THROUGH.  You would be back to threading it in from the end, which is
// impossible once a PL-259 is fitted - the plug is four times the width
// of the slot and it is not coming off.
//
// So the slot runs the full height of the neck and out of the top of it,
// leaving a clear vertical channel from open air down to the seat.  The
// cost is that it interrupts the thread over about five degrees of arc
// at two places, roughly three per cent of it.  Interrupted threads are
// ordinary - most moulded caps have them - and there is a great deal of
// margin here to spend.
z_cable_slot_top = z_neck_top + 1.0;

// Weep holes, from the gutter down and out through the bottom face.
weep_entry_r = interior_r - weep_d / 2 - 1.0;
weep_exit_r  = weep_entry_r + floor_t * tan(weep_tilt);

// Where the flat top of the lid ends.  The knurl is on the skirt, below
// this, so the whole face is available - but the text is still checked
// against it rather than eyeballed.
lid_flat_r   = body_or - edge_r - 1.0;


// =====================================================================
//  ASSERTS
// =====================================================================

assert(interior_h > 0 && interior_r > 0,
       "the interior has to have a size");

// THE governing constraint for this whole arrangement.
//
// The lid's skirt has to go somewhere, and stepping the neck in to make
// room for it narrows the opening.  If the contents will not pass through
// what is left, the wrap-over design is simply not available at this
// diameter and the enclosure has to get wider.
assert(mouth_d >= item_d + 4.0,
       str("the mouth is ", mouth_d, "mm and the contents are ", item_d,
           "mm - that is ", mouth_d - item_d, "mm of clearance, and it ",
           "needs about 4 to go in by hand.  Either widen the can or use ",
           "a lid that plugs in rather than wraps over."));

// The mouth must not somehow exceed the interior it opens into.
assert(mouth_d <= interior_d,
       "the mouth cannot be wider than the bore behind it");

// The skirt is cut into from the outside by the knurl and from the inside
// by the thread.  What is left between the two is the only thing holding
// the lid together.
assert(skirt_w - knurl_depth >= 1.8,
       str("the knurl cuts ", knurl_depth, "mm into a ", skirt_w,
           "mm skirt, leaving ", skirt_w - knurl_depth,
           "mm - it would break through into the thread groove"));

// The neck carries the whole load through its own wall.
assert(neck_wall >= 2.0,
       str("the neck wall is only ", neck_wall, "mm"));

// The shoulder is the hard stop.  Too narrow and it is an edge, not a
// landing, and the lid's travel stops being repeatable.
assert(shoulder_w - drip_ch >= 2.0,
       str("the lid lands on only ", shoulder_w - drip_ch, "mm of ",
           "shoulder once the drip chamfer is allowed for"));

// The skirt's groove must clear the neck's crest, and its own crest must
// clear the neck's root.  A thread is two interleaved helices, so both
// have to be true at once - checking only one of them is how the first
// attempt ended up either fouling by 1693mm^3 or, after an over-eager
// correction, missing entirely with a 0.36mm gap and no thread at all.
assert(abs(skirt_ir - (neck_or + thread_clr)) < 1e-9,
       str("the lid's thread groove reaches ", skirt_ir, " but the neck's ",
           "crest plus clearance is ", neck_or + thread_clr));

assert(skirt_bore_r > thread_r0 && skirt_bore_r < neck_or,
       str("the lid's bore is ", skirt_bore_r, ", which must sit between ",
           "the neck's root ", thread_r0, " and its crest ", neck_or, " - ",
           "a thread interleaves, and a bore outside the crest would ",
           "clear the neck completely and grip nothing"));

// The lid is cut 1mm deep into a 3mm disc.
assert(lid_disc_t - text_depth >= 1.5,
       str("only ", lid_disc_t - text_depth, "mm of lid left under the ",
           "lettering - it would show through, or split"));

// The lip has to be a long narrow gap to work as a labyrinth.  A short
// one is just a chamfer, and with no gasket here it is the primary
// defence.
//
// lip_h is derived FROM this ratio, so the test is a tautology and exists
// only to catch a bad edit to the derivation.  Compared with a tolerance
// for that reason: 0.3 has no exact binary representation, so the
// quotient lands a hair either side of 10 depending on the arithmetic
// order.  An exact >= here would be a coin toss - which is precisely how
// the nut socket failed an assert against its own design value earlier in
// this project.
assert(lip_h / lip_clr >= lip_ratio - 1e-6,
       str("the lip is ", lip_h, "mm long with ", lip_clr, "mm of ",
           "clearance.  There is no gasket here, so this ratio IS the ",
           "seal."));

assert(lip_h + neck_headroom <= neck_h,
       "the labyrinth lip is longer than the neck it hangs inside");

// Thread sanity, mirroring design_thread.py so a bad edit fails at render
// time rather than at print time.
assert(thread_crest_flat >= 0.8,
       str("thread crest is only ", thread_crest_flat, "mm - this is the ",
           "knife edge that made the 1/4\"-20 thread print mushy"));

assert(90 - thread_flank_ang <= 45,
       str("thread flanks overhang ", 90 - thread_flank_ang, " degrees ",
           "from vertical - they will droop.  RAISE thread_flank_ang; ",
           "steeper is safer."));

assert(thread_engage / thread_pitch >= 3,
       str("only ", thread_engage / thread_pitch, " thread crests engage"));

// The grip band has to be tall enough to actually grip.  It is derived
// from the thread now, so this is where a too-fine thread would show up
// as a lid nobody can open.
assert(skirt_h >= 8.0,
       str("the grip band is only ", skirt_h, "mm tall - raise ",
           "thread_crests or the pitch"));

// The whole reason the slot is as deep as it is: the lid has to screw
// down over the cable without touching it.  The lid turns one and a half
// times to close, so a cable it caught would be wound round the neck.
assert(z_shoulder - z_cable_top >= 1.5,
       str("only ", z_shoulder - z_cable_top, "mm between the top of a ",
           cable_d, "mm cable and the face the lid lands on - the lid ",
           "would drag on it as it turns.  Raise cable_lid_clr."));

// And it must not run so deep that it opens into the floor's gutter,
// which would turn a cable exit into a drain.
assert(z_cable_bot > z_floor_apex + 2.0,
       str("the cable slot reaches down to z ", z_cable_bot,
           ", too close to the floor at ", z_floor_apex));

// It grips only if it is narrower than the cable at the bottom and wider
// at the mouth.  Stated because the two are easy to transpose, and a slot
// that flares the wrong way spits the cable back out.
assert(cable_slot_w < cable_d && cable_mouth_w > cable_d,
       str("the cable slot must be narrower than the cable at its bottom ",
           "and wider at its mouth, or it will not hold anything"));

// The slot must pass right through the neck wall, not stop inside it.
// Stopping short leaves a web a few tenths thick bridging the channel -
// invisible in a render, one perimeter wide on the printer, and directly
// across the path the cable has to take.
assert(cable_reach_r < neck_ir && z_cable_slot_top > z_neck_top,
       str("the cable slot stops inside the neck (reaches r ",
           cable_reach_r, " of ", neck_ir, ", up to z ",
           z_cable_slot_top, " of ", z_neck_top,
           ") - it would be bridged rather than open"));

// Ears, cable slots and weep holes all live around the same circle on
// separate bearings.  Measured as real arc rather than as bare angles,
// because two features of different widths can be far apart in degrees
// and still overlap.
ear_half   = 360 * (ear_hole_d / 2 + ear_wall + 2) / (2 * PI * body_or);
slot_half  = 360 * (cable_slot_w / 2) / (2 * PI * body_or);
weep_half  = 360 * (weep_d / 2) / (2 * PI * weep_entry_r);

assert(45 - ear_half - slot_half > 5,
       str("the carabiner ears and the cable slots are only ",
           45 - ear_half - slot_half, " degrees apart"));

assert(22.5 - weep_half - ear_half > 3,
       str("the weep holes and the carabiner ears are only ",
           22.5 - weep_half - ear_half, " degrees apart"));

assert(22.5 - weep_half - slot_half > 3,
       str("the weep holes and the cable slots are only ",
           22.5 - weep_half - slot_half, " degrees apart - they would ",
           "merge into one opening at the weakest point of the wall"));

// The weep holes must reach daylight.  A hole that stops inside the floor
// is a blind pocket that collects the very water it was cut to release,
// and all four were exactly that in the first version.
assert(weep_exit_r < body_or - 1.0,
       str("the weep holes would surface at r ", weep_exit_r,
           ", past the wall at ", body_or));


echo(str("EFHW ENCLOSURE v3  OD ", 2 * body_or,
         " CONSTANT  assembled h ", overall_h,
         "  body h ", body_h, "  across ears ", 2 * ear_or));
echo(str("  ROOM    interior ", interior_d, " x ", interior_h,
         "   MOUTH ", mouth_d, " (", mouth_d - item_d,
         "mm clear on a ", item_d, "mm item)"));
echo(str("  THREAD  external on the neck, root ", 2 * thread_r0,
         " crest ", 2 * neck_or, "  pitch ", thread_pitch, " x ",
         thread_starts, " starts  engage ", thread_engage, " = ",
         thread_engage / thread_pitch, " crests, ",
         thread_engage / (thread_pitch * thread_starts), " turns"));
echo(str("  SEAL    no gasket: lip ", lip_h, "mm at ", lip_clr,
         "mm clearance, ratio ", lip_h / lip_clr,
         "  shoulder stop ", shoulder_w, "mm wide"));
echo(str("  LID     skirt ", skirt_h, " tall x ", skirt_w,
         " thick, disc ", lid_disc_t, ", ", knurl_count,
         " scallops, text ", text_size, "mm"));
echo(str("  CABLE   ", cable_slot_count, " slots open at the top for ",
         cable_d, "mm cable: mouth ", cable_mouth_w, " closing to ",
         cable_slot_w, ", seat at z ", z_cable_ctr, ", channel up to ",
         z_cable_slot_top, " through the neck, cable sits ",
         z_shoulder - z_cable_top, "mm clear of the lid"));


// =====================================================================
//  MODULES
// =====================================================================

// Things arranged evenly around the axis.
module around(n, start = 0) {
    for (i = [0 : n - 1])
        rotate([0, 0, start + i * 360 / n])
            children();
}


// ---- carabiner ears --------------------------------------------------

// One ear, in plan: a teardrop faired into the wall.
//
// The fairing is a morphological CLOSING - grow the outline by the blend
// radius, then shrink it back by the same amount.  Growing fills every
// concave corner; shrinking restores the convex ones it did not touch.
// What is left is the original shape with a fillet of exactly
// ear_blend_r in every internal corner, and nothing else changed.
//
// Worth doing it this way rather than subtracting a circle from each
// side.  Placing those circles means computing where the web meets a
// curved wall, and the first attempt put them 0.8mm clear of the
// material - so they removed nothing at all, and the ears printed as flat
// plates stuck on the side.  A closing cannot miss: it has no position to
// get wrong.
//
// The body's own circle has to be present while the fillet is formed, so
// there is something for it to blend INTO - and then removed again,
// leaving 1mm of overlap so the ear merges into the wall rather than
// meeting it on a coincident face.  The fillet itself survives that
// removal: it sits in the concave corner OUTSIDE the circle, tangent to
// both surfaces, so subtracting the disc does not touch it.
module ear_2d() {
    difference() {
        offset(r = -ear_blend_r)
            offset(r = ear_blend_r)
                union() {
                    circle(r = body_or);

                    hull() {
                        translate([ear_hole_r, 0])
                            circle(r = ear_hole_d / 2 + ear_wall);
                        translate([body_or - 10, 0])
                            circle(r = ear_hole_d / 2 + ear_wall + 4);
                    }
                }

        circle(r = body_or - 1);
    }
}


// ---- body ------------------------------------------------------------

// The cable slot, seen side-on in the plane of the wall.
//
// Swept radially by body_cuts().  Two parts, because they do two jobs:
//
//   the seat    a round-bottomed pocket that narrows onto the cable, so
//               it is held while the lid is being fitted
//
//   the channel a parallel slot above it, running up past the neck, so
//               the cable has a straight path down into the seat
//
// The taper is kept short on purpose.  Hulling the seat straight to the
// top of the neck would also produce a funnel, but spread over twenty
// millimetres instead of two, and a taper that shallow is a wedge: it
// would grip the cable most of the way down and fight being pushed the
// last little bit.
module cable_slot_2d() {
    hull() {
        translate([0, z_cable_ctr])
            circle(d = cable_slot_w, $fn = 32);

        translate([-cable_mouth_w / 2, z_cable_top - 0.01])
            square([cable_mouth_w, 0.02]);
    }

    translate([-cable_mouth_w / 2, z_cable_top])
        square([cable_mouth_w, z_cable_slot_top - z_cable_top]);
}

// The outside skin, the floor, and the neck - one revolve.
//
// The profile runs up the outside, across the shoulder, up the neck, and
// back down the inside to the crowned floor.  Building it as one closed
// outline rather than as a stack of cylinders is what guarantees the
// result is a single solid: the lid of the previous version was
// assembled from parts that did not quite touch, and exported as two
// separate watertight objects with a 7mm gap between them.
// The threaded neck, as its own solid.
//
// Built and unioned with its thread SEPARATELY from the rest of the body,
// then joined to it.  That is not tidiness, it is the only arrangement
// CGAL would accept.
//
// Unioning a helix with the full body profile fails outright - "CGAL
// error in applyUnion3D: assertion violation", no output at all - and
// bisecting the profile shows exactly where it turns:
//
//     neck tube + thread                        renders
//     + shoulder step + thread                  renders
//     + neck rim chamfer + thread               renders
//     + drip chamfer + thread                   renders
//     + the wall running down to the floor      FAILS
//
// Nothing about the thread changes across those cases, and matching the
// revolve's facet count to the sweep's ($fn = 180, 360) does not help,
// nor does moving the thread up or down, nor deepening the overlap -
// which made it worse.  It is the complexity of the other operand.
//
// So the neck is unioned with its thread while it is still a plain tube,
// which is the case that provably works, and the resulting solid is then
// unioned with the body.  Every boolean stays simple.
module neck() {
    union() {
        // Started below the shoulder so it buries itself in the cone's
        // material rather than sitting on a face.  Two solids that meet
        // on a shared face are two solids.
        rotate_extrude(convexity = 4)
            polygon([
                [neck_ir,           z_shoulder - 1.5],
                [neck_core_r,       z_shoulder - 1.5],
                [neck_core_r,       z_neck_top - 0.6],
                [neck_core_r - 0.6, z_neck_top],
                [neck_ir,           z_neck_top],
            ]);

        translate([0, 0, z_shoulder])
            male_thread(r0 = thread_r0,
                        pitch = thread_pitch,
                        length = thread_engage,
                        starts = thread_starts,
                        crest_flat = thread_crest_flat,
                        root_flat = thread_root_flat,
                        flank_ang = thread_flank_ang,
                        lead_in = thread_lead_in,
                        seg = 180);
    }
}


// The can: everything except the neck.
module body_can() {
    rotate_extrude(convexity = 8)
        polygon([
            [0,                    0],
            [body_or - edge_r,     0],
            [body_or,              edge_r],

            // Up the outside to the parting line.  The chamfer here meets
            // the one on the lid and forms a shallow V groove all the way
            // round: water beads in it and falls, instead of creeping
            // along the seam by capillary action.
            [body_or,              z_shoulder - drip_ch],
            [body_or - drip_ch,    z_shoulder],

            // The shoulder - the face the lid's skirt lands on - then in
            // to the mouth, and down the 45 degree cone to the full bore.
            [neck_ir,              z_shoulder],
            [interior_r,           z_bore_top],
            [interior_r,           z_floor_top],

            // The crowned floor: highest in the middle, so water runs
            // outward to the gutter at the wall however it is tilted.
            [0,                    z_floor_apex],
        ]);
}


module body_shell() {
    union() {
        body_can();
        neck();
    }

    // Ears, as part of the base slab: same height, same material, with
    // their top and bottom edges stepped back so neither is a sharp
    // corner and the first layer has somewhere to spread.
    //
    // Stacked slices rather than hull().  hull() is CONVEX, and the ear
    // outline is not - hulling it against its own inset copy bridges
    // straight across the waist of the teardrop and turns four ears into
    // one square slab.  That is exactly what it did, and it is the second
    // time in this project a convex hull has quietly filled in a shape it
    // was only meant to round: it erased a scalloped flange too.
    around(ear_count, start = 45) {
        linear_extrude(height = edge_r)
            offset(r = -edge_r) ear_2d();

        translate([0, 0, edge_r - 0.01])
            linear_extrude(height = floor_t - 2 * edge_r + 0.02)
                ear_2d();

        translate([0, 0, floor_t - edge_r])
            linear_extrude(height = edge_r)
                offset(r = -edge_r) ear_2d();
    }
}


// Everything hollowed out of the body.
module body_cuts() {
    // Carabiner holes, chamfered both ends so a gate slides in without
    // catching and there is no sharp edge to chew webbing.
    around(ear_count, start = 45)
        translate([ear_hole_r, 0, -0.01]) {
            cylinder(d = ear_hole_d, h = floor_t + 0.02);
            cylinder(d1 = ear_hole_d + 1.4, d2 = ear_hole_d, h = 0.71);
            translate([0, 0, floor_t - 0.7])
                cylinder(d1 = ear_hole_d, d2 = ear_hole_d + 1.4, h = 0.71);
        }

    // Cable slots, opposite each other, OPEN AT THE TOP.
    //
    // Drawn in the plane of the wall and swept radially inward, far
    // enough to pass clean through the neck rather than leaving a sliver
    // of it standing in the cable's way.
    around(cable_slot_count, start = -90)
        rotate([90, 0, 0])
            translate([0, 0, -(body_or + 2)])
                linear_extrude(height = body_or + 2 - cable_reach_r)
                    cable_slot_2d();

    // Weep holes, angled down and outward from the gutter, out through
    // the bottom face.
    //
    // Out through the BOTTOM rather than the side, so water leaves from
    // the lowest surface and drips clear.  Tilted 30 degrees from
    // vertical: enough to clear the wall, shallow enough that the hole's
    // own roof is a 30-degree overhang and needs no support.
    around(weep_count, start = 22.5)
        translate([weep_entry_r, 0, z_floor_top + 0.3])
            rotate([0, 180 - weep_tilt, 0])
                cylinder(d = weep_d, h = floor_t * 2.5);
}


module body() {
    difference() {
        body_shell();
        body_cuts();
    }
}


// ---- lid -------------------------------------------------------------

// The knurl: vertical scallops cut into the skirt only.
module lid_knurl_cut() {
    around(knurl_count)
        translate([body_or - knurl_depth + knurl_d / 2, 0, z_shoulder - 1])
            cylinder(d = knurl_d, h = skirt_h + 2);
}


// The callsigns, as a 2D shape.
module lid_text_2d() {
    offset(r = text_fatten) {
        translate([0, (text_size + text_gap) / 2])
            text(text_line1, size = text_size, font = text_font,
                 halign = "center", valign = "center");
        translate([0, -(text_size + text_gap) / 2])
            text(text_line2, size = text_size, font = text_font,
                 halign = "center", valign = "center");
    }
}


// The lid, before the thread, the knurl and the lettering.
//
// ONE closed profile, revolved: the top disc, the skirt hanging from its
// rim, and the labyrinth lip hanging inside that.  All three are the same
// wall of material folded round a hollow, so the lid is a single solid by
// construction rather than by hoping the pieces touch.
module lid_body() {
    rotate_extrude(convexity = 10)
        polygon([
            // Across the top face, out to the rim.
            [0,                   z_lid_top],
            [body_or - edge_r,    z_lid_top],
            [body_or,             z_lid_top - edge_r],

            // Down the outside to the parting line, where the chamfer
            // meets the body's.
            [body_or,             z_shoulder + drip_ch],
            [body_or - drip_ch,   z_shoulder],

            // The skirt's bottom face - what lands on the shoulder.
            [skirt_bore_r,        z_shoulder],

            // Up the inside of the skirt.  This surface clears the neck's
            // thread CREST; the groove is cut outward from it.
            [skirt_bore_r,        z_lid_inner],

            // In across the ceiling to the labyrinth lip, down its
            // outside, across its foot and back up its inside.
            [lip_or,              z_lid_inner],
            [lip_or,              z_lid_inner - lip_h],
            [lip_ir,              z_lid_inner - lip_h],
            [lip_ir,              z_lid_inner],

            // And in to the axis, closing under the disc.
            [0,                   z_lid_inner],
        ]);
}


module lid() {
    difference() {
        lid_body();

        // The thread, cut into the skirt.
        translate([0, 0, z_shoulder])
            female_thread_void(r0 = thread_r0,
                               pitch = thread_pitch,
                               length = skirt_h + 1,
                               starts = thread_starts,
                               clr = thread_clr,
                               crest_flat = thread_crest_flat,
                               root_flat = thread_root_flat,
                               flank_ang = thread_flank_ang,
                               seg = 180);

        lid_knurl_cut();

        translate([0, 0, z_lid_top - text_depth])
            linear_extrude(height = text_depth + 0.01)
                lid_text_2d();
    }
}


// ---- test coupon -----------------------------------------------------

// A short section of the real thread at the real diameter, so the fit can
// be proven in about twenty minutes instead of a five-hour print.
//
// The diameter is what matters and it is unchanged.  A coupon shrunk to
// some convenient smaller size would prove nothing: the errors that bite
// scale with circumference.
coupon_h = neck_h + 6;

module coupon_body() {
    difference() {
        union() {
            cylinder(r = body_or, h = 4);
            translate([0, 0, 4])
                cylinder(r = thread_r0, h = neck_h);
            translate([0, 0, 4])
                male_thread(r0 = thread_r0,
                            pitch = thread_pitch,
                            length = thread_engage,
                            starts = thread_starts,
                            crest_flat = thread_crest_flat,
                            root_flat = thread_root_flat,
                            flank_ang = thread_flank_ang,
                            lead_in = thread_lead_in,
                            seg = 180);
        }
        translate([0, 0, -0.01])
            cylinder(r = neck_ir, h = neck_h + 5);
    }
}


module coupon_lid() {
    difference() {
        cylinder(r = body_or, h = skirt_h);
        translate([0, 0, -0.01])
            cylinder(r = skirt_bore_r, h = skirt_h + 0.02);
        translate([0, 0, -0.5])
            female_thread_void(r0 = thread_r0,
                               pitch = thread_pitch,
                               length = skirt_h + 1,
                               starts = thread_starts,
                               clr = thread_clr,
                               crest_flat = thread_crest_flat,
                               root_flat = thread_root_flat,
                               flank_ang = thread_flank_ang,
                               seg = 180);
        around(knurl_count)
            translate([body_or - knurl_depth + knurl_d / 2, 0, -1])
                cylinder(d = knurl_d, h = skirt_h + 2);
    }
}


// =====================================================================
//  ENTRY POINT
// =====================================================================

variant_render_mode = is_undef(variant_render_mode)
    ? "assembly" : variant_render_mode;

// The lid prints face DOWN, lettering against the build plate.
//
// That puts the thread flanks the right way up to be self-supporting, and
// gives the text a glass-smooth face straight off the build sheet - which
// reads far better at 1mm deep than a top surface would.
module lid_print_oriented() {
    translate([0, 0, z_lid_top])
        rotate([180, 0, 0])
            lid();
}

if (variant_render_mode == "body") {
    body();

} else if (variant_render_mode == "lid") {
    lid_print_oriented();

} else if (variant_render_mode == "lid_placed") {
    // As modelled, screwed onto the neck - for the checks that reason
    // about the assembly rather than about the print.
    lid();

} else if (variant_render_mode == "coupon_body") {
    coupon_body();

} else if (variant_render_mode == "coupon_lid") {
    coupon_lid();

} else if (variant_render_mode == "assembly") {
    body();
    lid();

} else if (variant_render_mode == "section") {
    // Cut in half, to see the thread in mesh and the labyrinth lip.
    difference() {
        union() { body(); lid(); }
        translate([-200, 0, -50]) cube([400, 400, 400]);
    }

} else if (variant_render_mode == "none") {
    // Library only - the including file draws its own geometry.

} else {
    assert(false, str("unknown variant_render_mode: ",
                      variant_render_mode));
}
