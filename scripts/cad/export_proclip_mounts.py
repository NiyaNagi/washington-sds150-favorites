"""Export the six ProClip radio plates, the gauges, and the fit coupons.

Print order is deliberate and the filenames say so:

    1. proclip_gauge_*        does the pattern fit the real mount at all
    2. proclip_coupon_*       does each radio interface fit the real radio
    3. proclip_<variant>_*    only then, the plate itself

"horizontal" and "vertical" are LABELS for the two hole orientations, not
measurements.  Landscape is 38.05 across and 30.17 up; portrait is the
other way round.  Which of the two ProClip mounts is which has not been
verified - the gauge is what settles it, and swapping the mapping here is
a one-word change.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/export_proclip_mounts.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models" / "proclip mounts"
MODEL = MODELS / "proclip_radio_mount.scad"
TMP = ROOT / ".tmp-cad"
OPENSCAD = Path(r"C:\Program Files\OpenSCAD\openscad.exe")

# label -> amps_orientation.  See the module docstring before flipping.
ORIENTATIONS = [("horizontal", "landscape"), ("vertical", "portrait")]
VARIANTS = ["sds", "clip", "combined"]
SDS_COUPONS = ["easy", "nominal", "firm"]


def render(name: str, mode: str, fmt: str, **assignments) -> Path:
    out = MODELS / f"{name}.{fmt}"
    defines = ["-D", f'variant_render_mode="{mode}"']
    for key, value in assignments.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, str):
            rendered = f'"{value}"'
        else:
            rendered = str(value)
        defines.extend(["-D", f"{key}={rendered}"])
    out.unlink(missing_ok=True)
    started = time.monotonic()
    result = subprocess.run(
        [str(OPENSCAD), "-o", str(out), *defines, str(MODEL)],
        capture_output=True, text=True, cwd=ROOT)
    elapsed = time.monotonic() - started
    if not out.exists() or out.stat().st_size < 200:
        sys.stderr.write(((result.stdout or "") + (result.stderr or ""))[-2500:])
        raise SystemExit(f"OpenSCAD produced no {out.name}")
    print(f"  {out.name:<40} {elapsed:5.1f}s", end="")
    if fmt == "stl":
        mesh = trimesh.load(out)
        dims = mesh.bounds[1] - mesh.bounds[0]
        if not mesh.is_watertight or mesh.body_count != 1:
            raise SystemExit(
                f"\n{out.name}: watertight={mesh.is_watertight}, "
                f"bodies={mesh.body_count}")
        print(f"  {mesh.volume/1000:6.1f}cm3  "
              f"{dims[0]:5.1f}x{dims[1]:4.1f}x{dims[2]:5.1f}mm  ok")
    else:
        print("  written")
    return out


def main() -> int:
    if not OPENSCAD.exists():
        raise SystemExit(f"OpenSCAD not found at {OPENSCAD}")
    MODELS.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(exist_ok=True)

    print("ProClip radio mounting plates")

    print("\n1. AMPS gauges - print these FIRST, before anything else")
    for label, orientation in ORIENTATIONS:
        for fmt in ("stl", "3mf"):
            render(f"proclip_gauge_{label}", "gauge", fmt,
                   amps_orientation=orientation, variant="sds")

    print("\n2. SDS150 fit coupons - pick a fit before printing a plate")
    coupon_volumes: list[float] = []
    for fit in SDS_COUPONS:
        for fmt in ("stl", "3mf"):
            path = render(f"proclip_coupon_sds_{fit}", "coupon", fmt,
                          variant="sds", amps_orientation="landscape",
                          coupon_fit=fit)
            if fmt == "stl":
                coupon_volumes.append(float(trimesh.load(path).volume))
    if len({round(v, 3) for v in coupon_volumes}) != len(SDS_COUPONS):
        raise SystemExit(
            "the three SDS coupons came out geometrically identical - the "
            "fit overrides did not reach the keyhole")
    print("  coupon control: all three volumes are distinct")

    print("\n3. Belt-clip coupon")
    for fmt in ("stl", "3mf"):
        render("proclip_coupon_clip", "clip_coupon", fmt,
               variant="clip", amps_orientation="landscape")

    print("\n4. Plates")
    for variant in VARIANTS:
        for label, orientation in ORIENTATIONS:
            for fmt in ("stl", "3mf"):
                render(f"proclip_{variant}_{label}", "plate", fmt,
                       variant=variant, amps_orientation=orientation)

    # Looking from +Y, the cabin side, because that is the face the radios
    # attach to and the only one worth a picture.  rot_z=205 swings round
    # from OpenSCAD's default front view, which stares at the bearing face.
    print("\n5. Diagnostic previews")
    preview_specs = (
        [(f"proclip_preview_{v}_{lab}.png", "plate", v, orient)
         for v in VARIANTS for lab, orient in ORIENTATIONS]
        + [(f"proclip_assembly_{v}_horizontal.png", "assembly", v,
            "landscape") for v in VARIANTS])
    for filename, mode, variant, orientation in preview_specs:
        out = MODELS / filename
        result = subprocess.run(
            [str(OPENSCAD), "-o", str(out), "--imgsize=1100,1100",
             "--camera=0,0,0,72,0,205,500", "--projection=o",
             "--colorscheme=Tomorrow", "--viewall", "--autocenter",
             "-D", f'variant_render_mode="{mode}"',
             "-D", f'variant="{variant}"',
             "-D", f'amps_orientation="{orientation}"', str(MODEL)],
            capture_output=True, text=True, cwd=ROOT)
        if not out.exists() or out.stat().st_size < 1000:
            sys.stderr.write(
                ((result.stdout or "") + (result.stderr or ""))[-2000:])
            raise SystemExit(f"OpenSCAD produced no {filename}")
        print(f"  {filename}")

    print("\nall exports are single watertight solids")
    print("the AMPS pattern is a published standard, not a measured one -")
    print("offer the gauge up to the real mount before printing a plate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
