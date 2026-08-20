"""Check that fattening the callsigns has not closed up their counters.

The lettering is cut only 1mm deep into a 3mm lid, so every glyph is
thickened by offset(r = text_fatten) before it is used - a shallow recess
with thin strokes reads as a scratch, and the walls left between the
strokes come out under a nozzle width.

Thickening a glyph shrinks its COUNTERS, though: the enclosed holes in A
and D lose text_fatten from every side while the strokes gain it.  Push it
far enough and the A becomes a solid triangle and the D a solid slab.  It
is the worst kind of fault - the part still slices, still prints, still
looks like lettering in a thumbnail, and is only obviously wrong when the
finished lid is in your hand.  The same offset can quietly weld two
neighbouring letters together, which shows up the same way.

So this renders the 2D text twice, once as drawn and once with
text_fatten forced to zero, and insists the two have the same number of
outlines and the same number of holes.  It also renders a single letter
twice more, plain and fattened past what its counter can absorb, and
insists that the closure is noticed - a check that has never been seen to
fail has not been shown to work.  It then measures the narrowest stroke
that survived and how much fattening the tightest counter could still
take, and confirms on the lid itself that the recess is the depth it
should be with sound material left under it.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_text.py
"""

from __future__ import annotations

import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import shapely
import shapely.geometry
import trimesh
from shapely.ops import polylabel

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models"
TMP = ROOT / ".tmp-cad"

OPENSCAD_CANDIDATES = [
    Path(r"C:\Program Files\OpenSCAD\openscad.exe"),
    Path("/usr/bin/openscad"),
    Path("/usr/local/bin/openscad"),
]

# The narrowest stroke worth cutting 1mm deep.  Three millimetres is about
# seven extrusions at a 0.4mm nozzle, and it is also roughly where a
# recess stops reading as a letter and starts reading as a scratch - the
# eye needs a band of shadow, not a line.
MIN_STROKE = 3.0           # mm

# Material that must remain under the deepest part of the cut.  Below this
# the lettering telegraphs through as a ghost on the inside face, and the
# lid becomes a disc scored along the letters.
MIN_UNDER = 1.5            # mm

# How far inside the flat top the text has to stay.  The knurl is cut from
# the rim inward, and a letter that reaches into it loses a leg.
TEXT_MARGIN = 2.0          # mm

# The recess is a straight extrusion, so the measured depth should match
# the nominal to within tessellation noise.  Anything larger means
# something else is cutting the top face.
DEPTH_TOL = 0.05           # mm

# Erosion steps for the stroke-width search.  Half a hundredth of a
# millimetre is finer than any decision made from the answer.
WIDTH_RES = 0.005          # mm

# Height the text test coupon is extruded to, and where it is sectioned.
# Only ever used as a way of getting OpenSCAD's 2D result back into
# Python; nothing about the number matters except that it is not zero.
COUPON_H = 0.5             # mm

# The injected fault: one glyph, on its own, fattened until its counter
# must have closed.
#
# On its own because the first version of this control fattened the whole
# callsign, and at 1.6mm the letters welded to each other before any
# counter shut - the gaps BETWEEN the letters became enclosed holes, the
# total went from 3 counters up to 5, and the control read as "cannot see
# a closed counter" while the counters were in fact closing.  A single
# glyph has nothing to weld to.
#
# An A because its counter is the smallest on the lid, so a check that
# can see this one close can see any of them.
#
# 3mm because that counter measures 2.06mm from its centre to its nearest
# edge at this cap height, and offset() eats that distance directly.  2mm
# was tried first and left a 0.06mm sliver of hole - still a counter as
# far as the topology is concerned, so the control failed and said the
# check was blind when it was merely being asked a question too gently.
CONTROL_GLYPH = "A"
CONTROL_FATTEN = 3.0       # mm

# Smallest counter worth having, as a radius.  A hole that survives by a
# few hundredths survives in CAD and closes up on the plate: the counter
# is an island standing proud in the bottom of the recess, and an island
# two extrusions across is a blob.
MIN_COUNTER = 1.0          # mm


def find_openscad() -> Path:
    for path in OPENSCAD_CANDIDATES:
        if path.exists():
            return path
    raise SystemExit("OpenSCAD not found - install it or edit OPENSCAD_CANDIDATES")


def echoed_values(openscad: Path) -> dict[str, float]:
    """Read the model's own derived numbers.

    Numbers only.  The two callsigns are strings, and a string echoed into
    this line would be split apart by the whitespace parser the moment
    anyone put a space in a callsign; they are read from the source
    instead.
    """
    scad = MODELS / ".text_probe.scad"
    scad.write_text(
        "include <efhw_enclosure.scad>\n"
        'variant_render_mode = "none";\n'
        'echo(str("TEXTPROBE",'
        '" text_size=", text_size,'
        '" text_depth=", text_depth,'
        '" text_fatten=", text_fatten,'
        '" text_gap=", text_gap,'
        '" lid_disc_t=", lid_disc_t,'
        '" body_or=", body_or,'
        '" knurl_depth=", knurl_depth,'
        '" interior_r=", interior_r,'
        '" z_lid_inner=", z_lid_inner,'
        '" z_lid_top=", z_lid_top));\n',
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [str(openscad), "-o", str(TMP / "text_probe.stl"), str(scad)],
            capture_output=True, text=True,
        )
    finally:
        scad.unlink(missing_ok=True)

    text = (result.stderr or "") + (result.stdout or "")
    line = next((l for l in text.splitlines() if "TEXTPROBE" in l), None)
    if line is None:
        sys.stderr.write(text[-2000:])
        raise SystemExit("could not read the model's derived values")

    vals: dict[str, float] = {}
    for token in line.replace('"', "").split():
        if "=" in token:
            key, _, value = token.partition("=")
            try:
                vals[key] = float(value)
            except ValueError:
                pass
    return vals


def callsigns() -> tuple[str, str]:
    """The two lines, read out of the source.

    Only ever used to say how many glyphs were expected and to name them
    in the output.  Nothing is measured from it, so reading the source
    rather than the render costs nothing.
    """
    src = (MODELS / "efhw_enclosure.scad").read_text(encoding="utf-8")
    found = []
    for name in ("text_line1", "text_line2"):
        match = re.search(rf'^{name}\s*=\s*"([^"]*)"', src, re.MULTILINE)
        if match is None:
            raise SystemExit(f"could not find {name} in efhw_enclosure.scad")
        found.append(match.group(1))
    return found[0], found[1]


def render(openscad: Path, name: str, tail: str, out: Path) -> trimesh.Trimesh:
    """Render one temporary variant.

    The caller supplies everything after the include, render mode
    included.  Writing a mode here and letting the caller override it
    would work - the last assignment in an OpenSCAD scope wins - but it
    leaves two assignments to the same name in the file, and a reader
    checking why a render came out wrong has to know that rule to see
    which one took.

    Re-rendered only when the model is newer than the mesh.  The text
    coupons are quick, but the lid takes minutes and is shared with
    check_seal.py.  Staleness is judged against every source the model is
    built from, because a mesh older than the model it came from reads
    exactly like a model that passes.
    """
    sources = [MODELS / "efhw_enclosure.scad", MODELS / "thread_lib.scad"]
    newest = max(s.stat().st_mtime for s in sources)

    if not (out.exists() and out.stat().st_mtime > newest):
        scad = MODELS / f".text_{name}.scad"
        scad.write_text(
            "include <efhw_enclosure.scad>\n"
            f"{tail}\n",
            encoding="utf-8",
        )
        print(f"  rendering {name} ...", flush=True)
        try:
            result = subprocess.run(
                [str(openscad), "-o", str(out), str(scad)],
                capture_output=True, text=True,
            )
        finally:
            scad.unlink(missing_ok=True)

        if not out.exists() or out.stat().st_size < 200:
            sys.stderr.write((result.stderr or "")[-2000:])
            raise SystemExit(f"OpenSCAD produced nothing for {name}")

    return trimesh.load(out)


def text_outlines(mesh: trimesh.Trimesh, z: float) -> list:
    """The glyph outlines, as shapely polygons in the model's own XY.

    Taken as a section through the extruded coupon rather than from the
    triangles directly, so a hole in a glyph comes back as a hole in a
    polygon instead of as extra triangles that have to be interpreted.

    The section is brought into 2D with an explicit translation.  Letting
    trimesh choose its own frame would have been fine for counting, but
    the same polygons are used to aim a probe at the real lid, and a
    silently rotated frame would put that probe on the wrong letter.
    """
    section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if section is None:
        raise SystemExit(f"nothing to section at z={z} - the text is empty")

    flat, _ = section.to_2D(
        to_2D=trimesh.transformations.translation_matrix([0, 0, -z]))
    return list(flat.polygons_full)


def counters(polys: list) -> int:
    return sum(len(p.interiors) for p in polys)


def tightest_counter(polys: list) -> float:
    """Radius of the largest circle that fits in the smallest counter.

    This is the quantity the whole script is about.  offset(r) takes r off
    a counter from every side at once, so this number IS the fattening the
    lettering has left before a hole shuts - stated as a distance rather
    than as a count of holes that happen still to be there.
    """
    best = float("inf")
    for poly in polys:
        for ring in poly.interiors:
            hole = shapely.geometry.Polygon(ring)
            centre = polylabel(hole, tolerance=0.01)
            best = min(best, float(centre.distance(hole.exterior)))
    return best


def pinch_width(polys: list) -> float:
    """The narrowest stroke anywhere in the text, in mm.

    Found by eroding the whole shape with a disc and looking for the width
    at which the count of separate pieces first changes.  Erosion by w/2
    removes everything within w/2 of an edge, so a stroke of width w
    breaks in two the moment the disc passes it - and a piece thinner than
    that everywhere simply vanishes, which is the same signal.

    Deliberately not a scan of chord lengths across the shape.  A scan
    line crossing a diagonal reads it wider than it is, and a scan line
    near the apex of an A reads a couple of tenths and calls the whole
    letter unprintable.  Erosion does not care which way a stroke runs and
    rounds a sharp corner back rather than reporting it as a fault.
    """
    shape = shapely.union_all(polys)
    base = shapely.get_num_geometries(shape)

    def broken(width: float) -> bool:
        eroded = shape.buffer(-width / 2)
        return eroded.is_empty or shapely.get_num_geometries(eroded) != base

    # Bracket first rather than assuming a ceiling.  The answer is wanted
    # as a number even when it is comfortably over the limit, because a
    # stroke width that is drifting downward is worth seeing before it
    # arrives.
    lo, hi = 0.0, 0.5
    while hi < 64.0 and not broken(hi):
        lo, hi = hi, hi * 2
    if not broken(hi):
        return float("inf")

    while hi - lo > WIDTH_RES:
        mid = (lo + hi) / 2
        if broken(mid):
            hi = mid
        else:
            lo = mid
    return hi


def deepest_point(poly) -> tuple[float, float]:
    """A point as far from any edge of the glyph as it can be.

    Used to aim the depth probe.  A centroid would do for most letters and
    fall clean outside a C or a 7.
    """
    point = polylabel(poly, tolerance=0.05)
    return float(point.x), float(point.y)


def surface_z(mesh: trimesh.Trimesh, x: float, y: float,
              z_above: float, downward: bool = True) -> float:
    """Height of the first solid on a ray, or NaN if the ray misses."""
    origin = np.array([[x, y, z_above]])
    direction = np.array([[0.0, 0.0, -1.0 if downward else 1.0]])
    locs, _, _ = mesh.ray.intersects_location(
        ray_origins=origin, ray_directions=direction, multiple_hits=True)
    if len(locs) == 0:
        return float("nan")
    return float(locs[:, 2].max() if downward else locs[:, 2].min())


def main() -> int:
    openscad = find_openscad()
    TMP.mkdir(exist_ok=True)

    v = echoed_values(openscad)
    line1, line2 = callsigns()
    glyphs = len(line1.replace(" ", "")) + len(line2.replace(" ", ""))

    print("=== EFHW lid lettering ===")
    print(f"  \"{line1}\" over \"{line2}\" - {glyphs} glyphs at "
          f"{v['text_size']:.1f}mm cap height")
    print(f"  cut {v['text_depth']:.2f}mm into a {v['lid_disc_t']:.2f}mm lid, "
          f"every stroke fattened by {v['text_fatten']:.2f}mm")
    print()

    fat = render(openscad, "fat",
                 'variant_render_mode = "none";\n'
                 f"linear_extrude({COUPON_H}) lid_text_2d();",
                 TMP / "efhw_text_fat.stl")
    plain = render(openscad, "plain",
                   'variant_render_mode = "none";\n'
                   "text_fatten = 0;\n"
                   f"linear_extrude({COUPON_H}) lid_text_2d();",
                   TMP / "efhw_text_plain.stl")
    control = render(openscad, "control",
                     'variant_render_mode = "none";\n'
                     f"linear_extrude({COUPON_H}) offset(r = "
                     f'{CONTROL_FATTEN}) text("{CONTROL_GLYPH}", '
                     "size = text_size, font = text_font, "
                     'halign = "center", valign = "center");',
                     TMP / "efhw_text_control.stl")
    control_open = render(openscad, "control_open",
                          'variant_render_mode = "none";\n'
                          f"linear_extrude({COUPON_H}) "
                          f'text("{CONTROL_GLYPH}", '
                          "size = text_size, font = text_font, "
                          'halign = "center", valign = "center");',
                          TMP / "efhw_text_control_open.stl")
    lid = render(openscad, "lid_placed",
                 'variant_render_mode = "lid_placed";',
                 TMP / "efhw_lid_placed.stl")

    problems: list[str] = []

    # The two coupons must actually differ, or the override did not take
    # and the whole comparison below is a shape against itself.  That
    # override has failed silently in this project before.
    if abs(fat.volume - plain.volume) < 1.0:
        raise SystemExit(
            f"the fattened text ({fat.volume:.1f}mm^3) and the plain text "
            f"({plain.volume:.1f}mm^3) are the same size, so setting "
            f"text_fatten = 0 after the include did not take.  Every "
            f"comparison below would be a shape against itself.")

    fat_polys = text_outlines(fat, COUPON_H / 2)
    plain_polys = text_outlines(plain, COUPON_H / 2)

    # ---- 1. the counters survived ---------------------------------------
    print("  TOPOLOGY")
    print(f"    as drawn            : {len(fat_polys)} outlines, "
          f"{counters(fat_polys)} counters")
    print(f"    with fatten = 0     : {len(plain_polys)} outlines, "
          f"{counters(plain_polys)} counters")
    print(f"    one per character   : {glyphs} outlines expected")

    if counters(fat_polys):
        margin = tightest_counter(fat_polys)
        print(f"    tightest counter    : {margin:.2f} mm to its nearest "
              f"edge - room for that much more fattening")
        if margin < MIN_COUNTER:
            problems.append(
                f"the tightest counter is only {margin:.2f}mm from its own "
                f"edge, under the {MIN_COUNTER:.1f}mm that prints as a hole "
                f"rather than a blob.  It survives in CAD and will not "
                f"survive the nozzle.  Reduce text_fatten.")

    if counters(fat_polys) < counters(plain_polys):
        problems.append(
            f"fattening closed {counters(plain_polys) - counters(fat_polys)} "
            f"of the {counters(plain_polys)} counters - an A or a D has "
            f"filled in solid and is no longer a letter.  Reduce "
            f"text_fatten, or raise text_size so the counters start "
            f"bigger.")
    if len(fat_polys) < len(plain_polys):
        problems.append(
            f"fattening merged the glyphs: {len(plain_polys)} outlines "
            f"became {len(fat_polys)}.  Two letters have grown into each "
            f"other.  Reduce text_fatten.")
    if len(plain_polys) != glyphs:
        problems.append(
            f"the unfattened text has {len(plain_polys)} outlines for "
            f"{glyphs} characters - the font is not rendering what was "
            f"asked for.  Check text_font is installed and named exactly.")

    # ---- the control: a counter closed on purpose -----------------------
    #
    # Everything above is a comparison of two counts, and two counts agree
    # very readily when the thing that produces them is broken.  So a
    # single glyph is rendered twice more, once plain and once fattened
    # far past what its counter can absorb, and this script is required to
    # see the hole appear and disappear.  If it cannot, the PASS above
    # means only that nothing was being looked at.
    open_polys = text_outlines(control_open, COUPON_H / 2)
    shut_polys = text_outlines(control, COUPON_H / 2)
    print(f'    control "{CONTROL_GLYPH}" plain   : '
          f"{counters(open_polys)} counters")
    print(f"    same, fattened {CONTROL_FATTEN:.1f}mm : "
          f"{counters(shut_polys)} counters (must be none left)")

    if counters(open_polys) < 1:
        problems.append(
            f'a plain "{CONTROL_GLYPH}" reads as having no counter at all, '
            f"so this script never sees counters and could not report one "
            f"closing.  The fault is in the check, not the model.")
    elif counters(shut_polys) >= counters(open_polys):
        problems.append(
            f'fattening a lone "{CONTROL_GLYPH}" by {CONTROL_FATTEN}mm '
            f"still leaves {counters(shut_polys)} counters, so this script "
            f"cannot see the fault it exists to catch and everything above "
            f"is worthless.  Fix the check before trusting it.")

    # ---- 2. the strokes are wide enough to read -------------------------
    print()
    print("  STROKE WIDTH")
    narrow = pinch_width(fat_polys)
    plain_narrow = pinch_width(plain_polys)

    if math.isinf(narrow):
        print("    narrowest stroke    : no pinch anywhere - the text is "
              "one solid blob")
    else:
        print(f"    narrowest stroke    : {narrow:.2f} mm")
    if math.isinf(plain_narrow):
        print("    unfattened          : also no pinch")
    else:
        print(f"    unfattened          : {plain_narrow:.2f} mm")
    if not math.isinf(narrow) and not math.isinf(plain_narrow):
        print(f"    fattening bought    : {narrow - plain_narrow:+.2f} mm "
              f"(text_fatten {v['text_fatten']:.2f} on each side)")

    if narrow < MIN_STROKE:
        problems.append(
            f"the narrowest stroke is {narrow:.2f}mm, under the "
            f"{MIN_STROKE:.1f}mm that reads as a letter rather than a "
            f"scratch at {v['text_depth']:.1f}mm deep.  Raise text_fatten "
            f"- but re-run this, because that is what closes the counters.")

    # ---- 3. the recess on the real lid ----------------------------------
    print()
    print("  RECESS, MEASURED ON THE LID")

    # The top face itself, taken as the highest thing on the lid.  The
    # letters are cut down from it, so nothing can be above it, and using
    # the mesh rather than z_lid_rim_top means a lid that came out at the
    # wrong height still gives an honest depth.
    z_top = float(lid.bounds[1][2])
    print(f"    top face at z       : {z_top:.3f} "
          f"(nominal {v['z_lid_top']:.3f})")

    biggest = sorted(fat_polys, key=lambda p: p.area, reverse=True)[:4]
    depths, unders = [], []
    for poly in biggest:
        x, y = deepest_point(poly)
        floor = surface_z(lid, x, y, z_top + 5.0, downward=True)
        under = surface_z(lid, x, y, v["z_lid_inner"] - 5.0, downward=False)
        if math.isnan(floor) or math.isnan(under):
            problems.append(
                f"a ray dropped at ({x:.1f}, {y:.1f}), inside a letter, "
                f"misses the lid entirely - the text is not on the lid")
            continue
        depths.append(z_top - floor)
        unders.append(floor - under)
        print(f"    at ({x:6.1f},{y:6.1f}) : cut {z_top - floor:.3f} deep, "
              f"{floor - under:.3f} of lid under it")

    if depths:
        worst_cut = max(depths)
        thinnest = min(unders)
        if abs(worst_cut - v["text_depth"]) > DEPTH_TOL:
            problems.append(
                f"the letters are cut {worst_cut:.2f}mm deep where the "
                f"model asks for {v['text_depth']:.2f}mm.  Something other "
                f"than lid_text_2d() is cutting the top face.")
        if thinnest < MIN_UNDER:
            problems.append(
                f"only {thinnest:.2f}mm of lid is left under the deepest "
                f"letter, against the {MIN_UNDER:.1f}mm minimum - it would "
                f"ghost through or split along the lettering.  Reduce "
                f"text_depth or raise lid_t.")

    # ---- 4. the text stays on the flat --------------------------------
    print()
    print("  FOOTPRINT")
    coords = np.vstack([np.asarray(p.exterior.coords) for p in fat_polys])
    reach = float(np.hypot(coords[:, 0], coords[:, 1]).max())
    flat_r = v["body_or"] - v["knurl_depth"]
    size = fat.bounds[1] - fat.bounds[0]

    print(f"    text block          : {size[0]:.1f} x {size[1]:.1f} mm")
    print(f"    furthest glyph at r : {reach:.2f} mm")
    print(f"    flat top ends at r  : {flat_r:.2f} mm "
          f"(body_or {v['body_or']:.2f} less {v['knurl_depth']:.2f} of knurl)")
    print(f"    margin              : {flat_r - reach:.2f} mm")

    if reach > flat_r - TEXT_MARGIN:
        problems.append(
            f"the lettering reaches r={reach:.1f}mm and the flat top ends "
            f"at r={flat_r:.1f}mm, leaving {flat_r - reach:.1f}mm against "
            f"the {TEXT_MARGIN:.1f}mm wanted - a letter runs into the "
            f"knurl and loses a leg.  Reduce text_size.")

    print()
    print("-" * 62)
    if problems:
        print("FAIL")
        for line in problems:
            print(f"  - {line}")
        return 1

    print("PASS - every counter survives the fattening, no two glyphs have")
    print(f"       merged, the narrowest stroke clears {MIN_STROKE:.1f}mm, "
          f"the recess")
    print("       is the depth asked for with sound lid under it, and a")
    print("       counter closed on purpose was duly spotted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
