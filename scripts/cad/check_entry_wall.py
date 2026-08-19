"""Measure the ledge left around the stud's entry hole.

This is the thinnest place in the bracket and the one the eye lands on
first.  A previous version widened the latch tooth's relief right across
the neck slot to chase away a printing whisker; that put the relief's
inboard corner 26mm from the pivot, so it swung nearly 5mm as the latch
opened and took a visible scallop out of the entry hole - down to a 0.2mm
ledge on one side.

The model now asserts the clearance, but the assert works from the
model's own arithmetic, and it was that arithmetic which was wrong before.
This measures the finished mesh instead.

It walks around the entry hole and reports how far the solid ledge
extends radially at each angle, so a bite out of one side shows up as a
dip rather than being averaged away.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_entry_wall.py [stl]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models"
TMP = ROOT / ".tmp-cad"

OPENSCAD_CANDIDATES = [
    Path(r"C:\Program Files\OpenSCAD\openscad.exe"),
    Path("/usr/bin/openscad"),
    Path("/usr/local/bin/openscad"),
]

# The ledge is what the stud's head pulls against, so it carries the
# radio.  Three extrusion widths is the least worth printing.
MIN_LEDGE = 1.2


def find_openscad() -> Path:
    for path in OPENSCAD_CANDIDATES:
        if path.exists():
            return path
    raise SystemExit("OpenSCAD not found - install it or edit OPENSCAD_CANDIDATES")


def echoed_values(openscad: Path) -> dict[str, float]:
    scad = MODELS / ".entry_probe.scad"
    scad.write_text(
        'include <sds150_pd_bracket.scad>\n'
        'variant_render_mode = "none";\n'
        'echo(str("PROBE",'
        '" travel=", travel,'
        '" entry_d=", entry_d,'
        '" neck_w=", neck_w,'
        '" ledge_t=", ledge_t,'
        '" plate_t=", plate_t));\n',
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [str(openscad), "-o", str(TMP / "entry_probe.stl"), str(scad)],
            capture_output=True, text=True,
        )
    finally:
        scad.unlink(missing_ok=True)

    text = (result.stderr or "") + (result.stdout or "")
    line = next((l for l in text.splitlines() if "PROBE" in l), None)
    if line is None:
        raise SystemExit("could not read the model's derived values")

    vals: dict[str, float] = {}
    for token in line.replace('"', "").split():
        if "=" in token:
            key, _, value = token.partition("=")
            try:
                vals[key] = float(value)
            except ValueError:
                pass
    return vals


def ledge_reach(mesh: trimesh.Trimesh, cx: float, cy: float, z: float,
                r0: float, r_max: float, angle: float,
                step: float = 0.05) -> float:
    """How far the solid ledge extends outward from the hole, at one angle.

    Measures the FIRST continuous run of solid starting at the hole's rim.
    Stopping at the first gap is the point: a relief that has swung across
    and cut a slot leaves solid beyond it, and a test that simply totalled
    the material along the ray would count that far side and report a
    healthy wall across a hole.
    """
    ux, uy = np.cos(np.radians(angle)), np.sin(np.radians(angle))
    rs = np.arange(r0, r_max, step)
    pts = np.column_stack([cx + ux * rs, cy + uy * rs, np.full_like(rs, z)])
    inside = mesh.contains(pts)

    if not inside[0]:
        return 0.0
    first_gap = np.argmax(~inside) if (~inside).any() else len(inside)
    return float(first_gap * step)


def main() -> int:
    openscad = find_openscad()
    TMP.mkdir(exist_ok=True)

    stl = (Path(sys.argv[1]) if len(sys.argv) > 1
           else MODELS / "sds150_pd_bracket_self_tap.stl")
    if not stl.exists():
        raise SystemExit(f"no such file: {stl}")

    v = echoed_values(openscad)
    mesh = trimesh.load(stl)

    travel = v["travel"]
    r_hole = v["entry_d"] / 2
    # Mid-height of the LEDGE - the front layer, from the face to ledge_t,
    # which is what the stud's head catches behind.
    #
    # Not mid-plate: the head channel sits behind the ledge and is void all
    # the way from the entry hole down to the locked stud, so a probe at
    # mid-plate reads zero over that whole span and says nothing about the
    # wall.
    z = v["ledge_t"] / 2

    print(f"=== {stl.name} ===")
    print(f"  entry hole r={r_hole:.2f} at y={travel:.1f}, "
          f"probing the ledge at z={z:.2f}")

    # The neck slot leaves the hole downward, and it is void there by
    # design.  Its angular width is set by how wide the slot is against how
    # big the hole is - derived, not guessed: a hand-picked window of
    # 245-295 deg was 5 deg too narrow at each end and reported the slot's
    # own mouth as a missing wall.
    slot_half = np.degrees(np.arcsin(min(1.0, (v["neck_w"] / 2) / r_hole)))
    slot_lo, slot_hi = 270.0 - slot_half - 2.0, 270.0 + slot_half + 2.0

    print(f"  neck slot leaves the hole between {slot_lo:.0f} and "
          f"{slot_hi:.0f} deg - void by design, not measured")
    print()
    print("  angle    ledge      (0 deg = +X, 90 = up toward the screw)")

    worst, worst_angle = None, None
    for angle in range(0, 360, 5):
        reach = ledge_reach(mesh, 0.0, travel, z, r_hole + 0.02, r_hole + 14.0,
                            angle)
        slot = slot_lo <= angle <= slot_hi
        flag = "  (neck slot)" if slot else ""
        if angle % 15 == 0 or (not slot and reach < MIN_LEDGE):
            print(f"  {angle:5d}   {reach:6.2f} mm{flag}")
        if not slot and (worst is None or reach < worst):
            worst, worst_angle = reach, angle

    print()
    print(f"  thinnest ledge outside the slot: {worst:.2f} mm at "
          f"{worst_angle} deg")

    if worst < MIN_LEDGE:
        print()
        print(f"FAIL - {worst:.2f}mm of ledge at {worst_angle} deg is below "
              f"the {MIN_LEDGE}mm minimum.  Something is cutting into the "
              f"entry hole - most likely the latch tooth's swept relief.")
        return 1

    print()
    print("PASS - the entry hole has a sound ledge all the way round")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
