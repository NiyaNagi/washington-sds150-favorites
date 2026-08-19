"""Export the original Slim Radio mount mesh, unmodified, as an STL.

No cutting is done here.  Separating the visor arm from the old mounting
block is left to OpenSCAD, which uses exact arithmetic and does not leave
the sliver triangles that a mesh-library slice produces.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/export_source_mesh.py
"""

from __future__ import annotations

from pathlib import Path

from analyze_mount import MOUNT_3MF, GEOMETRY_ENTRY, load_3mf_mesh

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "models" / "slim_radio_mount_source.stl"


def main() -> None:
    mesh = load_3mf_mesh(MOUNT_3MF, GEOMETRY_ENTRY)

    lo, hi = mesh.bounds
    print(f"faces={len(mesh.faces)} watertight={mesh.is_watertight}")
    print(f"volume={mesh.volume:.1f} mm^3")
    for i, name in enumerate("XYZ"):
        print(f"  {name}: {lo[i]:8.3f} .. {hi[i]:8.3f}   size {hi[i] - lo[i]:7.3f}")

    if not mesh.is_watertight:
        raise SystemExit("source mesh is not watertight - refusing to export")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(OUT)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
