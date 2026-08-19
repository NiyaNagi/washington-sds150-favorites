"""Read-only forensics on models/Slim_Radio_mount.3mf.

Extracts the mesh from the 3MF, reports the bounding box, and prints a
cross-section profile along each axis so the junction plane between the
visor arm ("red" section) and the radio-mounting block ("blue" section)
can be located.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/analyze_mount.py
"""

from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
MOUNT_3MF = ROOT / "models" / "Slim_Radio_mount.3mf"
GEOMETRY_ENTRY = "3D/Objects/object_1.model"


def load_3mf_mesh(path: Path, entry: str) -> trimesh.Trimesh:
    """Load a single-object 3MF payload into a Trimesh."""
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read(entry).decode("utf-8", "replace"))

    vertices = [
        (float(v.get("x")), float(v.get("y")), float(v.get("z")))
        for v in root.iter()
        if v.tag.endswith("}vertex")
    ]
    faces = [
        (int(t.get("v1")), int(t.get("v2")), int(t.get("v3")))
        for t in root.iter()
        if t.tag.endswith("}triangle")
    ]
    return trimesh.Trimesh(
        vertices=np.asarray(vertices, dtype=np.float64),
        faces=np.asarray(faces, dtype=np.int64),
        process=False,
    )


def report_axis_profile(mesh: trimesh.Trimesh, axis: int, step: float = 2.0) -> None:
    """Print the cross-sectional extents of the mesh at slices along an axis."""
    names = "XYZ"
    normal = np.zeros(3)
    normal[axis] = 1.0
    lo, hi = mesh.bounds[0][axis], mesh.bounds[1][axis]

    other = [i for i in range(3) if i != axis]
    print(f"\n=== Cross-sections along {names[axis]} ===")
    print(f"{names[axis]:>8}  {'area':>9}  {names[other[0]]+' extent':>18}  {names[other[1]]+' extent':>18}")

    for position in np.arange(lo + step / 2, hi, step):
        origin = np.zeros(3)
        origin[axis] = position
        section = mesh.section(plane_origin=origin, plane_normal=normal)
        if section is None:
            print(f"{position:8.1f}  {'-':>9}  {'(empty)':>18}  {'':>18}")
            continue

        pts = section.vertices
        a_lo, a_hi = pts[:, other[0]].min(), pts[:, other[0]].max()
        b_lo, b_hi = pts[:, other[1]].min(), pts[:, other[1]].max()
        try:
            planar, _ = section.to_2D()
            area = planar.area
        except Exception:  # noqa: BLE001 - diagnostics only
            area = float("nan")
        print(
            f"{position:8.1f}  {area:9.1f}  "
            f"{a_lo:8.2f}..{a_hi:<8.2f}  {b_lo:8.2f}..{b_hi:<8.2f}"
        )


def main() -> None:
    mesh = load_3mf_mesh(MOUNT_3MF, GEOMETRY_ENTRY)
    print(f"vertices={len(mesh.vertices)} faces={len(mesh.faces)}")
    print(f"watertight={mesh.is_watertight} volume={mesh.volume:.1f} mm^3")
    lo, hi = mesh.bounds
    for i, name in enumerate("XYZ"):
        print(f"{name}: {lo[i]:8.3f} .. {hi[i]:8.3f}   size {hi[i] - lo[i]:7.3f}")

    for axis in range(3):
        report_axis_profile(mesh, axis)


if __name__ == "__main__":
    main()
