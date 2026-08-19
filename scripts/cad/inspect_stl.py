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
GRAZE_LIMIT = 0.5        # |cos| below this counts as a grazing hit


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
    solid = facing > GRAZE_LIMIT

    print(f"  thickness: {len(distances)} probes, "
          f"{int((~solid).sum())} grazing (discarded)")

    if not solid.any():
        return ["every thickness probe was grazing - geometry looks wrong"]

    kept = distances[solid]
    points = centres[ray_index][solid]

    print(f"    min = {kept.min():.3f} mm   "
          f"p1 = {np.percentile(kept, 1):.3f} mm   "
          f"median = {np.median(kept):.3f} mm")

    thin = kept < min_wall
    print(f"    probes under {min_wall} mm: {int(thin.sum())} "
          f"({100 * thin.mean():.2f}%)")

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

    if kept.min() < 0.05:
        problems.append(f"near zero-thickness material ({kept.min():.3f} mm)")
    elif kept.min() < min_wall:
        problems.append(
            f"thinnest wall is {kept.min():.2f} mm, under the {min_wall} mm limit"
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
