"""Sweep belt clips onto the ProClip plates' bridge.

The Kenwood TH-D75A is the physically measured article: 21.3mm at the
hinge, 17.6mm at the tip, 4.5mm of gap.  A second tapered article uses
the published 32mm UV-5R replacement-clip envelope, which is an envelope
check and NOT a claim that an unmeasured UV-5R jaw has been verified.

Two injected controls prove the harness sees both independent faults: a
clip whose gap is too small for the bridge, and a clip wider than the
bridge's end stops.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_proclip_clip.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models" / "proclip mounts"
MODEL = MODELS / "proclip_radio_mount.scad"
TMP = ROOT / ".tmp-cad"
OPENSCAD = Path(r"C:\Program Files\OpenSCAD\openscad.exe")

CASES = [("clip", "landscape"), ("clip", "portrait"),
         ("combined", "landscape"), ("combined", "portrait")]

TOUCH_TOL = 5.0
CONTROL_MIN = 20.0


def echo(variant: str, orientation: str) -> str:
    result = subprocess.run(
        [str(OPENSCAD), "-o", str(TMP / "_pcclip_null.stl"),
         "-D", 'variant_render_mode="none"',
         "-D", f'variant="{variant}"',
         "-D", f'amps_orientation="{orientation}"', str(MODEL)],
        capture_output=True, text=True, cwd=ROOT)
    return (result.stdout or "") + "\n" + (result.stderr or "")


def value(text: str, name: str) -> float:
    found = re.findall(rf"(?:^|\s){re.escape(name)}=(-?[0-9.]+)", text)
    if not found:
        raise SystemExit(f"model did not echo {name}")
    return float(found[-1])


def render(tag: str, mode: str, variant: str, orientation: str,
           **values: float) -> trimesh.Trimesh:
    out = TMP / f"pcclip_{tag}.stl"
    out.unlink(missing_ok=True)
    assigns = [f'variant_render_mode = "{mode}";',
               f'variant = "{variant}";',
               f'amps_orientation = "{orientation}";']
    assigns.extend(f"{key} = {val};" for key, val in values.items())
    wrapper = MODELS / f".pcclip_{tag}.scad"
    wrapper.write_text(
        "include <proclip_radio_mount.scad>\n" + "\n".join(assigns) + "\n",
        encoding="utf-8")
    try:
        result = subprocess.run([str(OPENSCAD), "-o", str(out), str(wrapper)],
                                capture_output=True, text=True, cwd=ROOT)
    finally:
        wrapper.unlink(missing_ok=True)
    if not out.exists() or out.stat().st_size < 200:
        sys.stderr.write(((result.stdout or "") + (result.stderr or ""))[-2000:])
        raise SystemExit(f"OpenSCAD produced no {tag}")
    return trimesh.load(out)


def shared(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    try:
        both = a.intersection(b)
    except Exception as exc:
        raise SystemExit(f"boolean intersection failed: {exc}") from exc
    if both is None or both.is_empty:
        return 0.0
    return abs(float(both.volume))


def sweep(body: trimesh.Trimesh, tag: str, variant: str, orientation: str,
          width: float, tip: float, gap: float,
          seated_top: float) -> tuple[float, float]:
    worst = 0.0
    worst_z = seated_top
    for i in range(9):
        z = seated_top + 10.0 - i * 10.0 / 8.0
        clip = render(f"{tag}_{i}", "clip_check", variant, orientation,
                      clip_check_w=width, clip_check_tip_w=tip,
                      clip_check_gap=gap)
        # clip_check_solid takes its top from the model, so shift the
        # rendered article instead of re-parameterising the module.
        clip.apply_translation([0.0, 0.0, z - seated_top])
        collision = shared(body, clip)
        if collision > worst:
            worst, worst_z = collision, z
    return worst, worst_z


def main() -> int:
    if not OPENSCAD.exists():
        raise SystemExit(f"OpenSCAD not found at {OPENSCAD}")
    TMP.mkdir(exist_ok=True)

    text = echo("clip", "landscape")
    bar_t = value(text, "bar_t")
    bar_top = value(text, "bar_top")
    gap = value(text, "kenwood_gap")
    kenwood_w = value(text, "kenwood_w")
    kenwood_tip = value(text, "kenwood_tip")
    generic_w = value(text, "generic_w")
    plate_t_c = value(text, "plate_t_c")
    test_h = value(text, "test_h")

    print("=== belt-clip bridge on the ProClip plates ===")
    print(f"  bridge {bar_t:.2f} mm thick in a measured {gap:.2f} mm gap")
    print(f"  measured closing length below the bar: {test_h:.1f} mm, "
          "fully swept")
    print(f"  bridge 35 mm wide x 25 mm tall, 22.3 mm rails, 33.0 mm stops")
    print()

    failures: list[str] = []

    for variant, orientation in CASES:
        tag = f"{variant}_{orientation}"
        local = echo(variant, orientation)
        top = value(local, "bar_top")
        seated_top = top + plate_t_c + 0.2
        print(f"  {variant.upper()} / {orientation}   bridge top z={top:.2f}")
        body = render(f"body_{tag}", "plate", variant, orientation)

        worst, z = sweep(body, f"kw_{tag}", variant, orientation,
                         kenwood_w, kenwood_tip, gap, seated_top)
        print(f"    Kenwood TH-D75A, 9 poses  : {worst:8.2f} mm^3 "
              f"at top z={z:.2f}")
        if worst > TOUCH_TOL:
            failures.append(
                f"{tag}: the measured Kenwood clip intersects {worst:.1f}mm^3 "
                f"while descending; worst top z={z:.2f}")

        worst, z = sweep(body, f"gen_{tag}", variant, orientation,
                         generic_w, kenwood_tip, gap, seated_top)
        print(f"    32 mm tapered envelope    : {worst:8.2f} mm^3 "
              f"at top z={z:.2f}")
        if worst > TOUCH_TOL:
            failures.append(
                f"{tag}: the 32mm tapered envelope intersects {worst:.1f}mm^3;"
                " the outer compatibility target is not met")

        tight = render(f"tight_{tag}", "clip_check", variant, orientation,
                       clip_check_w=kenwood_w, clip_check_tip_w=kenwood_tip,
                       clip_check_gap=2.5)
        tight_v = shared(body, tight)
        print(f"    (fault) gap cut to 2.5 mm : {tight_v:8.2f} mm^3")
        if tight_v < CONTROL_MIN:
            failures.append(
                f"{tag}: the undersized-gap control produced only "
                f"{tight_v:.1f}mm^3")

        wide = render(f"wide_{tag}", "clip_check", variant, orientation,
                      clip_check_w=40.0, clip_check_tip_w=40.0,
                      clip_check_gap=gap)
        wide_v = shared(body, wide)
        print(f"    (fault) 40 mm square clip : {wide_v:8.2f} mm^3")
        if wide_v < CONTROL_MIN:
            failures.append(
                f"{tag}: the oversized-width control produced only "
                f"{wide_v:.1f}mm^3")
        print()

    if failures:
        print("=== FAIL ===")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("=== PASS ===")
    print("  the measured Kenwood and the 32 mm tapered envelope descend")
    print("  freely; too-small gaps and over-wide clips are rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
