"""Audit the exported standoff where the Peak Design plate and screw act.

The model asserts its own dimensions; this script checks the rendered mesh.
It verifies all three socket styles share one 39mm external base, that a real
1/4-inch screw path reaches the intended depth, that a shifted path hits solid
material, and that every variant remains one watertight body.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/audit_radio_standoff.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models" / "peak design radio standoff"
TMP = ROOT / ".tmp-cad"
OPENSCAD = Path(r"C:\Program Files\OpenSCAD\openscad.exe")

STYLES = {
    "self_tap": 8.25,
    "insert": 6.00,
    "nut": 5.60,
}
BASE_SIZE = 39.0
BOUND_TOL = 0.03
CLEAR_TOL = 2.0
CONTROL_MIN = 80.0


def render(style: str) -> trimesh.Trimesh:
    wrapper = MODELS / f".standoff_audit_{style}.scad"
    out = TMP / f"standoff_audit_{style}.stl"
    wrapper.write_text(
        "include <peak_design_radio_standoff.scad>\n"
        f'thread_style = "{style}";\n'
        'variant_render_mode = "stalk";\n',
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [str(OPENSCAD), "-o", str(out), str(wrapper)],
            capture_output=True, text=True, cwd=ROOT,
        )
    finally:
        wrapper.unlink(missing_ok=True)
    if not out.exists() or out.stat().st_size < 200:
        sys.stderr.write(((result.stdout or "") + (result.stderr or ""))[-2000:])
        raise SystemExit(f"OpenSCAD produced no {style} standoff")
    return trimesh.load(out)


def cylinder(diameter: float, height: float, x: float = 0.0) -> trimesh.Trimesh:
    probe = trimesh.creation.cylinder(radius=diameter / 2.0, height=height,
                                      sections=64)
    probe.apply_translation([x, 0.0, height / 2.0])
    return probe


def shared(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    both = a.intersection(b)
    if both is None or both.is_empty:
        return 0.0
    return abs(float(both.volume))


def main() -> int:
    TMP.mkdir(exist_ok=True)
    failures: list[str] = []
    meshes: dict[str, trimesh.Trimesh] = {}

    print("=== Peak Design standoff interface audit ===")
    for style, depth in STYLES.items():
        mesh = render(style)
        meshes[style] = mesh
        dims = mesh.bounds[1] - mesh.bounds[0]
        base_vertices = mesh.vertices[mesh.vertices[:, 2] <= 0.05]
        base_span = np.ptp(base_vertices[:, :2], axis=0) if len(base_vertices) else np.zeros(2)

        print()
        print(f"  {style.upper()}")
        print(f"    topology                   : watertight={mesh.is_watertight}, "
              f"bodies={mesh.body_count}, broken={len(trimesh.repair.broken_faces(mesh))}")
        print(f"    full bounds                : {dims[0]:.2f} x {dims[1]:.2f} x {dims[2]:.2f} mm")
        print(f"    bearing-face span          : {base_span[0]:.2f} x {base_span[1]:.2f} mm")

        if not mesh.is_watertight or mesh.body_count != 1:
            failures.append(f"{style} is not one watertight body")
        if abs(base_span[0] - BASE_SIZE) > BOUND_TOL or abs(base_span[1] - BASE_SIZE) > BOUND_TOL:
            failures.append(
                f"{style} bearing face is {base_span[0]:.2f}x{base_span[1]:.2f}, "
                f"not {BASE_SIZE:.1f}x{BASE_SIZE:.1f}")

        clear_probe = cylinder(4.8, depth - 0.2)
        clear_v = shared(mesh, clear_probe)
        print(f"    4.8mm screw-path probe     : {clear_v:8.2f} mm^3")
        if clear_v > CLEAR_TOL:
            failures.append(
                f"{style} blocks {clear_v:.1f}mm^3 of the centered screw path")

        shifted = cylinder(4.8, depth - 0.2, x=8.5)
        shifted_v = shared(mesh, shifted)
        print(f"    shifted-path control       : {shifted_v:8.2f} mm^3")
        if shifted_v < CONTROL_MIN:
            failures.append(
                f"{style} shifted control only found {shifted_v:.1f}mm^3")

    print()
    print("  COMMON EXTERNAL ENVELOPE")
    bounds = [mesh.bounds for mesh in meshes.values()]
    spread = max(float(np.abs(a - bounds[0]).max()) for a in bounds[1:])
    print(f"    maximum bounds difference  : {spread:.5f} mm")
    if spread > 0.001:
        failures.append(f"socket variants differ externally by {spread:.4f}mm")

    print()
    if failures:
        print("=== FAIL ===")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("=== PASS ===")
    print("  all socket styles share one full 39mm bearing footprint and clear screw path")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
