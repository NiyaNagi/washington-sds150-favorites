"""Sweep the M6 adjustable head through its complete -45..+45 degree range.

The whole double-sided head rotates.  Positive angles present the SDS150
screen upward; negative angles present the belt-clip radio upward.  Only the
active face is expected to carry a radio at non-zero angles.

Checks:
  * stalk and head never occupy the same solid volume;
  * the active radio clears the fixed stalk at 0/15/30/45 degrees;
  * the active radio's bottom stays above the Peak Design bearing plane;
  * a deliberately lowered head collides, proving the harness.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_radio_standoff_tilt.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models" / "peak design radio standoff"
MODEL = MODELS / "peak_design_radio_standoff.scad"
TMP = ROOT / ".tmp-cad"
OPENSCAD = Path(r"C:\Program Files\OpenSCAD\openscad.exe")
TOUCH_TOL = 2.0
RADIO_TOL = 10.0
CONTROL_MIN = 500.0


def render(name: str, mode: str, out: Path, **values: float) -> trimesh.Trimesh:
    args = [str(OPENSCAD), "-o", str(out), "-D",
            f'variant_render_mode="{mode}"']
    for key, value in values.items():
        args.extend(["-D", f"{key}={value}"])
    args.append(str(MODEL))
    out.unlink(missing_ok=True)
    result = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
    if not out.exists() or out.stat().st_size < 200:
        sys.stderr.write(((result.stdout or "") + (result.stderr or ""))[-2000:])
        raise SystemExit(f"OpenSCAD produced no {name}")
    mesh = trimesh.load(out)
    expected_bodies = 2 if mode == "thd_reference" else 1
    if not mesh.is_watertight or mesh.body_count != expected_bodies:
        raise SystemExit(
            f"{name}: watertight={mesh.is_watertight}, bodies={mesh.body_count}, "
            f"expected={expected_bodies}")
    return mesh


def shared(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    both = a.intersection(b)
    if both is None or both.is_empty:
        return 0.0
    return abs(float(both.volume))


def main() -> int:
    TMP.mkdir(exist_ok=True)
    stalk = render("stalk", "stalk", TMP / "tilt_stalk.stl")
    failures: list[str] = []

    print("=== M6 adjustable-head sweep ===")
    print("  one M6x30 bolt, captive M6 nut, continuous -45..+45 degrees")
    print()
    print("  HEAD AGAINST STALK")
    worst = 0.0
    worst_angle = 0
    for angle in range(-45, 46, 5):
        head = render(f"head_{angle}", "head_positioned",
                      TMP / f"tilt_head_{angle}.stl", head_angle=angle)
        volume = shared(stalk, head)
        if volume > worst:
            worst, worst_angle = volume, angle
    print(f"    worst of 19 positions      : {worst:9.3f} mm^3 at {worst_angle:+d} deg")
    if worst > TOUCH_TOL:
        failures.append(
            f"head intersects stalk by {worst:.2f}mm^3 at {worst_angle:+d} degrees")

    print()
    print("  ACTIVE RADIO CLEARANCE")
    for angle in (0, 15, 30, 45):
        sds = render(f"sds_{angle}", "sds_reference",
                     TMP / f"tilt_sds_{angle}.stl", check_angle=angle)
        collision = shared(stalk, sds)
        bottom = float(sds.bounds[0, 2])
        print(f"    SDS {angle:2d} deg: stalk {collision:7.2f} mm^3, "
              f"bottom z={bottom:6.2f} mm")
        if collision > RADIO_TOL:
            failures.append(f"SDS hits stalk by {collision:.1f}mm^3 at {angle} degrees")
        if bottom < 20.0 - 0.01:
            failures.append(f"SDS bottom is z={bottom:.2f}mm at {angle} degrees")

    for magnitude in (0, 15, 30, 45):
        angle = -magnitude
        radio = render(f"thd_{magnitude}", "thd_reference",
                       TMP / f"tilt_thd_{magnitude}.stl", check_angle=angle)
        collision = shared(stalk, radio)
        bottom = float(radio.bounds[0, 2])
        print(f"    clip {magnitude:2d} deg: stalk {collision:7.2f} mm^3, "
              f"bottom z={bottom:6.2f} mm")
        if collision > RADIO_TOL:
            failures.append(
                f"belt radio hits stalk by {collision:.1f}mm^3 at {angle} degrees")
        if bottom < 0:
            failures.append(
                f"belt radio reaches {abs(bottom):.2f}mm below plate at {angle} degrees")

    print()
    print("  INJECTED-FAULT CONTROL")
    head = render("fault_head", "head_positioned", TMP / "tilt_fault_head.stl",
                  head_angle=0)
    fault = head.copy()
    fault.apply_translation([0.0, 0.0, -15.0])
    fault_v = shared(stalk, fault)
    print(f"    head lowered 15mm          : {fault_v:9.1f} mm^3")
    if fault_v < CONTROL_MIN:
        failures.append(f"lowered-head control produced only {fault_v:.1f}mm^3")

    print()
    if failures:
        print("=== FAIL ===")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("=== PASS ===")
    print("  the joint rotates continuously through every requested angle;")
    print("  the active radio remains above the plate and clear of the stalk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
