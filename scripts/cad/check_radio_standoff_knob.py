"""Verify the large M6 finger knobs positively drive their screw heads.

A round socket/button cap in a round printed cup can slip independently of the
knob.  Each knob therefore has a male printed hex that enters the screw's Allen
recess.  This harness assembles a separate cap-head solid with the matching hex
socket, expects zero interference, then replaces it with a deliberately solid
cap and requires the post to collide.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_radio_standoff_knob.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "models" / "peak design radio standoff" / "peak_design_radio_standoff.scad"
TMP = ROOT / ".tmp-cad"
OPENSCAD = Path(r"C:\Program Files\OpenSCAD\openscad.exe")
TOUCH_TOL = 1.0
CONTROL_MIN = 20.0
KNOB_T = 15.0

STYLES = {
    # style: head diameter, head height, Allen AF
    "button_4mm": (11.0, 3.5, 4.0),
    "socket_5mm": (10.2, 6.2, 5.0),
}


def render(style: str) -> trimesh.Trimesh:
    out = TMP / f"knob_{style}.stl"
    result = subprocess.run(
        [str(OPENSCAD), "-o", str(out),
         "-D", 'variant_render_mode="knob"',
         "-D", f'knob_style="{style}"', str(MODEL)],
        capture_output=True, text=True, cwd=ROOT,
    )
    if not out.exists() or out.stat().st_size < 200:
        sys.stderr.write(((result.stdout or "") + (result.stderr or ""))[-2000:])
        raise SystemExit(f"OpenSCAD produced no {style} knob")
    return trimesh.load(out)


def cap_head(diameter: float, height: float, hex_af: float,
             socket: bool) -> trimesh.Trimesh:
    head = trimesh.creation.cylinder(radius=diameter / 2, height=height,
                                     sections=64)
    head.apply_translation([0, 0, KNOB_T - height / 2])
    if not socket:
        return head

    # Trimesh's six-sided cylinder is specified by circumradius.  AF is
    # therefore converted to across-corners exactly as in the SCAD model.
    recess = trimesh.creation.cylinder(
        radius=(hex_af + 0.05) / (2 * 0.8660254037844386),
        height=min(3.2, height - 0.3), sections=6,
    )
    recess.apply_translation([0, 0, KNOB_T - height + recess.extents[2] / 2])
    result = head.difference(recess)
    if result is None or result.is_empty:
        raise SystemExit("failed to construct cap-head socket control")
    return result


def shared(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    both = a.intersection(b)
    if both is None or both.is_empty:
        return 0.0
    return abs(float(both.volume))


def main() -> int:
    TMP.mkdir(exist_ok=True)
    failures: list[str] = []
    print("=== M6 high-grip finger knobs ===")

    for style, (head_d, head_h, hex_af) in STYLES.items():
        knob = render(style)
        matching = cap_head(head_d, head_h, hex_af, socket=True)
        solid = cap_head(head_d, head_h, hex_af, socket=False)
        fit = shared(knob, matching)
        control = shared(knob, solid)
        dims = knob.bounds[1] - knob.bounds[0]

        print()
        print(f"  {style}")
        print(f"    knob envelope              : {dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f} mm")
        print(f"    topology                   : watertight={knob.is_watertight}, bodies={knob.body_count}")
        print(f"    matching cap + Allen socket: {fit:8.2f} mm^3")
        print(f"    solid-cap fault control    : {control:8.2f} mm^3")

        if not knob.is_watertight or knob.body_count != 1:
            failures.append(f"{style} knob is not one watertight body")
        if fit > TOUCH_TOL:
            failures.append(f"{style} matching screw head intersects by {fit:.1f}mm^3")
        if control < CONTROL_MIN:
            failures.append(f"{style} solid-cap control only produced {control:.1f}mm^3")

    print()
    if failures:
        print("=== FAIL ===")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("=== PASS ===")
    print("  both caps clear their cups and the printed Allen posts positively drive them")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
