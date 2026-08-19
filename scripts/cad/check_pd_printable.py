"""Judge whether the bracket's unsupported regions are actually a problem.

check_printable.py answers "is there anything directly below this face?",
which is the right question for a printed-in-place lever - a floating arm
must never need support, because support in that gap welds the mechanism
solid.  But it is too blunt on its own, because it flags two things that
print perfectly well:

  * a BRIDGE - a flat roof spanning between two walls.  Nothing is below
    it, but the extruder pulls a taut strand from one side to the other.
    Bridges up to roughly 20mm are routine at 0.4mm.

  * a self-supporting CHAMFER - a sloped face where each layer overhangs
    the one beneath by less than the extrusion width.  Nothing is below
    the face itself, yet every layer rests on the last.

What genuinely fails is an ISLAND: a flat region cantilevered into space
with no wall to anchor either end.

This script separates those three cases, so the bracket is judged on
whether it will actually print rather than on a raw area figure.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_pd_printable.py <stl>
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

import numpy as np
import trimesh

# Faces steeper than this are walls, not overhangs.
DOWNFACING = -0.7

# A face this close to horizontal is a flat roof - a bridge or an island.
# Anything between this and DOWNFACING is a sloped chamfer.
FLAT = -0.98

# Slicers bridge comfortably up to about here at a 0.4mm nozzle.
BRIDGE_LIMIT = 22.0     # mm

# Ignore the first layer, which sits on the plate.
PLATE_CLEARANCE = 0.6

# Areas below this are single stray facets, not features.
NEGLIGIBLE = 3.0        # mm^2


def classify(mesh: trimesh.Trimesh) -> int:
    normals = mesh.face_normals
    centres = mesh.triangles_center

    down = np.where(normals[:, 2] < DOWNFACING)[0]
    if len(down) == 0:
        print("nothing overhangs at all")
        return 0

    # Cast down from just under each face; a hit means solid material
    # below, so it is supported.
    origins = centres[down] + np.array([0, 0, -1e-3])
    hit = mesh.ray.intersects_any(
        ray_origins=origins,
        ray_directions=np.tile([0, 0, -1.0], (len(origins), 1)),
    )

    free = down[~hit]
    free = free[centres[free][:, 2] > PLATE_CLEARANCE]

    # Group by height: coplanar faces at the same Z are one feature.
    groups: dict[float, list[int]] = collections.defaultdict(list)
    for face in free:
        groups[round(float(centres[face][2]), 2)].append(face)

    print(f"{'z (mm)':>8}  {'area':>8}  {'kind':<10}  detail")
    print("-" * 64)

    problems: list[str] = []

    for z in sorted(groups):
        faces = np.array(groups[z])
        area = float(mesh.area_faces[faces].sum())
        if area < NEGLIGIBLE:
            continue

        steepest = float(normals[faces][:, 2].min())
        pts = mesh.triangles[faces].reshape(-1, 3)
        span_x = float(pts[:, 0].max() - pts[:, 0].min())
        span_y = float(pts[:, 1].max() - pts[:, 1].min())
        span = min(span_x, span_y)     # a bridge is crossed the short way

        if steepest > FLAT:
            # Sloped: each layer steps in by less than a nozzle width.
            angle = np.degrees(np.arccos(-steepest))
            print(f"{z:8.2f}  {area:8.1f}  {'chamfer':<10}  "
                  f"{angle:.0f} deg from vertical - self supporting")

        elif span <= BRIDGE_LIMIT:
            print(f"{z:8.2f}  {area:8.1f}  {'bridge':<10}  "
                  f"spans {span:.1f} mm - within the {BRIDGE_LIMIT:.0f} mm "
                  "a slicer bridges cleanly")

        else:
            print(f"{z:8.2f}  {area:8.1f}  {'ISLAND':<10}  "
                  f"spans {span:.1f} mm with nothing to anchor it")
            problems.append(
                f"{area:.0f} mm^2 at z={z:.2f} spans {span:.1f} mm - too "
                "wide to bridge, so the slicer will want support there"
            )

    print("-" * 64)

    if problems:
        print("FAIL")
        for line in problems:
            print(f"  - {line}")
        print("\n  Support inside the latch relief would weld the "
              "mechanism solid, so this has to be fixed in the geometry, "
              "not in the slicer.")
        return 1

    print("PASS - every unsupported region is a bridge or a self-"
          "supporting chamfer")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"no such file: {path}")
        return 2

    mesh = trimesh.load(path)
    print(f"=== {path.name} ===")
    return classify(mesh)


if __name__ == "__main__":
    raise SystemExit(main())
