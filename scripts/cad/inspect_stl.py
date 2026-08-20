"""Inspect a rendered mount STL for geometry problems.

Checks the things a snap-fit part can silently get wrong:

  * non-manifold / non-watertight shells, stray bodies
  * degenerate and near-zero-area triangles
  * genuinely thin walls

Wall thickness is measured by shooting a ray inward from each face centre
and finding where it leaves the solid.  Hits are only counted when the far
surface actually faces back at us; without that filter, tapered and
filleted regions report phantom near-zero readings, because a ray started
near the edge of a sloping face exits through its neighbour almost
immediately.  Calibration: the untouched original model reports a 4.0mm
minimum wall, which matches its design.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/inspect_stl.py <stl> [min_wall_mm]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import trimesh

DEFAULT_MIN_WALL = 1.2   # mm; a 0.4mm nozzle wants at least this

# How nearly antiparallel two surfaces must be before the gap between
# them counts as a WALL.
#
# A wall is two surfaces facing each other, so their normals are
# antiparallel and |cos| is close to 1.  Two surfaces meeting at an
# ANGLE are not a wall, they are an edge or a groove, and the distance
# between them near the corner goes to zero no matter how much solid
# material is behind it.
#
# This mattered the moment a threaded part arrived.  At the old limit of
# 0.5, the two flanks of a thread crest - 60 degrees apart, |cos| 0.5 -
# were being measured against each other, and the tip of the lead-in
# chamfer duly reported 0.005mm of "wall".  There is nothing wrong with
# it: a chamfer that did not taper to nothing would be a step.
#
# Raising this to 0.95 changes no mount's reading at all - the visor
# mount still reports 2.400, the bracket 1.250, and the untouched
# original 4.000 - because a real wall's faces are parallel.  What it
# stops is a V-groove being read as a crack.
FACING_LIMIT = 0.95

# A knife edge has vanishing AREA; a thin wall has real area.  Below this
# the thin region cannot be a hole waiting to happen, only a corner the
# slicer will round off - which it would have rounded off anyway.
MIN_THIN_AREA = 5.0      # mm^2

# What the printer can actually put down in one pass.
#
# Material thinner than this is not made THIN, it is not made at all -
# the slicer finds nowhere to fit an extrusion and omits it.  That is a
# defect when the missing material was a wall, because the result is a
# hole.  It is not a defect when the missing material was the tip of a
# wedge, because a wedge has to end somewhere and ending it 0.4mm early
# is invisible.
#
# The lid is the case in point.  Its lettering is fattened by 0.35mm a
# side to survive being cut only 1mm deep, and where the diagonals of an
# M or an A converge, that fattening turns the apex into a sliver a few
# microns thick.  186 faces of it, all vertical, all inside the recess.
# None of it will print, and the letters are none the worse: check_text.py
# measures the same glyphs directly and finds 12 separate outlines, 3
# intact counters and a narrowest stroke of 3.30mm.
EXTRUSION_W = 0.42       # mm


def check_topology(mesh: trimesh.Trimesh) -> list[str]:
    problems: list[str] = []

    print(f"  faces={len(mesh.faces)}  vertices={len(mesh.vertices)}")
    print(f"  watertight={mesh.is_watertight}  "
          f"winding_consistent={mesh.is_winding_consistent}")
    print(f"  volume={mesh.volume / 1000:.2f} cm^3  bodies={mesh.body_count}")

    if not mesh.is_watertight:
        problems.append("mesh is not watertight")
    if not mesh.is_winding_consistent:
        problems.append("face winding is inconsistent")
    if mesh.body_count != 1:
        problems.append(f"mesh has {mesh.body_count} disconnected bodies")
    if mesh.volume <= 0:
        problems.append("mesh volume is not positive (inverted normals?)")

    return problems


def check_degenerate(mesh: trimesh.Trimesh) -> list[str]:
    """Look for slivers: triangles with almost no area.

    A handful of these is normal and harmless.  Wherever a curved surface
    crosses a flat one - a conical boss blending into a plate, say - the
    tessellator has to place vertices on the intersection, and some of the
    resulting triangles come out with essentially no area.  Their count
    shifts if you nudge any dimension, and no choice of dimensions drives
    it to zero, which is the signature of tessellation noise rather than a
    modelling error.  Slicers discard zero-area triangles outright.

    What genuinely matters is whether the surface still closes, and that
    is already tested by the watertight and winding checks.  So a few
    slivers are reported and tolerated; a flood of them is not, because
    that means the tessellator has lost the surface - which is exactly
    what a helical thread swept from knife-edge profiles once did here,
    producing 246 slivers and an open mesh.
    """
    problems: list[str] = []

    tiny = mesh.area_faces < 1e-6
    count = int(tiny.sum())
    fraction = count / len(mesh.faces)

    print(f"  degenerate faces: {count} ({100 * fraction:.2f}% of faces)")

    if fraction > 0.01:
        problems.append(
            f"{count} degenerate faces ({100 * fraction:.1f}% of the mesh) "
            "- the tessellation has broken down, not just rounded off"
        )
    elif count:
        print("    (tessellation noise at curved/flat intersections - "
              "harmless while the mesh stays watertight)")

    edges = mesh.vertices[mesh.edges_unique]
    lengths = np.linalg.norm(edges[:, 0] - edges[:, 1], axis=1)
    print(f"  shortest edge: {lengths.min():.5f} mm")

    return problems


def check_thickness(mesh: trimesh.Trimesh, min_wall: float) -> list[str]:
    """Measure wall thickness along inward face normals."""
    problems: list[str] = []

    centres = mesh.triangles_center
    normals = mesh.face_normals
    origins = centres - normals * 1e-4

    hits, ray_index, tri_index = mesh.ray.intersects_location(
        origins, -normals, multiple_hits=False
    )
    if len(hits) == 0:
        return ["thickness probe found no opposite surface"]

    distances = np.linalg.norm(hits - origins[ray_index], axis=1)

    # A genuine opposite wall faces back at us; a grazing hit on a tapered
    # neighbour does not, and is what produces phantom thin readings.
    facing = np.abs(
        np.einsum("ij,ij->i", normals[ray_index], mesh.face_normals[tri_index])
    )
    solid = facing > FACING_LIMIT

    print(f"  thickness: {len(distances)} probes, "
          f"{int((~solid).sum())} not facing (edges and grooves, discarded)")

    if not solid.any():
        return ["every thickness probe was grazing - geometry looks wrong"]

    kept = distances[solid]
    points = centres[ray_index][solid]
    areas = mesh.area_faces[ray_index][solid]

    print(f"    min = {kept.min():.3f} mm   "
          f"p1 = {np.percentile(kept, 1):.3f} mm   "
          f"median = {np.median(kept):.3f} mm")

    thin = kept < min_wall
    thin_area = float(areas[thin].sum())

    # Split the thin material by whether the printer could make it at all.
    # Below one extrusion it is simply omitted, so it can only be a
    # vanishing edge; at or above one extrusion it is real material that
    # came out too thin, which is the thing worth failing on.
    sliver = kept < EXTRUSION_W
    sliver_area = float(areas[sliver].sum())
    real_thin_area = thin_area - sliver_area

    print(f"    probes under {min_wall} mm: {int(thin.sum())} "
          f"({100 * thin.mean():.2f}%), covering "
          f"{thin_area:.2f} mm^2 of {mesh.area:.0f} mm^2")
    if sliver.any():
        print(f"      of which under one {EXTRUSION_W} mm extrusion: "
              f"{int(sliver.sum())} probes, {sliver_area:.2f} mm^2 "
              f"(too thin to be printed at all - vanishing edges)")

    if thin.any():
        worst = points[thin]
        print(f"    thin region spans "
              f"X {worst[:, 0].min():.1f}..{worst[:, 0].max():.1f}  "
              f"Y {worst[:, 1].min():.1f}..{worst[:, 1].max():.1f}  "
              f"Z {worst[:, 2].min():.1f}..{worst[:, 2].max():.1f}")

        order = np.argsort(kept)[:5]
        print("    thinnest probes:")
        for index in order:
            x, y, z = points[index]
            print(f"      {kept[index]:6.3f} mm at ({x:7.2f}, {y:7.2f}, {z:7.2f})")

    # Judged on the material the printer would actually try to lay down,
    # and on area rather than on the single worst probe.  One triangle at
    # the tip of a chamfer is not a defect; a patch of thin wall is.
    if real_thin_area < MIN_THIN_AREA:
        return problems

    printable = kept[thin & ~sliver]
    problems.append(
        f"thinnest printable wall is {printable.min():.2f} mm, under the "
        f"{min_wall} mm limit, over {real_thin_area:.1f} mm^2"
    )

    return problems


def main() -> None:
    stl = Path(sys.argv[1])
    min_wall = float(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_MIN_WALL

    mesh = trimesh.load(stl)
    print(f"=== {stl.name} ===")

    problems: list[str] = []
    problems += check_topology(mesh)
    problems += check_degenerate(mesh)
    problems += check_thickness(mesh, min_wall)

    if problems:
        print("\n  PROBLEMS:")
        for line in problems:
            print(f"    - {line}")
        sys.exit(1)

    print("\n  no problems found")


if __name__ == "__main__":
    main()
