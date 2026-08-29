"""Verify both radios can coexist and be inserted from opposite faces.

The reference radios are deliberately simple conservative envelopes.  This is
not a cosmetic render check: each envelope is rendered separately, intersected
with the standoff and with the other radio, and repeated through the working
insertion strokes.  A translated-radio fault proves the collision harness.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_radio_standoff_assembly.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models" / "peak design radio standoff"
TMP = ROOT / ".tmp-cad"
OPENSCAD = Path(r"C:\Program Files\OpenSCAD\openscad.exe")
TOUCH_TOL = 10.0
CONTROL_MIN = 1000.0


def render(name: str, mode: str, out: Path, **values: float) -> trimesh.Trimesh:
    wrapper = MODELS / f".standoff_assembly_{name}.scad"
    assignments = [f'variant_render_mode = "{mode}";']
    assignments.extend(f"{key} = {value};" for key, value in values.items())
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
    if not mesh.is_watertight:
        raise SystemExit(f"{name} is not watertight")
    return mesh


def shared(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    both = a.intersection(b)
    if both is None or both.is_empty:
        return 0.0
    return abs(float(both.volume))


def shared_structure(parts: list[trimesh.Trimesh], other: trimesh.Trimesh) -> float:
    return sum(shared(part, other) for part in parts)


def main() -> int:
    TMP.mkdir(exist_ok=True)
    stalk = render("stalk", "stalk", TMP / "assembly_stalk.stl")
    head = render("head", "head_neutral", TMP / "assembly_head.stl")
    structure = [stalk, head]
    thd_seated = render("thd_0", "thd_reference", TMP / "assembly_thd_0.stl",
                        clip_check_dz=0.0)
    sds_seated = render("sds_0", "sds_reference", TMP / "assembly_sds_0.stl",
                        check_pos=0.0)

    failures: list[str] = []
    print("=== opposed-face radio assembly ===")
    print(f"  neutral height 160.0mm, stalk+head "
          f"{(stalk.volume + head.volume)/1000:.1f}cm^3")
    print()

    print("  BOTH SEATED")
    for label, volume in (
        ("SDS150 against standoff", shared_structure(structure, sds_seated)),
        ("TH-D75A against standoff", shared_structure(structure, thd_seated)),
        ("radio against radio", shared(sds_seated, thd_seated)),
    ):
        print(f"    {label:28s}: {volume:9.2f} mm^3")
        if volume > TOUCH_TOL:
            failures.append(f"{label} overlaps by {volume:.1f}mm^3")

    print()
    print("  SDS150 INSERTING, BELT RADIO SEATED")
    worst = 0.0
    worst_pos = 0.0
    for i, pos in enumerate((0.0, 4.75, 9.5, 14.25, 19.0)):
        sds = render(f"sds_{i}", "sds_reference",
                     TMP / f"assembly_sds_{i}.stl", check_pos=pos)
        volume = shared(sds, thd_seated)
        body_v = shared_structure(structure, sds)
        total = max(volume, body_v)
        if total > worst:
            worst, worst_pos = total, pos
    print(f"    worst of 5 positions       : {worst:9.2f} mm^3 at {worst_pos:.2f}mm")
    if worst > TOUCH_TOL:
        failures.append(
            f"SDS insertion has {worst:.1f}mm^3 interference at {worst_pos:.2f}mm")

    print()
    print("  BELT RADIO INSERTING, SDS150 SEATED")
    worst = 0.0
    worst_dz = 0.0
    for i, dz in enumerate((0.0, 5.0, 10.0, 15.0, 20.0)):
        thd = render(f"thd_{i}", "thd_reference",
                     TMP / f"assembly_thd_{i}.stl", clip_check_dz=dz)
        volume = shared(thd, sds_seated)
        body_v = shared_structure(structure, thd)
        total = max(volume, body_v)
        if total > worst:
            worst, worst_dz = total, dz
    print(f"    worst of 5 positions       : {worst:9.2f} mm^3 at lift {worst_dz:.1f}mm")
    if worst > TOUCH_TOL:
        failures.append(
            f"belt-radio insertion has {worst:.1f}mm^3 interference at "
            f"lift {worst_dz:.1f}mm")

    print()
    print("  CLEARANCES")
    sds_bottom = float(sds_seated.bounds[0][2])
    thd_bottom = float(thd_seated.bounds[0][2])
    print(f"    SDS150 bottom over plate   : {sds_bottom:9.2f} mm")
    print(f"    belt-radio bottom over plate: {thd_bottom:8.2f} mm")
    if sds_bottom < 20.0 - 0.01:
        failures.append(f"SDS150 bottom clearance is only {sds_bottom:.2f}mm")
    if thd_bottom < 0.0:
        failures.append(f"belt radio reaches {abs(thd_bottom):.2f}mm below the plate")

    print()
    print("  INJECTED-FAULT CONTROL")
    fault = thd_seated.copy()
    fault.apply_translation([0.0, 45.0, 0.0])
    fault_v = shared(fault, sds_seated)
    print(f"    rear radio shifted through spine: {fault_v:8.1f} mm^3")
    if fault_v < CONTROL_MIN:
        failures.append(
            f"translated-radio fault produced only {fault_v:.1f}mm^3")

    print()
    if failures:
        print("=== FAIL ===")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("=== PASS ===")
    print("  both radios seat and insert independently on opposite faces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
