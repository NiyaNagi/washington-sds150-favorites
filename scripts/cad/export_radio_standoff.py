"""Export the Peak Design radio standoff and its fit coupons.

Production variants share one outside shape and differ only in the centered
1/4"-20 socket.  Coupons are deliberately separate: print and select the SDS
fit before committing to a 160mm-tall body, then verify the real belt clips on
the cropped rear interface.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/export_radio_standoff.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models" / "peak design radio standoff"
TMP = ROOT / ".tmp-cad"
OPENSCAD = Path(r"C:\Program Files\OpenSCAD\openscad.exe")

PRODUCTION = [
    ("self_tap", "peak_design_radio_standoff_self_tap"),
    ("insert", "peak_design_radio_standoff_insert"),
    ("nut", "peak_design_radio_standoff_nut"),
]

# Exact dimensions live in the SCAD coupon_fit branch.  Keeping only labels
# here prevents a second copy that can drift while still producing files.
SDS_COUPONS = ["easy", "nominal", "firm"]

CLIP_COUPONS = [
    ("thin", 2.8),
    ("nominal", 3.0),
    ("thick", 3.2),
]


def render(name: str, mode: str, fmt: str, **assignments: float | str) -> Path:
    out = MODELS / f"{name}.{fmt}"
    defines = ["-D", f'variant_render_mode="{mode}"']
    for key, value in assignments.items():
        rendered = f'"{value}"' if isinstance(value, str) else str(value)
        defines.extend(["-D", f"{key}={rendered}"])
    out.unlink(missing_ok=True)
    started = time.monotonic()
    result = subprocess.run(
        [str(OPENSCAD), "-o", str(out), *defines,
         str(MODELS / "peak_design_radio_standoff.scad")],
        capture_output=True, text=True, cwd=ROOT,
    )
    elapsed = time.monotonic() - started
    if not out.exists() or out.stat().st_size < 200:
        sys.stderr.write(((result.stdout or "") + (result.stderr or ""))[-2500:])
        raise SystemExit(f"OpenSCAD produced no {out.name}")
    print(f"  {out.name:<47} {elapsed:5.1f}s", end="")
    if fmt == "stl":
        mesh = trimesh.load(out)
        dims = mesh.bounds[1] - mesh.bounds[0]
        if not mesh.is_watertight or mesh.body_count != 1:
            raise SystemExit(
                f"\n{out.name}: watertight={mesh.is_watertight}, "
                f"bodies={mesh.body_count}")
        print(f"  {mesh.volume/1000:6.1f}cm3  "
              f"{dims[0]:.1f}x{dims[1]:.1f}x{dims[2]:.1f}mm  ok")
    else:
        print("  written")
    return out


def main() -> int:
    if not OPENSCAD.exists():
        raise SystemExit(f"OpenSCAD not found at {OPENSCAD}")
    MODELS.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(exist_ok=True)

    print("Peak Design opposed-face radio standoff")
    print("\nProduction parts")
    for style, name in PRODUCTION:
        for fmt in ("stl", "3mf"):
            render(name, "body", fmt, thread_style=style)

    print("\nSDS150 fit coupons")
    coupon_volumes: list[float] = []
    for label in SDS_COUPONS:
        name = f"radio_standoff_coupon_sds_{label}"
        for fmt in ("stl", "3mf"):
            path = render(name, "coupon", fmt, coupon_fit=label)
            if fmt == "stl":
                coupon_volumes.append(float(trimesh.load(path).volume))

    if len({round(volume, 3) for volume in coupon_volumes}) != len(SDS_COUPONS):
        raise SystemExit(
            "SDS coupon variants are geometrically identical - fit overrides "
            "did not reach the keyhole")
    print("  coupon geometry control: all three volumes are distinct")

    print("\nBelt-clip interface coupons")
    clip_volumes: list[float] = []
    for label, thickness in CLIP_COUPONS:
        name = ("radio_standoff_coupon_clip" if label == "nominal"
                else f"radio_standoff_coupon_clip_{label}")
        for fmt in ("stl", "3mf"):
            path = render(name, "clip_coupon", fmt, clip_bar_t=thickness)
            if fmt == "stl":
                clip_volumes.append(float(trimesh.load(path).volume))

    if len({round(volume, 3) for volume in clip_volumes}) != len(CLIP_COUPONS):
        raise SystemExit(
            "belt-clip coupon variants are geometrically identical - bar "
            "thickness overrides did not reach the mesh")
    print("  coupon geometry control: all three bar thicknesses are distinct")

    print("\nDiagnostic previews")
    preview_specs = [
        ("radio_standoff_preview_body.png", "body",
         "0,0,82,70,0,28,430"),
        ("radio_standoff_preview_assembly.png", "assembly",
         "0,0,82,70,0,28,430"),
        ("radio_standoff_preview_section.png", "section",
         "0,0,82,72,0,0,360"),
    ]
    for filename, mode, camera in preview_specs:
        out = MODELS / filename
        result = subprocess.run(
            [str(OPENSCAD), "-o", str(out), "--imgsize=1100,1100",
             f"--camera={camera}", "--projection=o", "--colorscheme=Tomorrow",
             "-D", f'variant_render_mode="{mode}"',
             str(MODELS / "peak_design_radio_standoff.scad")],
            capture_output=True, text=True, cwd=ROOT,
        )
        if not out.exists() or out.stat().st_size < 1000:
            sys.stderr.write(((result.stdout or "") + (result.stderr or ""))[-2000:])
            raise SystemExit(f"OpenSCAD produced no {filename}")
        print(f"  {filename}")

    print("\nall exports are single watertight solids")
    print("print coupons first; production fit is not final until physical checks pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
