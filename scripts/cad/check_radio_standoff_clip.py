"""Sweep measured and conservative belt clips over the standoff bridge.

The Kenwood TH-D75A is the physically measured article.  Its 21.3mm hinge
narrows to 17.6mm and has 4.5mm of gap.  A second tapered article uses the
published 32mm UV-5R replacement-clip envelope; that is an envelope check,
not a claim that an unmeasured UV-5R jaw has been verified.

Two injected controls prove the harness can see both independent faults:
a clip whose gap is too small for the bar, and a constant-width 32mm plate
that cannot pass the centering funnel.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_radio_standoff_clip.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models" / "peak design radio standoff"
MODEL = MODELS / "peak_design_radio_standoff.scad"
TMP = ROOT / ".tmp-cad"
OPENSCAD = Path(r"C:\Program Files\OpenSCAD\openscad.exe")

TOUCH_TOL = 5.0
CONTROL_MIN = 20.0


def echo_text() -> str:
    result = subprocess.run(
        [str(OPENSCAD), "-o", str(TMP / "_clip_null.stl"),
         "-D", 'variant_render_mode="none"', str(MODEL)],
        capture_output=True, text=True, cwd=ROOT,
    )
    return (result.stdout or "") + "\n" + (result.stderr or "")


def value(text: str, name: str) -> float:
    found = re.findall(rf"(?:^|\s){re.escape(name)}=(-?[0-9.]+)", text)
    if not found:
        raise SystemExit(f"model did not echo {name}")
    return float(found[-1])


def render(name: str, mode: str, out: Path, **values: float) -> trimesh.Trimesh:
    wrapper = MODELS / f".standoff_clip_{name}.scad"
    assigns = [f'variant_render_mode = "{mode}";']
    assigns.extend(f"{key} = {val};" for key, val in values.items())
    wrapper.write_text(
        "include <peak_design_radio_standoff.scad>\n"
        + "\n".join(assigns) + "\n",
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


def sweep(body: trimesh.Trimesh, label: str, width: float, tip: float,
          gap: float, top: float) -> tuple[float, float]:
    worst = 0.0
    worst_z = top + 10.0
    for i in range(9):
        z = top + 10.0 - i * 10.0 / 8.0
        clip = render(
            f"{label}_{i}", "clip_check", TMP / f"clip_{label}_{i}.stl",
            clip_check_w=width, clip_check_tip_w=tip,
            clip_check_gap=gap, clip_check_top_z=z,
        )
        collision = shared(body, clip)
        if collision > worst:
            worst, worst_z = collision, z
    return worst, worst_z


def main() -> int:
    if not OPENSCAD.exists():
        raise SystemExit(f"OpenSCAD not found at {OPENSCAD}")
    TMP.mkdir(exist_ok=True)
    text = echo_text()
    bar_t = value(text, "bar_t")
    bar_top = value(text, "bar_top")
    kenwood_w = value(text, "kenwood_w")
    kenwood_tip = value(text, "kenwood_tip")
    gap = value(text, "kenwood_gap")
    generic_w = value(text, "generic_w")
    lead_r = value(text, "lead_r")
    plate_t = value(text, "plate_t")

    body = render("body", "body", TMP / "clip_fit_body.stl")
    failures: list[str] = []

    print("=== belt-clip bridge fit ===")
    print(f"  bridge thickness {bar_t:.2f} mm, measured Kenwood gap {gap:.2f} mm")
    print("  two-stage lateral funnel: 33.0mm at top -> 22.3mm at bottom")
    print()

    print("  KENWOOD TH-D75A - PHYSICALLY MEASURED")
    seated_top = bar_top + lead_r + plate_t + 0.2
    worst, z = sweep(body, "kenwood", kenwood_w, kenwood_tip, gap,
                     seated_top)
    print(f"    worst of 9 insertion poses : {worst:8.2f} mm^3 at top z={z:.2f}")
    if worst > TOUCH_TOL:
        failures.append(
            f"the measured Kenwood clip intersects {worst:.1f}mm^3 while "
            f"descending; worst top z={z:.2f}")

    print()
    print("  UV-5R PUBLISHED ENVELOPE - TAPERED CONSERVATIVE ARTICLE")
    worst, z = sweep(body, "generic", generic_w, kenwood_tip, gap,
                     seated_top)
    print(f"    worst of 9 insertion poses : {worst:8.2f} mm^3 at top z={z:.2f}")
    if worst > TOUCH_TOL:
        failures.append(
            f"the 32mm tapered envelope intersects {worst:.1f}mm^3; the "
            "outer compatibility target is not met")

    print()
    print("  INJECTED-FAULT CONTROLS")
    tight = render(
        "tight_gap", "clip_check", TMP / "clip_tight_gap.stl",
        clip_check_w=kenwood_w, clip_check_tip_w=kenwood_tip,
        clip_check_gap=2.5, clip_check_top_z=seated_top,
    )
    tight_v = shared(body, tight)
    print(f"    gap reduced to 2.5mm       : {tight_v:8.2f} mm^3")
    if tight_v < CONTROL_MIN:
        failures.append(
            f"the undersized-gap control only produced {tight_v:.1f}mm^3")

    square = render(
        "square_32", "clip_check", TMP / "clip_square_32.stl",
        clip_check_w=generic_w, clip_check_tip_w=generic_w,
        clip_check_gap=gap, clip_check_top_z=seated_top,
    )
    square_v = shared(body, square)
    print(f"    non-tapered 32mm clip      : {square_v:8.2f} mm^3")
    if square_v < CONTROL_MIN:
        failures.append(
            f"the non-tapered wide control only produced {square_v:.1f}mm^3")

    print()
    if failures:
        print("=== FAIL ===")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("=== PASS ===")
    print("  the measured Kenwood and tapered 32mm envelope descend freely;")
    print("  too-small gaps and non-tapered wide clips are both rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
