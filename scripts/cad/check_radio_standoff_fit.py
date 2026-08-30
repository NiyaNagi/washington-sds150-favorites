"""Verify the SDS150 gravity keyhole against the standoff as separate solids.

There is intentionally no latch.  The expected behavior is therefore:

* the head drops through the upper entry without touching;
* the stud moves down the whole slot without touching;
* it sits free at the locked end;
* a straight pull away from the face is blocked by a substantial ledge;
* a deliberately oversized stud is detected by the same harness.

The moving stud and the body are rendered separately.  Generating a void and
its mating solid from one boolean can hide the same error in both.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_radio_standoff_fit.py
"""

from __future__ import annotations

import subprocess
import sys
import re
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models" / "peak design radio standoff"
MODEL = MODELS / "peak_design_radio_standoff.scad"
TMP = ROOT / ".tmp-cad"
OPENSCAD = Path(r"C:\Program Files\OpenSCAD\openscad.exe")

TOUCH_TOL = 8.0       # mm^3 of tessellation noise on a large curved interface
BLOCK_MIN = 120.0     # mm^3 means the ledge genuinely blocks pull-out
CONTROL_MIN = 50.0    # deliberately oversized stud must be obvious


def model_values() -> tuple[float, float, float, float]:
    result = subprocess.run(
        [str(OPENSCAD), "-o", str(TMP / "_fit_null.stl"),
         "-D", 'variant_render_mode="none"',
         str(MODELS / "peak_design_radio_standoff.scad")],
        capture_output=True, text=True, cwd=ROOT,
    )
    text = (result.stdout or "") + "\n" + (result.stderr or "")
    match = re.search(r"SDS locked_z=[0-9.]+ entry_z=[0-9.]+ "
                      r"bottom_z=[0-9.]+ travel=([0-9.]+) min=([0-9.]+)", text)
    if not match:
        raise SystemExit("the model did not echo SDS travel and minimum")
    ledge_match = re.search(r"FIT preload=[0-9.]+ slide=[0-9.]+ "
                            r"ledge_t=([0-9.]+) neck_h=([0-9.]+)", text)
    if not ledge_match:
        raise SystemExit("the model did not echo SDS ledge thickness")
    return (float(match.group(1)), float(match.group(2)),
            float(ledge_match.group(1)), float(ledge_match.group(2)))


def render(name: str, mode: str, out: Path, **values: float | str) -> trimesh.Trimesh:
    assignments = [f'variant_render_mode = "{mode}";']
    for key, value in values.items():
        if isinstance(value, str):
            assignments.append(f'{key} = "{value}";')
        else:
            assignments.append(f"{key} = {value};")
    wrapper = MODELS / f".standoff_fit_{name}.scad"
    wrapper.write_text(
        "include <peak_design_radio_standoff.scad>\n"
        + "\n".join(assignments) + "\n",
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
        raise SystemExit(f"OpenSCAD produced no {name}")
    mesh = trimesh.load(out)
    if not mesh.is_watertight or mesh.body_count != 1:
        raise SystemExit(
            f"{name} is not one watertight body "
            f"(watertight={mesh.is_watertight}, bodies={mesh.body_count})")
    return mesh


def shared(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    try:
        both = a.intersection(b)
    except Exception as exc:
        raise SystemExit(f"boolean intersection failed: {exc}") from exc
    if both is None or both.is_empty:
        return 0.0
    return abs(float(both.volume))


def main() -> int:
    if not OPENSCAD.exists():
        raise SystemExit(f"OpenSCAD not found at {OPENSCAD}")
    TMP.mkdir(exist_ok=True)

    travel, minimum, ledge_t, neck_h = model_values()
    axial_free = neck_h - ledge_t
    body = render("head", "head_neutral", TMP / "standoff_fit_head.stl")

    print("=== SDS150 gravity-keyhole fit ===")
    print(f"  head: {body.volume/1000:.1f} cm^3, one watertight solid")
    print(f"  travel: {travel:.2f} mm (mathematical minimum {minimum:.3f} mm)")
    print(f"  ledge: {ledge_t:.3f} mm, intentional axial freedom {axial_free:.3f} mm")
    print()

    failures: list[str] = []

    print("  DROP AND DOWNWARD TRAVEL")
    worst = 0.0
    worst_pos = travel
    for i in range(11):
        pos = travel * (10 - i) / 10.0
        stud = render(f"travel_{i}", "sds_check",
                      TMP / f"standoff_stud_{i}.stl",
                      check_pos=pos, check_lift=0.0, check_extra=0.0)
        volume = shared(body, stud)
        if volume > worst:
            worst, worst_pos = volume, pos
    print(f"    worst of 11 positions      : {worst:8.2f} mm^3 at {worst_pos:.2f} mm")
    if worst > TOUCH_TOL:
        failures.append(
            f"the real stud intersects {worst:.1f}mm^3 at slot position "
            f"{worst_pos:.2f}; it will not drop freely")

    print()
    print("  SEATED AND PULL-OUT")
    seated = render("seated", "sds_check", TMP / "standoff_stud_seated.stl",
                    check_pos=0.0, check_lift=0.0, check_extra=0.0)
    seated_v = shared(body, seated)
    print(f"    seated                    : {seated_v:8.2f} mm^3")
    if seated_v > TOUCH_TOL:
        failures.append(f"the seated stud intersects {seated_v:.1f}mm^3")

    pull_distance = axial_free + 1.5
    pull = render("pull", "sds_check", TMP / "standoff_stud_pull.stl",
                  check_pos=0.0, check_lift=pull_distance, check_extra=0.0)
    pull_v = shared(body, pull)
    print(f"    pulled {pull_distance:.3f}mm outward  : {pull_v:8.2f} mm^3")
    if pull_v < BLOCK_MIN:
        failures.append(
            f"pull-out only meets {pull_v:.1f}mm^3 of ledge; the head is not "
            "substantially captured")

    print()
    print("  INJECTED-FAULT CONTROL")
    fat = render("fat", "sds_check", TMP / "standoff_stud_fat.stl",
                 check_pos=travel / 2, check_lift=0.0, check_extra=3.0)
    fat_v = shared(body, fat)
    print(f"    stud enlarged by 3.0mm    : {fat_v:8.2f} mm^3")
    if fat_v < CONTROL_MIN:
        failures.append(
            f"an oversized stud produced only {fat_v:.1f}mm^3; the harness "
            "cannot detect a fit fault")

    print()
    if failures:
        print("=== FAIL ===")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("=== PASS ===")
    print("  the SDS150 drops freely, seats without interference, and its head is captured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
