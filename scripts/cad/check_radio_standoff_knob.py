"""Verify the GoPro-style M6 captured-nut knob and fixed hex bolt.

The knob is a nut driver, not a cap-head sleeve. A standard M6 nut slides into
its central hex pocket from one wing. The opposite fork ear captures a standard
M6 hex bolt head, so turning the knob rotates only the nut. Independent solids
prove the insertion path, screw passage, and both anti-rotation hex pockets.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_radio_standoff_knob.py
"""

from __future__ import annotations

import math
import re
import subprocess
import sys
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "models" / "peak design radio standoff" / "peak_design_radio_standoff.scad"
TMP = ROOT / ".tmp-cad"
OPENSCAD = Path(r"C:\Program Files\OpenSCAD\openscad.exe")
TOUCH_TOL = 1.0
CONTROL_MIN = 8.0


def render(mode: str, name: str) -> trimesh.Trimesh:
    out = TMP / f"knob_{name}.stl"
    result = subprocess.run(
        [str(OPENSCAD), "-o", str(out),
         "-D", f'variant_render_mode="{mode}"', str(MODEL)],
        capture_output=True, text=True, cwd=ROOT,
    )
    if not out.exists() or out.stat().st_size < 200:
        sys.stderr.write(((result.stdout or "") + (result.stderr or ""))[-2000:])
        raise SystemExit(f"OpenSCAD produced no {name}")
    return trimesh.load(out)


def model_values() -> dict[str, float]:
    out = TMP / "_knob_echo.stl"
    result = subprocess.run(
        [str(OPENSCAD), "-o", str(out), "-D",
         'variant_render_mode="none"', str(MODEL)],
        capture_output=True, text=True, cwd=ROOT,
    )
    text = (result.stdout or "") + "\n" + (result.stderr or "")

    def value(name: str) -> float:
        hits = re.findall(rf"(?:^|\s){re.escape(name)}=(-?[0-9.]+)", text)
        if not hits:
            raise SystemExit(f"model did not echo {name}")
        return float(hits[-1])

    return {name: value(name) for name in (
        "ref_d", "ref_t", "scale", "tip_d", "thickness", "nut_z0",
        "nut_h", "nut_floor", "back_wall", "nut_af", "nut_t", "bolt_d",
        "bolt_head_af", "bolt_head_h", "bolt_head_x0", "outer_w",
    )}


def hex_ring(af: float, height: float, bore: float) -> trimesh.Trimesh:
    outer = trimesh.creation.cylinder(
        radius=af / (2 * math.cos(math.radians(30))),
        height=height, sections=6,
    )
    hole = trimesh.creation.cylinder(radius=bore / 2, height=height + 0.4,
                                     sections=48)
    ring = outer.difference(hole)
    if ring is None or ring.is_empty:
        raise SystemExit("failed to construct M6 nut reference")
    return ring


def cylinder_x(diameter: float, length: float, x0: float,
               sections: int = 48) -> trimesh.Trimesh:
    mesh = trimesh.creation.cylinder(radius=diameter / 2, height=length,
                                     sections=sections)
    rotation = trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0])
    mesh.apply_transform(rotation)
    mesh.apply_translation([x0 + length / 2, 0, 108.0])
    return mesh


def shared(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    both = a.intersection(b)
    if both is None or both.is_empty:
        return 0.0
    return abs(float(both.volume))


def main() -> int:
    TMP.mkdir(exist_ok=True)
    failures: list[str] = []
    values = model_values()
    knob = render("knob", "captured_nut")
    stalk = render("stalk", "captured_bolt")
    dims = knob.bounds[1] - knob.bounds[0]

    nut = hex_ring(values["nut_af"], values["nut_t"], 6.0)
    nut.apply_translation([0, 0, values["nut_z0"] + values["nut_t"] / 2])
    nut_fit = shared(knob, nut)
    rotated_nut = nut.copy()
    rotated_nut.apply_transform(
        trimesh.transformations.rotation_matrix(math.radians(30), [0, 0, 1]))
    nut_control = shared(knob, rotated_nut)

    insertion_worst = 0.0
    insertion_at = 0.0
    for x in [0, 4, 8, 12, 16, 20, 24, 28, 32, 36]:
        moving = nut.copy()
        moving.apply_translation([x, 0, 0])
        volume = shared(knob, moving)
        if volume > insertion_worst:
            insertion_worst, insertion_at = volume, x

    bore = trimesh.creation.cylinder(radius=3.0,
                                     height=values["thickness"] - values["back_wall"],
                                     sections=48)
    bore.apply_translation([0, 0, values["back_wall"] + bore.extents[2] / 2])
    bore_fit = shared(knob, bore)

    bolt_head = cylinder_x(values["bolt_head_af"] / math.cos(math.radians(30)),
                           values["bolt_head_h"], values["bolt_head_x0"],
                           sections=6)
    bolt_fit = shared(stalk, bolt_head)
    rotated_head = bolt_head.copy()
    rotated_head.apply_transform(trimesh.transformations.rotation_matrix(
        math.radians(30), [1, 0, 0], point=[0, 0, 108.0]))
    bolt_control = shared(stalk, rotated_head)
    shaft = cylinder_x(6.0, 30.0, values["bolt_head_x0"] - 30.0)
    shaft_fit = shared(stalk, shaft)
    nut_x_min = -values["outer_w"] / 2 - values["nut_floor"] - values["nut_h"]
    nut_x_max = nut_x_min + values["nut_t"]
    screw_x_min = values["bolt_head_x0"] - 30.0
    thread_engagement = min(values["bolt_head_x0"], nut_x_max) - max(screw_x_min, nut_x_min)
    thread_protrusion = nut_x_min - screw_x_min

    actual_span = float(max(dims[0], dims[1]))
    target_span = values["ref_d"] * values["scale"]
    print("=== GoPro-style M6 captured-nut knob ===")
    print(f"  reference / scale            : {values['ref_d']:.1f} mm x {values['scale']:.2f}")
    print(f"  knob envelope                : {dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f} mm")
    print(f"  required maximum span        : {target_span:.1f} mm")
    print(f"  topology                     : watertight={knob.is_watertight}, bodies={knob.body_count}")
    print(f"  matching M6 nut              : {nut_fit:8.2f} mm^3")
    print(f"  side insertion worst         : {insertion_worst:8.2f} mm^3 at x={insertion_at:.0f}")
    print(f"  nut rotated 30deg control    : {nut_control:8.2f} mm^3")
    print(f"  M6 screw passage             : {bore_fit:8.2f} mm^3")
    print(f"  matching hex bolt head       : {bolt_fit:8.2f} mm^3")
    print(f"  rotated bolt-head control    : {bolt_control:8.2f} mm^3")
    print(f"  M6x30 shaft passage          : {shaft_fit:8.2f} mm^3")
    print(f"  nut thread engagement        : {thread_engagement:8.2f} mm")
    print(f"  thread beyond nut            : {thread_protrusion:8.2f} mm")

    if not knob.is_watertight or knob.body_count != 1:
        failures.append("knob is not one watertight body")
    if actual_span < target_span - 0.05:
        failures.append(
            f"knob span {actual_span:.2f}mm is below 1.4x target {target_span:.2f}mm")
    for label, volume in (
        ("matching nut", nut_fit), ("nut insertion", insertion_worst),
        ("screw passage", bore_fit), ("matching bolt head", bolt_fit),
        ("M6x30 shaft", shaft_fit),
    ):
        if volume > TOUCH_TOL:
            failures.append(f"{label} intersects by {volume:.1f}mm^3")
    if nut_control < CONTROL_MIN:
        failures.append(f"rotated-nut control only produced {nut_control:.1f}mm^3")
    if bolt_control < CONTROL_MIN:
        failures.append(f"rotated bolt-head control only produced {bolt_control:.1f}mm^3")
    if thread_engagement < values["nut_t"] - 0.05:
        failures.append(
            f"M6x30 engages only {thread_engagement:.2f}mm of the {values['nut_t']:.2f}mm nut")
    if thread_protrusion < 1.0:
        failures.append(f"M6x30 extends only {thread_protrusion:.2f}mm beyond the nut")

    print()
    if failures:
        print("=== FAIL ===")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("=== PASS ===")
    print("  the knob captures and drives the M6 nut; the fork captures the hex bolt head")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
