"""Measure the enclosure's real geometry on the exported mesh.

The model asserts a great deal about itself and every one of those
asserts passes, because they all compare typed numbers against typed
numbers.  None of them looks at the solid that comes out the other end.
That is the gap this closes: every figure below is read off the mesh,
because the arithmetic is what has been wrong before.

The order is deliberate.  The interior is checked first because it is the
part's entire reason for existing - if the advertised 120 x 75 cylinder
does not fit, nothing further matters.  Then the holes, which fail by
breaking into somewhere they should not.  Then the wall.  Then, last, the
question no interference check can answer: does the water actually run
out, or does the box hold it?

The flange style is taken from the file name and fed back into the model
before its derived values are read.  That is not a nicety.  The equivalent
check on the Peak Design bracket read the DEFAULT socket style no matter
which mesh it was handed, so it measured a hex pocket against a chamfer's
diameter and reported a healthy part as broken.  Here the scallop cuts the
very outline the carabiner holes live in, so reading the wrong style would
be worse than useless.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/audit_enclosure.py [stl]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models"
TMP = ROOT / ".tmp-cad"

OPENSCAD_CANDIDATES = [
    Path(r"C:\Program Files\OpenSCAD\openscad.exe"),
    Path("/usr/bin/openscad"),
    Path("/usr/local/bin/openscad"),
]

# Minimum acceptable material between two voids, in mm.  Three extrusion
# widths at a 0.4mm nozzle - the thinnest thing the slicer will still
# build as a wall rather than as a skin.
MIN_WALL = 1.2

# How much a measured wall may fall short of its nominal before it counts
# as thin.  The mesh is faceted and the probe lands wherever it lands, so
# a few hundredths are the measurement, not the part.
WALL_TOL = 0.15

# Grid pitch for the drainage-path search, in mm.
#
# Two opposing constraints.  Too coarse and the grid steps over the weep
# hole's opening, which is a thin crescent where a round hole breaks out
# through a curved surface at a shallow angle, and reports a blocked hole
# that is actually open.  Too fine and the flood fill needs hundreds of
# thousands of point-in-mesh tests, which this environment runs in pure
# Python because it has no embree - the first version used 0.06mm and did
# not finish.
#
# 0.25mm sits between them with room on both sides: it puts about twelve
# cells across a 3mm weep hole, and about eight through the thinnest wall
# it must not leak through.  The assert below keeps that true if either
# number is ever changed.
PATH_STEP = 0.25

# Bearings are probed a third of a degree off the feature's own plane of
# symmetry.  Dead on it, a ray leaving the axis runs straight through the
# vertical edge of the tessellated hole it is trying to measure, and a
# ray through an edge gets counted twice or not at all.  That is not
# hypothetical: on the first run three of the four carabiner holes read
# as solid material and the fourth measured correctly, saved by nothing
# but rounding.
#
# It costs almost nothing.  A third of a degree is 0.38mm of offset out
# at the carabiner holes, which narrows a 3mm weep hole's measured width
# by 0.07mm - and in the safe direction, since it under-reports the
# opening rather than over-reporting it.
PROBE_SKEW = 0.31  # degrees


def probe_bearing(deg):
    """A bearing in radians, nudged clear of the facet edges."""
    return np.radians(np.asarray(deg, float) + PROBE_SKEW)


def find_openscad() -> Path:
    for path in OPENSCAD_CANDIDATES:
        if path.exists():
            return path
    raise SystemExit("OpenSCAD not found - install it or edit OPENSCAD_CANDIDATES")


ECHO_KEYS = [
    "interior_r", "interior_h", "wall_or", "wall_t",
    "flange_or", "flange_t",
    "carabiner_r", "carabiner_d", "carabiner_wall",
    "weep_d", "weep_count", "weep_r",
    "cable_slot_w", "cable_slot_count", "cable_slot_h",
    "z_floor_edge", "z_floor_apex", "z_rim", "z_tongue_top",
    "thread_minor_r", "thread_major_r",
    "groove_ir", "groove_or", "lid_or", "z_wall_base",
]


def echoed_values(openscad: Path, style: str) -> dict[str, float]:
    """Read the model's own derived numbers, so the probes land in the
    right places even after the design is retuned.

    The flange style has to match the mesh.  It sets the outline the
    carabiner holes are cut from, so reading one style's numbers while
    measuring the other's solid would compare a hole against a flange
    edge that is not there.
    """
    parts = "".join(f'" {k}=", {k}, ' for k in ECHO_KEYS)
    scad = MODELS / ".audit_efhw_probe.scad"
    scad.write_text(
        "include <efhw_enclosure.scad>\n"
        'variant_render_mode = "none";\n'
        f'flange_style = "{style}";\n'
        f'echo(str("AUDIT", {parts}""));\n',
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [str(openscad), "-o", str(TMP / "audit_efhw_probe.stl"), str(scad)],
            capture_output=True, text=True,
        )
    finally:
        scad.unlink(missing_ok=True)

    text = (result.stderr or "") + (result.stdout or "")
    line = next((l for l in text.splitlines() if "AUDIT" in l), None)
    if line is None:
        print(text[-2000:])
        raise SystemExit("could not read the model's derived values")

    vals: dict[str, float] = {}
    for token in line.replace('"', "").split():
        if "=" in token:
            key, _, value = token.partition("=")
            try:
                vals[key] = float(value)
            except ValueError:
                pass

    missing = [k for k in ECHO_KEYS if k not in vals]
    if missing:
        raise SystemExit(f"the model did not echo: {', '.join(missing)}")
    return vals


# ---- probes ----------------------------------------------------------

def runs_of(d, flag):
    """Contiguous spans of d where flag holds, as (start, end)."""
    out, start = [], None
    for value, f in zip(d, flag):
        if f and start is None:
            start = float(value)
        elif not f and start is not None:
            out.append((start, float(value)))
            start = None
    if start is not None:
        out.append((start, float(d[-1])))
    return out


def radial_hits(mesh: trimesh.Trimesh, thetas, zs) -> list[np.ndarray]:
    """Radii at which a ray leaving the axis crosses the surface.

    Cast, not sampled.  A 2.00mm wall then reads as 2.00 rather than as
    whatever the sample pitch rounds it to, and one ray costs less than
    the several hundred inside/outside tests the same answer used to
    take - which matters, because there is no compiled ray engine in this
    environment and every point test is two rays in Python.

    The crossings alternate, so whether the axis itself is solid can be
    read off the count rather than assumed: an odd number of crossings
    means the ray started inside.
    """
    thetas = np.asarray(thetas, float)
    zs = np.asarray(zs, float)
    origins = np.column_stack([np.zeros(len(zs)), np.zeros(len(zs)), zs])
    dirs = np.column_stack(
        [np.cos(thetas), np.sin(thetas), np.zeros(len(thetas))])

    locs, ray_idx, _ = mesh.ray.intersects_location(
        ray_origins=origins, ray_directions=dirs, multiple_hits=True)

    out: list[list[float]] = [[] for _ in range(len(zs))]
    for point, idx in zip(locs, ray_idx):
        out[idx].append(float(np.hypot(point[0], point[1])))
    return [np.array(sorted(r)) for r in out]


def surface_below(mesh: trimesh.Trimesh, xs, ys, z_from: float):
    """Height of the highest solid surface seen looking straight down.

    Cast rather than sampled, so a floor that is 0.03mm out is reported as
    0.03mm out rather than rounded to the nearest sample.  NaN where the
    ray finds nothing at all, which is a different failure from finding
    the floor in the wrong place.
    """
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    origins = np.column_stack([xs, ys, np.full(len(xs), z_from)])
    dirs = np.tile([0.0, 0.0, -1.0], (len(xs), 1))

    locs, ray_idx, _ = mesh.ray.intersects_location(
        ray_origins=origins, ray_directions=dirs, multiple_hits=True)

    best = np.full(len(xs), np.nan)
    for point, idx in zip(locs, ray_idx):
        if np.isnan(best[idx]) or point[2] > best[idx]:
            best[idx] = point[2]
    return best


def solid_at(mesh: trimesh.Trimesh, thetas, zs, rs) -> np.ndarray:
    """Whether each point is buried in material.

    Counted from the crossings on a ray leaving the axis: past the last
    one is fresh air, so an odd number of crossings beyond a point means
    the point is inside the solid.

    Steadier than a general point-in-mesh test, which on this mesh called
    six of the forty-eight points on one ring clear when every one of
    them was a millimetre deep in the flange - and clear is the direction
    that hides a fault rather than inventing one.
    """
    hits = radial_hits(mesh, thetas, zs)
    return np.array([np.count_nonzero(h > r) % 2 == 1
                     for h, r in zip(hits, np.asarray(rs, float))])


def void_arcs(mesh: trimesh.Trimesh, r: float, z: float,
              step_deg: float = 0.3):
    """Openings around a circle, as (centre, half width) in degrees.

    Wraps, because an opening that straddles zero is still one opening
    and counting it as two would halve its measured width.
    """
    angles = np.arange(0.0, 360.0, step_deg)
    void = ~solid_at(mesh, probe_bearing(angles),
                     np.full(len(angles), z), np.full(len(angles), r))

    if void.all():
        return [(0.0, 180.0)]
    if not void.any():
        return []

    # Rotate so the list starts on solid, then every run is whole.
    first_solid = int(np.argmax(~void))
    rolled = np.roll(void, -first_solid)
    spans = runs_of(np.arange(len(rolled)) * step_deg, rolled)

    out = []
    for a0, a1 in spans:
        width = a1 - a0 + step_deg
        centre = (a0 + a1) / 2 + first_solid * step_deg
        out.append((centre % 360.0, width / 2))
    return sorted(out)


def plane_solid(mesh: trimesh.Trimesh, theta: float,
                us: np.ndarray, ws: np.ndarray) -> np.ndarray:
    """Solid/void map of one meridian half-plane.

    Built from ray crossings, one ray per row, with a single inside test
    per span to say which side of each crossing is material.  The obvious
    alternative - testing every cell - is two rays per cell in Python and
    takes long enough that the run gets killed before it prints anything.

    Boundaries land where the surface actually is rather than on the
    nearest grid line, which is what lets the map resolve an opening
    narrower than its own pitch.
    """
    hits = radial_hits(mesh, np.full(len(ws), theta), ws)

    solid = np.zeros((len(us), len(ws)), dtype=bool)
    for j, h in enumerate(hits):
        e = np.concatenate([[us[0]], h[(h > us[0]) & (h < us[-1])], [us[-1]]])
        e = e[np.concatenate([[True], np.diff(e) > 1e-6])]
        for k, mid in enumerate((e[:-1] + e[1:]) / 2):
            if np.count_nonzero(h > mid) % 2 == 1:
                solid[np.searchsorted(us, e[k]):
                      np.searchsorted(us, e[k + 1]), j] = True
    return solid


def flood(void: np.ndarray, seed: tuple[int, int]) -> np.ndarray:
    """Everything reachable through void, four-connected."""
    reached = np.zeros_like(void, dtype=bool)
    if not void[seed]:
        return reached
    stack = [seed]
    reached[seed] = True
    nu, nw = void.shape
    while stack:
        i, j = stack.pop()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = i + di, j + dj
            if 0 <= a < nu and 0 <= b < nw and void[a, b] and not reached[a, b]:
                reached[a, b] = True
                stack.append((a, b))
    return reached


def drain_mouth(mesh: trimesh.Trimesh, theta: float,
                us: np.ndarray, ws: np.ndarray, seed_r: float):
    """Where a void that reaches the interior breaks out of the part.

    Returns the height range of the opening, or None if the interior does
    not reach the outside anywhere in this plane.

    Searched in the feature's own plane of symmetry, which is where its
    opening is widest - a path that is not there is not anywhere - and
    only up to a little above the flange, so the fill cannot cheat by
    climbing the interior and going out over the rim.
    """
    solid = plane_solid(mesh, theta, us, ws)

    # Outside the part is whatever lies beyond the last solid sample at
    # that height, worked out row by row.  Taken as one radius for the
    # whole part instead, an overhanging flange would make the wall above
    # it look like open air.
    outer = np.full(len(ws), -np.inf)
    for j in range(len(ws)):
        col = np.nonzero(solid[:, j])[0]
        if col.size:
            outer[j] = us[col.max()]
    exterior = us[:, None] > outer[None, :]

    seed = (int(np.argmin(np.abs(us - seed_r))), len(ws) - 2)
    reached = flood(~solid, seed)
    if not reached.any():
        raise SystemExit(
            "the interior seed for the drainage search landed in solid - "
            "the probe is wrong, not the part")

    out_cells = reached & exterior
    if not out_cells.any():
        return None

    # The mouth is where the reached void crosses the surface, not
    # everything beyond it: once outside, the whole half-plane is
    # connected and its height range would mean nothing.
    inner = reached & ~exterior
    mouth = np.zeros_like(out_cells)
    mouth[1:, :] |= out_cells[1:, :] & inner[:-1, :]
    mouth[:-1, :] |= out_cells[:-1, :] & inner[1:, :]
    mouth[:, 1:] |= out_cells[:, 1:] & inner[:, :-1]
    mouth[:, :-1] |= out_cells[:, :-1] & inner[:, 1:]

    wz = ws[np.nonzero(mouth)[1]]
    return float(wz.min()), float(wz.max())


def main() -> int:
    openscad = find_openscad()
    TMP.mkdir(exist_ok=True)

    stl = (Path(sys.argv[1]) if len(sys.argv) > 1
           else MODELS / "efhw_enclosure_body_scallop.stl")
    if not stl.exists():
        raise SystemExit(f"no such file: {stl} - run export_enclosure.py first")

    style = next((s for s in ("scallop", "disc") if s in stl.stem), "scallop")

    v = echoed_values(openscad, style)
    mesh = trimesh.load(stl)

    # The drainage flood fill is only meaningful if its grid is fine
    # enough to pass through the hole it is looking for and too fine to
    # leak through the wall around it.  Both are checked against the
    # model's own numbers rather than assumed, since either could change.
    assert v["weep_d"] / PATH_STEP >= 6, (
        f"the drainage grid is {PATH_STEP}mm but the weep holes are only "
        f"{v['weep_d']}mm across - the search would step over them and "
        f"call an open hole blocked")
    assert MIN_WALL / PATH_STEP >= 4, (
        f"the drainage grid is {PATH_STEP}mm against a {MIN_WALL}mm "
        f"minimum wall - the flood fill could leak straight through solid "
        f"material and call a blind pocket a drain")

    print(f"=== {stl.name} ===  (flange style: {style})")
    size = mesh.bounds[1] - mesh.bounds[0]
    print(f"  {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm, "
          f"{mesh.volume / 1000:.1f} cm^3, "
          f"{mesh.body_count} body, watertight={mesh.is_watertight}")
    print()

    problems: list[str] = []

    lug_nominal = 45.0 + np.arange(4) * 90.0
    lug_deg = probe_bearing(lug_nominal)

    # ---- the interior is the point of the whole part -------------------
    print("  INTERIOR VOLUME")
    z_lo, z_hi = v["z_floor_apex"], v["z_floor_apex"] + v["interior_h"]

    # Sampled just inside the advertised surface, so a wall exactly on
    # size reads as clear rather than as a coin toss against the facets.
    ang_deg = np.arange(0.0, 360.0, 7.5)
    zs = np.linspace(z_lo + 0.05, z_hi - 0.05, 16)
    tt, zz = np.meshgrid(probe_bearing(ang_deg), zs, indexing="ij")

    # The crown apex is the tallest thing on the floor, so it - not the
    # perimeter - is what sets the real height.
    thetas = np.concatenate([tt.ravel(), probe_bearing([0.0])])
    z_pts = np.concatenate([zz.ravel(), [z_lo + 0.05]])
    r_pts = np.concatenate([np.full(tt.size, v["interior_r"] - 0.05), [0.0]])
    blocked = solid_at(mesh, thetas, z_pts, r_pts)

    # The floor as built, along a radius, for the height above and the
    # drainage check below.
    radii = np.linspace(0.0, v["interior_r"] - 1.0, 13)
    floor = surface_below(mesh, radii, np.zeros_like(radii), z_hi - 2.0)
    floor_max = float(np.nanmax(floor))

    print(f"    advertised          : {2 * v['interior_r']:.1f} dia x "
          f"{v['interior_h']:.1f} tall, z {z_lo:.2f} to {z_hi:.2f}")
    print(f"    highest floor found : z {floor_max:.2f} "
          f"(model puts the apex at z {z_lo:.2f})")
    print(f"    clear height        : {z_hi - floor_max:.2f} mm")
    print(f"    samples in solid    : {int(blocked.sum())} of {len(blocked)}")

    if blocked.any():
        bad_z = z_pts[blocked]
        extra = ""
        if floor_max > z_lo + 0.05 and abs(floor_max - v["flange_t"]) < 0.2:
            extra = (f"  The floor measures the top of the base flange "
                     f"(flange_t = {v['flange_t']:.2f}), which stands "
                     f"{v['flange_t'] - v['z_floor_apex']:.2f}mm higher than "
                     f"the crown apex at z {v['z_floor_apex']:.2f} - the "
                     f"flange has swallowed the floor.  Either raise the "
                     f"floor above flange_t or measure z_floor_apex from "
                     f"z_flange_top.")
        problems.append(
            f"the advertised {2 * v['interior_r']:.0f} x {v['interior_h']:.0f} "
            f"clear cylinder does not fit: {int(blocked.sum())} of "
            f"{len(blocked)} sample points are inside solid, from z "
            f"{bad_z.min():.2f} to z {bad_z.max():.2f}.  Only "
            f"{z_hi - floor_max:.2f}mm of the {v['interior_h']:.1f}mm is "
            f"actually clear.{extra}")

    # ---- carabiner holes vs the wall and the flange edge ---------------
    #
    # Two ways to get this wrong and they fail differently.  Break inward
    # and the hole opens into the interior, which lets water straight in
    # and thins the wall carrying the load.  Break outward and the lug
    # tears off the first time the whole thing swings on a carabiner.
    print()
    print("  CARABINER HOLES vs INTERIOR")
    z_flange_mid = v["flange_t"] / 2
    z_wall_probe = v["z_wall_base"] + 5.0

    at_flange = radial_hits(mesh, lug_deg, np.full(len(lug_deg), z_flange_mid))
    at_wall = radial_hits(mesh, lug_deg, np.full(len(lug_deg), z_wall_probe))

    for k, theta in enumerate(lug_deg):
        rf, rw = at_flange[k], at_wall[k]
        deg = lug_nominal[k]

        # Halfway up the flange the axis is buried in solid, so the
        # crossings pair off as voids from the very first one.
        edge = float(rf[-1]) if rf.size else float("nan")
        wall_od = float(rw[1]) if rw.size >= 2 else float("nan")
        hole = next(((float(a), float(b)) for a, b in zip(rf[0::2], rf[1::2])
                     if a <= v["carabiner_r"] <= b), None)

        if hole is None and v["carabiner_r"] > edge:
            print(f"    {deg:5.1f} deg          : flange ends at r "
                  f"{edge:.2f}, hole wanted at r "
                  f"{v['carabiner_r'] - v['carabiner_d'] / 2:.2f} to "
                  f"{v['carabiner_r'] + v['carabiner_d'] / 2:.2f}")
            problems.append(
                f"at {deg:.0f} degrees the flange stops at r {edge:.2f}, "
                f"short of the carabiner hole at r {v['carabiner_r']:.2f} - "
                f"there is no lug there at all, so the hole has been cut "
                f"away rather than drilled.  The scallops sit on the same "
                f"bearings as the holes; move one set by half a spacing")
            continue

        if hole is None:
            print(f"    {deg:5.1f} deg          : no hole - solid across r "
                  f"{v['carabiner_r']:.2f}")
            problems.append(
                f"there is no carabiner hole at {deg:.0f} degrees: the mesh "
                f"is solid across r {v['carabiner_r']:.2f} where the hole "
                f"should be")
            continue

        gap_in = hole[0] - wall_od
        gap_out = edge - hole[1]
        print(f"    {deg:5.1f} deg          : hole r {hole[0]:.2f}..{hole[1]:.2f}"
              f"   wall OD {wall_od:.2f}   flange edge {edge:.2f}"
              f"   inboard {gap_in:.2f}   outboard {gap_out:.2f}")

        if gap_in < 1.5:
            problems.append(
                f"only {gap_in:.2f}mm between the carabiner hole at "
                f"{deg:.0f} degrees and the cylinder wall - raise "
                f"carabiner_wall")
        if gap_out < 1.5:
            problems.append(
                f"only {gap_out:.2f}mm of flange outboard of the carabiner "
                f"hole at {deg:.0f} degrees - the lug would tear out.  "
                f"Widen the flange or pull the holes inboard")

    # ---- weep holes ----------------------------------------------------
    #
    # A weep hole that does not go all the way through is worse than no
    # weep hole: it looks like drainage and holds water.  So this does not
    # ask whether a hole was cut, it asks whether a path exists from the
    # inside to the outside, by filling the void in the hole's own plane
    # of symmetry.  That plane is where the opening is widest, so a path
    # that does not exist there does not exist anywhere.
    #
    # And where it comes out matters as much as whether it does.  Above
    # the flange the water lands on the flange's top face and sits in the
    # corner it makes with the wall, which is the puddle this enclosure
    # was shaped to avoid.
    print()
    print("  WEEP HOLES")
    n_weep = int(round(v["weep_count"]))
    weep_nominal = 45.0 + np.arange(n_weep) * 360.0 / n_weep
    weep_deg = probe_bearing(weep_nominal)

    us = np.arange(v["interior_r"] - 4.0, v["flange_or"] + 3.0, PATH_STEP)
    ws = np.arange(0.0, v["z_wall_base"] + 8.0, PATH_STEP)
    seed_r = v["interior_r"] - 2.0

    # Prove the search can find a path before believing it when it does
    # not.  A cable slot is a hole through the same wall that indisputably
    # connects the inside to the outside, so if the fill cannot get out
    # through one of those, then "no weep hole drains" is a statement
    # about this code and not about the enclosure.
    #
    # The slot bearings are measured, not typed, and the same measurement
    # is used again further down.
    slots = void_arcs(mesh, v["weep_r"],
                      v["z_floor_edge"] + v["cable_slot_h"] / 2)
    control = (drain_mouth(mesh, probe_bearing(slots[0][0]), us, ws, seed_r)
               if slots else None)
    if control is None:
        problems.append(
            "the drainage search cannot find its way out through a cable "
            "slot, which is an open channel through the wall.  Nothing it "
            "says about the weep holes means anything until that is fixed")
        print("    control (slot)      : NOT FOUND - the search is blind")
    else:
        print(f"    control (slot)      : drains, mouth at z "
              f"{control[0]:.2f}..{control[1]:.2f}")

    found = 0
    drained = 0
    for theta, deg in zip(weep_deg, weep_nominal):

        # Is anything cut here at all?  The control probe sits where the
        # wall must be solid - without it a mesh that was void everywhere
        # would read as four perfect holes.
        #
        # A QUARTER of the spacing round, not half.  Half a weep spacing
        # lands exactly on a cable slot on this part, and the control duly
        # reported the wall as missing on two of the four holes - a fault
        # in the check, dressed up as a fault in the model.
        off = theta + np.pi / (2 * n_weep)
        here, there = solid_at(
            mesh, [theta, off],
            [v["z_floor_edge"], v["z_floor_edge"]],
            [v["weep_r"], v["weep_r"]])

        if not there:
            problems.append(
                "the wall between the weep holes is not solid - the probe "
                "cannot tell a hole from a gap and nothing below is "
                "trustworthy")
        if here:
            print(f"    {deg:5.1f} deg          : nothing cut at r "
                  f"{v['weep_r']:.2f}, z {v['z_floor_edge']:.2f}")
            continue
        found += 1

        mouth = drain_mouth(mesh, theta, us, ws, seed_r)
        if mouth is None:
            print(f"    {deg:5.1f} deg          : cut, but no path from the "
                  f"interior to the outside")
            continue

        drained += 1
        print(f"    {deg:5.1f} deg          : drains, mouth at z "
              f"{mouth[0]:.2f}..{mouth[1]:.2f} "
              f"(flange top z {v['flange_t']:.2f})")

        if mouth[0] > v["flange_t"]:
            problems.append(
                f"the {deg:.0f} degree weep hole comes out at z "
                f"{mouth[0]:.2f}, above the flange top face at z "
                f"{v['flange_t']:.2f} - the water it drains lands on the "
                f"flange and pools in the corner against the wall.  Steepen "
                f"the hole or take it out through the flange")

    print(f"    holes cut           : {found} of {n_weep}")
    print(f"    holes that drain    : {drained} of {n_weep}")

    if found < n_weep:
        problems.append(
            f"only {found} of {n_weep} weep holes are present in the mesh - "
            f"at some hanging angle there would be no drain at the low point")
    if drained < found:
        problems.append(
            f"{found - drained} of the {found} weep holes are blind pockets: "
            f"they open into the interior and stop inside the material.  "
            f"Water collects in them and cannot get out, which is worse than "
            f"having no weep hole at all.  Lengthen the cut so it clears the "
            f"outside surface")

    # ---- cable slots vs weep holes -------------------------------------
    #
    # Compared as bearings rather than in three dimensions on purpose.  If
    # either feature is ever moved up or down the wall the height that
    # separates them today disappears, and the two openings merge into one
    # long tear at the corner where the wall meets the floor - the most
    # loaded line on the part.
    print()
    print("  CABLE SLOTS vs WEEP HOLES")

    # The slots reach down to the same height as the weep holes, so the
    # lower scan sees both and the two have to be told apart before they
    # can be compared.  Measured against the bearings only the slots
    # appear on, and dropped - otherwise the closest pair found is a slot
    # sitting on top of itself, which reads as a negative wall.
    mixed = void_arcs(mesh, v["weep_r"], v["z_floor_edge"])
    weeps = [(c, h) for c, h in mixed
             if all(abs((c - sc + 180) % 360 - 180) > sh + h
                    for sc, sh in slots)]

    print(f"    cable slots         : "
          f"{[f'{c:.1f}+-{h:.2f} deg' for c, h in slots]}")
    print(f"    weep holes          : "
          f"{[f'{c:.1f}+-{h:.2f} deg' for c, h in weeps]}")

    if len(slots) != int(round(v["cable_slot_count"])):
        problems.append(
            f"found {len(slots)} cable slots where the model asks for "
            f"{int(round(v['cable_slot_count']))}")
    if len(weeps) != n_weep:
        problems.append(
            f"found {len(weeps)} weep holes around the wall where the model "
            f"asks for {n_weep}")

    if slots and weeps:
        worst = min(
            (abs((sc - wc + 180) % 360 - 180) - sh - wh, sc, wc)
            for sc, sh in slots for wc, wh in weeps)
        gap_deg, at_s, at_w = worst
        gap_mm = np.radians(gap_deg) * v["weep_r"]
        print(f"    closest pair        : slot at {at_s:.1f} deg, weep at "
              f"{at_w:.1f} deg")
        print(f"    material between    : {gap_deg:.2f} deg = "
              f"{gap_mm:.2f} mm of arc")
        if gap_mm < MIN_WALL:
            problems.append(
                f"only {gap_mm:.2f}mm of wall between a cable slot and a "
                f"weep hole - they merge into one opening at the weakest "
                f"line on the part.  Move the weep holes off the slot "
                f"bearings")

    # ---- wall thickness ------------------------------------------------
    #
    # Probed on bearings that miss both the slots and the weep holes, and
    # below the flare that carries the thread, so this is the plain wall
    # and nothing else.
    print()
    print("  WALL THICKNESS")
    probe_deg = probe_bearing(22.5 + np.arange(8) * 45.0)
    probe_z = np.linspace(v["z_wall_base"] + 2.0, v["z_tongue_top"] - 0.5, 20)
    tt, zz = np.meshgrid(probe_deg, probe_z, indexing="ij")
    hits = radial_hits(mesh, tt.ravel(), zz.ravel())

    thinnest, where = float("inf"), None
    for h, theta, z in zip(hits, tt.ravel(), zz.ravel()):
        # The first crossing outward from the axis is the bore; the next
        # one is the outside.  Anything nearer in than the bore would be
        # something loose in the interior, and there is nothing loose.
        h = h[h >= v["interior_r"] - 1.0]
        if h.size < 2:
            problems.append(
                f"no wall at all at {np.degrees(theta):.0f} degrees, z "
                f"{z:.1f} - the cylinder has a hole in it there")
            continue
        t = float(h[1] - h[0])
        if t < thinnest:
            thinnest, where = t, (np.degrees(theta), z, (h[0], h[1]))

    if where is not None:
        deg, z, span = where
        print(f"    nominal             : {v['wall_t']:.2f} mm")
        print(f"    thinnest measured   : {thinnest:.2f} mm at "
              f"{deg:.0f} deg, z {z:.1f} (r {span[0]:.2f}..{span[1]:.2f})")
        if thinnest < v["wall_t"] - WALL_TOL:
            problems.append(
                f"the wall is {thinnest:.2f}mm at {deg:.0f} degrees, z "
                f"{z:.1f}, against a nominal {v['wall_t']:.2f}mm - something "
                f"is eating into it there")

    # ---- does it actually drain ----------------------------------------
    #
    # The one question none of the interference checks can reach.  A box
    # can pass every clearance test ever written and still be a bucket.
    print()
    print("  DRAINAGE SENSE")
    print("    floor profile, centre outward:")
    for r, h in zip(radii[::3], floor[::3]):
        print(f"      r {r:5.1f} : z {h:.3f}")

    centre_z = float(floor[0])
    rim_z = float(floor[-1])
    fall = centre_z - rim_z
    print(f"    fall from centre    : {fall:+.3f} mm over "
          f"{radii[-1]:.1f} mm of radius")

    if not np.isfinite(centre_z) or not np.isfinite(rim_z):
        problems.append(
            "the downward probe missed the floor - there is no floor under "
            "part of the interior")
    elif fall <= 0.05:
        problems.append(
            f"the floor falls {fall:+.3f}mm from the centre to the wall, so "
            f"it is flat or sloping inward - water collects in the middle "
            f"instead of running to the weep holes, which is the opposite of "
            f"what the crown is for.  The crown is {v['z_floor_apex'] - v['z_floor_edge']:.2f}mm "
            f"tall in the model, so something is filling it in")

    print()
    print("-" * 62)
    if problems:
        print("FAIL")
        for line in problems:
            print(f"  - {line}")
        return 1

    print("PASS - the advertised interior fits, every hole clears its")
    print("       neighbours, the wall holds section, and the floor drains")
    print("       outward to weep holes that come out below the flange")
    return 0


if __name__ == "__main__":
    sys.exit(main())
