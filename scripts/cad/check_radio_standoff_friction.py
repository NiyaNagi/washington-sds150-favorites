"""Validate the standoff's replaceable continuous-angle friction washers.

Concentric rings were rotationally symmetric and therefore could not key torque.
The replacement is a pair of keyed 95A-TPU/rubber annular washers recessed into
the moving head. This harness proves their mesh fit, keyed anti-rotation flats,
loose-joint clearance through -45..+45 degrees, and conservative clamp capacity.

The coefficient of friction is still material- and print-dependent, so the
physical joint coupon remains the final acceptance test.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_radio_standoff_friction.py
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
FLAT_CONTROL_MIN = 0.5
TPU_PLA_MU = 0.30       # conservative design assumption; confirm by coupon
PLA_PLA_MU = 0.18       # prior smooth-face assumption
M6_CLAMP_TARGET = 500.0    # realistic finger-tight preload with 50.4mm knob
RADIO_MASS_KG = 0.400
RADIO_ARM_MM = 40.0
G = 9.80665


def render(name: str, mode: str, **values: float) -> trimesh.Trimesh:
    out = TMP / f"friction_{name}.stl"
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
    if not mesh.is_watertight:
        raise SystemExit(f"{name} is not watertight")
    return mesh


def model_values() -> dict[str, float]:
    out = TMP / "_friction_echo.stl"
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
        "washer_od", "washer_id", "washer_t", "recess_d", "loose_clr",
        "r", "bolt_d",
    )}


def shared(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    both = a.intersection(b)
    if both is None or both.is_empty:
        return 0.0
    return abs(float(both.volume))


def main() -> int:
    TMP.mkdir(exist_ok=True)
    values = model_values()
    failures: list[str] = []

    head = render("head", "head_neutral")
    stalk = render("stalk", "stalk")
    washer = render("washer", "friction_washer")
    pair = render("pair_0", "friction_washers_positioned", head_angle=0)

    head_fit = shared(head, pair)
    stalk_fit = shared(stalk, pair)

    rotated = pair.copy()
    rotated.apply_transform(trimesh.transformations.rotation_matrix(
        math.radians(5), [1, 0, 0], point=[0, 0, 108]))
    keyed_control = shared(head, rotated)

    worst = 0.0
    worst_angle = 0
    for angle in range(-45, 46, 5):
        installed = render(f"pair_{angle}", "friction_washers_positioned",
                           head_angle=angle)
        volume = shared(stalk, installed)
        if volume > worst:
            worst, worst_angle = volume, angle

    dimensions = washer.bounds[1] - washer.bounds[0]
    hole_r = values["washer_id"] / 2
    outer_r = values["washer_od"] / 2
    # The washer has two flats, so the full-annulus integral would slightly
    # overstate its radius. The arithmetic mean of inner and outer radii is a
    # deliberately conservative value for this broad truncated annulus.
    effective_r = (outer_r + hole_r) / 2.0
    required_moment = 3 * RADIO_MASS_KG * G * RADIO_ARM_MM
    old_capacity = 2 * PLA_PLA_MU * M6_CLAMP_TARGET * effective_r
    new_capacity = 2 * TPU_PLA_MU * M6_CLAMP_TARGET * effective_r
    required_clamp = required_moment / (2 * TPU_PLA_MU * effective_r)

    print("=== continuous-angle keyed friction washers ===")
    print(f"  single washer envelope       : {dimensions[0]:.1f} x {dimensions[1]:.1f} x {dimensions[2]:.2f} mm")
    print(f"  washer topology              : watertight={washer.is_watertight}, bodies={washer.body_count}")
    print(f"  installed pair topology      : watertight={pair.is_watertight}, bodies={pair.body_count}")
    print(f"  washer against head          : {head_fit:8.3f} mm^3")
    print(f"  washer against loose stalk   : {stalk_fit:8.3f} mm^3")
    print(f"  rotated-flat fault control   : {keyed_control:8.2f} mm^3")
    print(f"  worst stalk clearance sweep  : {worst:8.3f} mm^3 at {worst_angle:+d} deg")
    print()
    print("  CONSERVATIVE CLAMP MODEL")
    print(f"    effective friction radius  : {effective_r:5.2f} mm")
    print(f"    3g radio moment            : {required_moment/1000:5.3f} N m")
    print(f"    clamp required, mu=0.30    : {required_clamp:5.0f} N")
    print(f"    old PLA/PLA at 0.5kN       : {old_capacity/1000:5.2f} N m")
    print(f"    keyed TPU/PLA at 0.5kN     : {new_capacity/1000:5.2f} N m")
    print(f"    3g capacity factor         : {new_capacity/required_moment:5.1f}")

    if washer.body_count != 1:
        failures.append(f"washer has {washer.body_count} bodies instead of one")
    if pair.body_count != 2:
        failures.append(f"installed pair has {pair.body_count} bodies instead of two")
    if abs(dimensions[2] - values["washer_t"]) > 0.02:
        failures.append(
            f"washer mesh is {dimensions[2]:.3f}mm thick, expected {values['washer_t']:.3f}mm")
    if head_fit > TOUCH_TOL:
        failures.append(f"washer pair intersects head by {head_fit:.2f}mm^3")
    if stalk_fit > TOUCH_TOL:
        failures.append(f"washer pair binds loose stalk by {stalk_fit:.2f}mm^3")
    if keyed_control < FLAT_CONTROL_MIN:
        failures.append(
            f"rotated-flat control produced only {keyed_control:.2f}mm^3; flats do not key")
    if worst > TOUCH_TOL:
        failures.append(
            f"washers hit stalk by {worst:.2f}mm^3 at {worst_angle:+d} degrees")
    if new_capacity < 3 * required_moment:
        failures.append("washer joint has less than 3x capacity over the 3g moment")

    print()
    if failures:
        print("=== FAIL ===")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("=== PASS ===")
    print("  keyed compliant washers preserve continuous motion and improve modeled grip")
    print("  physical coupon torque testing is still required for the chosen TPU/rubber")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
