"""Draw cutaway cross-sections of a rendered mount STL.

Slices along the keyhole slot and across it, so the ledge, head channel,
sprung tongue and detent bump can be checked before printing.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/section_stl.py <stl> <out.png> [axis]
        axis: 0 = cut on X (default), 1 = cut on Y
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.collections import LineCollection


def draw_section(ax, mesh, axis: int, position: float) -> None:
    names = "XYZ"
    normal = np.zeros(3)
    normal[axis] = 1.0
    origin = np.zeros(3)
    origin[axis] = position

    section = mesh.section(plane_origin=origin, plane_normal=normal)
    other = [i for i in range(3) if i != axis]

    if section is not None:
        verts = section.vertices[:, other]
        segments = [verts[entity.points] for entity in section.entities]
        ax.add_collection(LineCollection(segments, linewidths=1.1, colors="crimson"))

    ax.autoscale()
    ax.set_aspect("equal")
    ax.set_title(f"cut {names[axis]} = {position:.1f}")
    ax.set_xlabel(names[other[0]])
    ax.set_ylabel(names[other[1]])
    ax.grid(True, linewidth=0.3, alpha=0.6)


def main() -> None:
    stl = Path(sys.argv[1])
    out = Path(sys.argv[2])
    axis = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    mesh = trimesh.load(stl)
    positions = [0.0, 3.0, 5.0, 7.0, 9.0, -6.0]

    fig, axes = plt.subplots(2, 3, figsize=(19, 12))
    for ax, position in zip(axes.ravel(), positions):
        draw_section(ax, mesh, axis, position)

    fig.tight_layout()
    fig.savefig(out, dpi=110)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
