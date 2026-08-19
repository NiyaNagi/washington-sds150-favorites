"""Find regions that would print in mid-air, for a given orientation.

A printed-in-place lever is only manufacturable if the void it flexes into
is a VERTICAL slot at print time.  Lay the part flat and that void becomes
a horizontal gap with the arm hovering over it - the slicer then reports
floating regions and the arm needs support, which would weld it solid.

This samples downward-facing surfaces and reports any that have nothing
beneath them, for each candidate orientation.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_printable.py <stl>
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import trimesh

# Surfaces steeper than this are walls, not overhangs.
DOWNFACING = -0.7
# Ignore the first layer or two: those sit on the plate.
PLATE_CLEARANCE = 0.6

ORIENTATIONS = {
    "as modelled (Z up)": (0, 0, 0),
    "on its side (X up)": (0, 90, 0),
    "on its side (Y up)": (90, 0, 0),
    "on its back": (180, 0, 0),
}


def floating_area(mesh: trimesh.Trimesh) -> tuple[float, float]:
    """Total downfacing area with nothing below it, and its lowest point."""
    normals = mesh.face_normals
    centres = mesh.triangles_center

    down = normals[:, 2] < DOWNFACING
    if not down.any():
        return 0.0, float("nan")

    origins = centres[down] + np.array([0, 0, -1e-3])
    hits = mesh.ray.intersects_any(origins, np.tile([0, 0, -1.0], (len(origins), 1)))

    above_plate = origins[:, 2] > mesh.bounds[0][2] + PLATE_CLEARANCE
    unsupported = ~hits & above_plate

    area = mesh.area_faces[down][unsupported].sum()
    lowest = origins[unsupported][:, 2].min() if unsupported.any() else float("nan")
    return float(area), float(lowest)


def main() -> None:
    stl = Path(sys.argv[1])
    base = trimesh.load(stl)
    print(f"=== {stl.name} ===")

    for label, (rx, ry, rz) in ORIENTATIONS.items():
        mesh = base.copy()
        for angle, axis in ((rx, [1, 0, 0]), (ry, [0, 1, 0]), (rz, [0, 0, 1])):
            if angle:
                mesh.apply_transform(
                    trimesh.transformations.rotation_matrix(np.radians(angle), axis)
                )
        mesh.apply_translation([0, 0, -mesh.bounds[0][2]])

        area, lowest = floating_area(mesh)
        size = mesh.bounds[1] - mesh.bounds[0]
        verdict = "clean" if area < 5.0 else f"{area:7.1f} mm^2 FLOATING"
        print(f"  {label:22s} {size[0]:5.1f} x {size[1]:5.1f} x {size[2]:5.1f} mm   "
              f"{verdict}")
        if area >= 5.0 and not np.isnan(lowest):
            print(f"  {'':22s} lowest unsupported surface at Z = {lowest:.2f} mm")


if __name__ == "__main__":
    main()
