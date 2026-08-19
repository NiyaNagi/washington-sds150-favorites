// =====================================================================
//  Printable helical threads
// =====================================================================
//
//  A general-purpose thread generator for 3D printing.  Nothing in here
//  knows about any particular part; it takes a pitch, a diameter and a
//  length and produces a male thread, or the void that cuts the matching
//  female one.
//
//  WHY THIS EXISTS AT ALL
//
//  This project removed a modelled-helix thread once already.  The note
//  in sds150_pd_bracket.scad is blunt about it: a 1/4"-20 form is 0.69mm
//  deep, its crests come to a knife edge measuring 0.004mm, it printed
//  mushy, and it produced 246 degenerate faces and an open mesh.
//
//  That verdict was right, and it was right about THAT SCALE.  A large
//  enclosure thread is a different object:
//
//                      1/4"-20 (removed)      a 4mm-pitch enclosure
//      pitch              1.27 mm                   4.0 mm
//      depth              0.69 mm                   1.73 mm
//      crest              0.004 mm                  1.0 mm
//
//  A 1mm crest is two and a half extrusions wide at a 0.4mm nozzle.  It
//  is a real printed surface, not an artefact.  So the geometry is sound
//  here where it was not there - but the tessellation still has to be
//  MEASURED rather than assumed, because that is the half of the old
//  failure that had nothing to do with size.  inspect_stl.py counts
//  degenerate faces, and that count is the canary.
//
//
//  HOW THE THREAD IS BUILT
//
//  As one polyhedron, swept directly along the helix.
//
//  The obvious alternative - union together a few hundred little wedges,
//  one per angular step - is far slower and asks CGAL to do several
//  hundred boolean operations on coincident faces, which is where mesh
//  degeneracy tends to come from in the first place.  Sweeping a closed
//  profile and emitting the vertices and faces directly gives an exact
//  manifold with no booleans at all.
//
//
//  THE PROFILE, AND WHY IT TILES
//
//  The axial cross-section is a trapezoid spanning exactly one pitch, so
//  consecutive turns stack against each other with no seam:
//
//        dr
//         ^
//         |        C........D          <- crest flat
//         |       /          \
//         |      /            \
//         |  ---B              E---    <- root flat
//         |     |              |
//       0 +-----A--------------+-----> dz
//         |     :              :
//         |  G--+--------------+--F    <- overlap into the core
//              0             pitch
//
//  G and F sit at negative dr, INSIDE the core cylinder.  That overlap is
//  deliberate: two solids that merely touch on a coincident face leave
//  whiskers of plastic a tenth of a millimetre thick, which this project
//  has measured more than once.  Overlap, never abut.
//
//
//  MULTIPLE STARTS
//
//  A multi-start thread is the same ribbon swept more than once, evenly
//  spaced around the circumference.  Each ribbon still carries a
//  one-pitch profile, but advances `lead` per revolution rather than
//  `pitch`, and the other starts fill the space in between.
//
//  This matters for a lid you open with cold hands: engagement depth is
//  set by the number of crests, but the number of TURNS to undo it is set
//  by the lead.  Two starts halve the turns for the same grip.
//
// =====================================================================


// ---------------------------------------------------------------------
//  PROFILE
// ---------------------------------------------------------------------

// Depth of a thread, from the parameters that describe its shape.
//
// Everything follows from the pitch once the flats and the flank angle
// are chosen: what is left of the pitch after the two flats is spent on
// the two flanks, and how much depth that buys depends on their angle.
function thread_depth(pitch, crest_flat, root_flat, flank_ang) =
    (pitch - crest_flat - root_flat) / 2 * tan(flank_ang);

// The closed profile, in (dr, dz) relative to the minor radius.
//
// Wound counter-clockwise.  The winding is not decorative - it decides
// which way the swept faces end up pointing, and a polyhedron with
// inside-out faces is not a solid at all.
//
// Three things here exist purely to keep the boolean clean, and all three
// were added in response to a measured failure:
//
//   overlap     buries the inner edge inside the core cylinder
//   z_overlap   stretches that buried tail past both ends of the pitch,
//               so neighbouring ribbons interpenetrate rather than meet
//               face to face.  Without it, on a two-start thread the top
//               edge of one ribbon lands exactly on the bottom edge of
//               the next: "Simple: no", 8 volumes, 72 broken faces.
//   root_sink   drops the root line BELOW the core surface, so the
//               flanks cross it at an angle instead of running along it.
//
// The last one is the subtle one.  A thread's root is, by definition,
// flush with its minor diameter - so a profile whose root sits at dr = 0
// lies exactly ON the core cylinder, and the two surfaces meet tangentially
// along a helical curve.  The solid there pinches to zero thickness, which
// is not a manifold edge, and the triangulation tears along it.  A
// single-start thread got away with it; two starts did not.
//
// Sinking the root fixes it without changing the finished shape at all,
// because the visible root is then formed by the CYLINDER rather than by
// the ribbon.  The flanks are simply extended back to meet the lower line,
// so the root flat measured at the core surface is still exactly
// `root_flat` - see the assert below.
function thread_profile(pitch, crest_flat, root_flat, flank_ang,
                        overlap = 0.6, z_overlap = 0.4, root_sink = 0.4) =
    let (
        depth   = thread_depth(pitch, crest_flat, root_flat, flank_ang),
        run     = (pitch - crest_flat - root_flat) / 2,

        // How far along the axis the flank travels while dropping the
        // extra `root_sink` below the core surface.
        dz_sink = root_sink / tan(flank_ang)
    )
    assert(root_flat - 2 * dz_sink > 0.05,
           str("root_sink of ", root_sink, "mm eats the whole ", root_flat,
               "mm root flat - the two flanks would cross below the core ",
               "surface and the profile would fold over itself"))
    [
        [-overlap,   -z_overlap],                     // G
        [-root_sink, dz_sink],                        // A, root line
        [-root_sink, root_flat - dz_sink],            // B, root line
        [depth,      root_flat + run],                // C, crest
        [depth,      root_flat + run + crest_flat],   // D, crest
        [-root_sink, pitch + dz_sink],                // E, next root line
        [-overlap,   pitch + z_overlap],              // F
    ];


// ---------------------------------------------------------------------
//  2D POLYGON OFFSET
// ---------------------------------------------------------------------

// Grow a simple closed polygon outward by `c`, mitring the corners.
//
// Used to derive the female thread from the male one, so the two are
// conjugate by construction rather than by two lists of numbers that have
// to be kept in step by hand.
//
// OpenSCAD's built-in offset() would do this, but it returns geometry
// rather than points, and the sweep needs points.
function _unit2(v) = v / max(sqrt(v[0] * v[0] + v[1] * v[1]), 1e-9);

function poly_offset(pts, c) =
    let (n = len(pts))
    [ for (i = [0 : n - 1])
        let (
            p  = pts[i],
            pm = pts[(i - 1 + n) % n],
            pn = pts[(i + 1) % n],

            // For a counter-clockwise polygon the interior lies to the
            // LEFT of each edge, so the outward normal is to the right.
            e1 = _unit2(p - pm),
            e2 = _unit2(pn - p),
            n1 = [ e1[1], -e1[0] ],
            n2 = [ e2[1], -e2[0] ],

            // The mitre runs along the bisector, and has to be longer
            // than c by however much the corner is folded.  Clamped, so a
            // near-reflex corner produces a blunt end rather than a spike
            // shooting off to infinity.
            b    = _unit2(n1 + n2),
            fold = max(b * n1, 0.25)
        )
        p + b * (c / fold)
    ];


// ---------------------------------------------------------------------
//  THE SWEEP
// ---------------------------------------------------------------------

// One helical ribbon, as a single polyhedron.
//
// The sweep is specified by the ANGLE RANGE it covers, not by a turn
// count, because each start of a multi-start thread has to cover the same
// axial extent and they all begin at different angles.
//
//   profile   closed (dr, dz) point list, counter-clockwise
//   r0        radius that dr = 0 refers to
//   lead      axial advance per full revolution
//   a0, a1    angular range to sweep, degrees
//   z_off     axial offset of this ribbon
//   seg       angular steps per revolution
//
// Height follows the angle directly: z = lead * a / 360 + z_off.  Tying
// the two together in one expression is what keeps a ribbon on its helix.
// An earlier version advanced height from the STEP INDEX instead, and
// then shifted each start with a translate.  Both starts came out on
// exactly the same helix, perfectly superimposed - CGAL still called the
// union "simple", because a solid unioned with a copy of itself is a
// perfectly good solid, and the fault only surfaced as 116 broken faces
// in the exported triangulation.
module thread_ribbon(profile, r0, lead, a0, a1, z_off = 0, seg = 120) {
    n     = len(profile);
    steps = max(2, ceil(abs(a1 - a0) / 360 * seg));
    dang  = (a1 - a0) / steps;

    verts = [
        for (i = [0 : steps])
            let (a = a0 + i * dang)
            for (p = profile)
                [ (r0 + p[0]) * cos(a),
                  (r0 + p[0]) * sin(a),
                  lead * a / 360 + z_off + p[1] ]
    ];

    // Side walls: two TRIANGLES per profile edge per step.
    //
    // Triangles, not quads, and this matters.  A quad spanning one
    // angular step of a helix is twisted - its four corners do not lie in
    // a plane - and OpenSCAD says so: "PolySet has nonplanar faces.
    // Attempting alternate construction".  It tolerates that while the
    // thread is buried inside a larger cylinder, because the boolean
    // never has to intersect those faces.  The moment the thread stands
    // proud of its core and CGAL has to compute a real intersection
    // curve, it fails outright:
    //
    //     CGAL ERROR: assertion violation!
    //     Current top level object is empty.
    //
    // Three points always lie in a plane, so triangulating removes the
    // problem at the source.  The cost is twice as many faces, which is
    // nothing.
    //
    // Written as an explicit third loop rather than with `each`, because
    // `let` followed by `each` inside nested comprehensions does not bind
    // the way it reads and produced a mesh that would not close.
    sides = [
        for (i = [0 : steps - 1])
            for (j = [0 : n - 1])
                for (t = [0, 1])
                    let (k = (j + 1) % n)
                        t == 0
                            ? [ i * n + j, i * n + k, (i + 1) * n + k ]
                            : [ i * n + j, (i + 1) * n + k, (i + 1) * n + j ]
    ];

    // End caps, left as single polygons.
    //
    // OpenSCAD triangulates a polygon face itself, and it does a better
    // job than a naive fan from vertex 0: this profile is not star-shaped
    // about that corner, so a fan produces overlapping triangles and the
    // result is not a closed mesh at all - "The given mesh is not closed!
    // Unable to convert to CGAL_Nef_Polyhedron."
    //
    // The caps are also very nearly flat, being one profile at one angle,
    // so they do not suffer the twist that makes the SIDE faces a problem.
    //
    // Reversed at the start so both caps point away from the solid.
    cap_lo = [ for (j = [n - 1 : -1 : 0]) j ];
    cap_hi = [ for (j = [0 : n - 1]) steps * n + j ];

    polyhedron(points = verts,
               faces  = concat(sides, [cap_lo], [cap_hi]),
               convexity = 10);
}


// All starts of a thread, each covering the axial range z_lo .. z_hi.
//
// Start s is the same helix raised by s pitches.  Working back from the
// height it has to reach gives the angles it must be swept between:
//
//     z = lead * a / 360 + s * pitch      ->     a = 360 (z - s*pitch) / lead
//
// Deriving the angles from the heights, rather than sweeping a fixed
// number of turns and hoping it reaches, is what guarantees every start
// spans the whole thread instead of petering out part way up.
module thread_starts(profile, r0, lead, starts, z_lo, z_hi, seg = 120) {
    pitch = lead / starts;
    for (s = [0 : starts - 1])
        let (z_off = s * pitch)
            thread_ribbon(profile, r0, lead,
                          360 * (z_lo - z_off) / lead,
                          360 * (z_hi - z_off) / lead,
                          z_off, seg);
}


// ---------------------------------------------------------------------
//  MALE AND FEMALE
// ---------------------------------------------------------------------

// A male thread, on the outside of a cylinder of radius `r0`.
//
// `length` is the finished axial length.  The sweep deliberately runs
// past both ends and is then trimmed square, because a helix cut mid-turn
// otherwise leaves a feathered tail thinner than the nozzle can print.
//
// `lead_in` chamfers the ends of the CRESTS only, so the thread starts
// easily and cannot cross-thread on a sharp corner.  It is applied by
// intersecting with a double-ended cone, which leaves the root untouched.
module male_thread(r0, pitch, length, starts = 1,
                   crest_flat = 1.0, root_flat = 1.0, flank_ang = 60,
                   lead_in = 1.2, seg = 120, overlap = 0.6) {

    lead    = pitch * starts;
    depth   = thread_depth(pitch, crest_flat, root_flat, flank_ang);
    profile = thread_profile(pitch, crest_flat, root_flat, flank_ang,
                             overlap);

    intersection() {
        // Swept past both ends, then trimmed square.  A helix cut off
        // mid-turn otherwise tapers away to a feather thinner than the
        // nozzle can print.
        thread_starts(profile, r0, lead, starts,
                      -pitch, length + pitch, seg);

        // Square trim, with the crest chamfers built into the envelope.
        //
        // $fn matched to the sweep's own angular resolution.  Left at the
        // default this facets far more coarsely than the thread, and
        // intersecting two differently-faceted round surfaces shaves
        // slivers off every mismatched edge.
        rotate_extrude(convexity = 4, $fn = seg)
            polygon([
                [r0 - overlap - 0.1, 0],
                [r0 + depth,         lead_in],
                [r0 + depth,         length - lead_in],
                [r0 - overlap - 0.1, length],
            ]);
    }
}


// The void that cuts a female thread.
//
// This is the male thread grown by `clr` in every direction, so the pair
// is conjugate by construction.  Subtract it from a tube whose bore is
// r0 + clr.
//
// Deriving one from the other is the whole point.  A female thread
// written out as its own set of numbers is a second copy of the same
// intent, and this project's entire bug history is second copies drifting
// out of step with the first.
//
// It is still verified as two separate solids afterwards - see
// check_thread_fit.py.  The bracket's latch and its relief were also
// generated from one outline, and that is exactly why an error in the
// clearance appeared in both and cancelled itself out of every check.
//
// NOTE THE SQUARE TRIM.  The male thread's envelope tapers at the ends to
// chamfer its crests; doing the same to this one would be exactly wrong.
// Shrinking a VOID adds material, so a tapered envelope here builds the
// female thread PROUD at its mouth, where it then jams against the male
// crest.  It measured 72mm^3 of interference half a turn in.  The lead-in
// for the pair comes from the male chamfer alone.
module female_thread_void(r0, pitch, length, starts = 1, clr = 0.35,
                          crest_flat = 1.0, root_flat = 1.0,
                          flank_ang = 60, seg = 120,
                          overlap = 0.6) {

    lead    = pitch * starts;
    depth   = thread_depth(pitch, crest_flat, root_flat, flank_ang);
    profile = poly_offset(
        thread_profile(pitch, crest_flat, root_flat, flank_ang, overlap),
        clr);

    intersection() {
        thread_starts(profile, r0, lead, starts,
                      -pitch, length + pitch, seg);

        // Square, and run past both ends so the cut breaks cleanly out of
        // the part rather than stopping flush with its face.
        rotate_extrude(convexity = 4, $fn = seg)
            polygon([
                [r0 - overlap - clr - 0.1, -0.5],
                [r0 + depth + clr,         -0.5],
                [r0 + depth + clr,         length + 0.5],
                [r0 - overlap - clr - 0.1, length + 0.5],
            ]);
    }
}


// ---------------------------------------------------------------------
//  SELF TEST
// ---------------------------------------------------------------------
//
// A small threaded pair, for checking the library on its own before any
// real part depends on it.  Rendered only when this file is opened
// directly - including it from elsewhere draws nothing.

thread_lib_demo = is_undef(thread_lib_demo) ? "none" : thread_lib_demo;

module _demo_plug(r0 = 15, pitch = 4, len = 12, starts = 2, clr = 0.35) {
    union() {
        cylinder(r = r0, h = len + 4);
        male_thread(r0, pitch, len, starts, seg = 96);
    }
}

module _demo_socket(r0 = 15, pitch = 4, len = 12, starts = 2, clr = 0.35) {
    depth = thread_depth(pitch, 1.0, 1.0, 60);
    difference() {
        cylinder(r = r0 + depth + clr + 3, h = len + 4);
        translate([0, 0, -0.01])
            cylinder(r = r0 + clr, h = len + 4.02);
        female_thread_void(r0, pitch, len, starts, clr, seg = 96);
    }
}

if (thread_lib_demo == "plug") {
    _demo_plug();

} else if (thread_lib_demo == "socket") {
    _demo_socket();

} else if (thread_lib_demo == "pair") {
    _demo_plug();
    translate([0, 0, 30]) _demo_socket();

} else if (thread_lib_demo == "none") {
    // Library only.

} else {
    assert(false, str("unknown thread_lib_demo: ", thread_lib_demo));
}
