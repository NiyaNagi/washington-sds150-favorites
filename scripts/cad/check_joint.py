"""Check the join between the visor clamp and the new block.

The block is grown off the top of the clamp's upper jaw.  If its footprint
does not match the clamp's outline at that height, the walls do not line
up and the join shows as a step or a thin overhanging lip running down
each side of the part - obvious once sliced, and a place for the print to
delaminate.

This scans down each side wall through the join and reports any dip or
step between neighbouring heights.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_joint.py <stl>
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import trimesh

# A step smaller than this is finer than the printer can resolve.
TOLERANCE = 0.10


def wall_profile(mesh: trimesh.Trimesh, axis: int, sign: int,
                 heights: np.ndarray) -> list[float]:
    """Outermost surface position along `axis` at each height."""
    lo, hi = mesh.bounds
    other = 1 - axis
    samples = np.arange(lo[other] + 4, hi[other] - 4, 2.0)

    profile = []
    for z in heights:
        far = hi[axis] + 20 if sign > 0 else lo[axis] - 20
        direction = np.zeros(3)
        direction[axis] = -sign

        best = []
        for s in samples:
            origin = np.zeros(3)
            origin[axis] = far
            origin[other] = s
            origin[2] = z
            hits = mesh.ray.intersects_location([origin], [direction])[0]
            if len(hits):
                best.append(hits[:, axis].max() if sign > 0
                            else hits[:, axis].min())
        profile.append(max(best) * sign if best else np.nan)
    return profile


def main() -> None:
    stl = Path(sys.argv[1])
    mesh = trimesh.load(stl)
    lo, hi = mesh.bounds
    print(f"=== {stl.name} ===")

    # Exports are print-oriented, so the clamp/block join runs up what is
    # now the Z axis of the part.  Scan the two long side walls.
    heights = np.arange(lo[2] + 2, hi[2] - 2, 0.5)

    problems = []
    for axis, sign, label in ((1, 1, "+Y side"), (1, -1, "-Y side")):
        profile = wall_profile(mesh, axis, sign, heights)
        print(f"\n  {label}:")

        worst = 0.0
        worst_z = np.nan
        for i in range(1, len(profile)):
            if np.isnan(profile[i]) or np.isnan(profile[i - 1]):
                continue
            step = abs(profile[i] - profile[i - 1])
            if step > worst:
                worst, worst_z = step, heights[i]

        print(f"    largest step between adjacent heights = {worst:.3f} mm"
              f" at Z = {worst_z:.1f}")
        if worst > TOLERANCE:
            problems.append(f"{label}: {worst:.3f} mm step at Z = {worst_z:.1f}")

    if problems:
        print("\n  PROBLEMS:")
        for line in problems:
            print(f"    - {line}")
        sys.exit(1)

    print("\n  side walls are continuous through the join")


if __name__ == "__main__":
    main()
