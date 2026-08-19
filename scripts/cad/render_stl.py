"""Render an STL to shaded PNG views for visual inspection.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/render_stl.py <stl> [<out.png>]
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

VIEWS = [
    ("iso top", 28, -60),
    ("iso other side", 28, 120),
    ("top down (radio side)", 89, -90),
    ("front", 2, -90),
    ("side", 2, 0),
    ("underside", -40, -60),
]


def add_mesh(ax, mesh) -> None:
    tris = mesh.vertices[mesh.faces]
    light = np.array([0.35, -0.55, 0.75])
    light /= np.linalg.norm(light)
    shade = 0.30 + 0.70 * np.clip(mesh.face_normals @ light, 0, 1)
    colors = np.stack(
        [shade * 0.55, shade * 0.70, shade * 0.95, np.ones_like(shade)], axis=1
    )
    ax.add_collection3d(Poly3DCollection(tris, facecolors=colors, edgecolors="none"))

    lo, hi = mesh.bounds
    center = (lo + hi) / 2
    radius = (hi - lo).max() / 2
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)
    ax.set_box_aspect((1, 1, 1))


def main() -> None:
    stl = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else stl.with_suffix(".png")

    mesh = trimesh.load(stl)
    lo, hi = mesh.bounds
    print(f"{stl.name}: faces={len(mesh.faces)} watertight={mesh.is_watertight}")
    print(f"  volume={mesh.volume:.1f} mm^3  bodies={mesh.body_count}")
    for i, name in enumerate("XYZ"):
        print(f"  {name}: {lo[i]:8.2f} .. {hi[i]:8.2f}   size {hi[i] - lo[i]:7.2f}")

    fig = plt.figure(figsize=(18, 11))
    for index, (title, elev, azim) in enumerate(VIEWS, start=1):
        ax = fig.add_subplot(2, 3, index, projection="3d")
        add_mesh(ax, mesh)
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(title)
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")

    fig.tight_layout()
    fig.savefig(out, dpi=100)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
