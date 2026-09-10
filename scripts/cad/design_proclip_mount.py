"""Load and section sizing for the ProClip radio plates.

Everything here is read back out of the model's own echo.  Retyping a
dimension into a calculation is how this project has produced confident,
wrong numbers before, so the script fails rather than guesses.

What it works out, per plate:

* the moment the radios apply at the ProClip interface at 1g/3g/5g;
* the tension that moment puts into the upper pair of M4s;
* out-of-plane bending stress in the thinnest section of the plate, and
  the factor of safety against a conservative PLA strength;
* the minimum M4 length, given an ESTIMATED ProClip plate thickness.

The number this script cannot produce is the important one: how much a
ProClip's dashboard-seam grip will actually hold.  Brodit publish no such
rating.  See docs/proclip-radio-mounts.md.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/design_proclip_mount.py
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "models" / "proclip mounts" / "proclip_radio_mount.scad"
TMP = ROOT / ".tmp-cad"
OPENSCAD = Path(r"C:\Program Files\OpenSCAD\openscad.exe")

G = 9.80665
PLA_STRENGTH_MPA = 25.0    # conservative, as used by the standoff
PLA_MODULUS_MPA = 2400.0
FOS_TARGET = 3.0
ACCELERATIONS = [("1g static", 1.0), ("3g road bump", 3.0), ("5g shock", 5.0)]

CASES = [("sds", "landscape"), ("sds", "portrait"),
         ("clip", "landscape"), ("clip", "portrait"),
         ("combined", "landscape"), ("combined", "portrait")]


def echo(variant: str, orientation: str) -> str:
    TMP.mkdir(exist_ok=True)
    result = subprocess.run(
        [str(OPENSCAD), "-o", str(TMP / "_pcdes_null.stl"),
         "-D", 'variant_render_mode="none"',
         "-D", f'variant="{variant}"',
         "-D", f'amps_orientation="{orientation}"', str(MODEL)],
        capture_output=True, text=True, cwd=ROOT)
    return (result.stdout or "") + "\n" + (result.stderr or "")


def value(text: str, name: str) -> float:
    found = re.findall(rf"(?:^|\s){re.escape(name)}=(-?[0-9.]+)", text)
    if not found:
        raise SystemExit(f"model did not echo {name}; refusing to assume it")
    return float(found[-1])


def main() -> int:
    if not OPENSCAD.exists():
        raise SystemExit(f"OpenSCAD not found at {OPENSCAD}")

    print("=== ProClip radio plate sizing ===")
    print(f"  PLA taken at {PLA_STRENGTH_MPA:.0f} MPa and "
          f"{PLA_MODULUS_MPA:.0f} MPa, both deliberately conservative")
    print()

    worst_fos = None
    worst_case = ""

    for variant, orientation in CASES:
        text = echo(variant, orientation)
        plate_t = value(text, "plate_t")
        amps_x = value(text, "amps_x")
        amps_z = value(text, "amps_z")
        sds_arm = value(text, "sds_arm_y")
        clip_arm = value(text, "clip_arm_y")
        sds_m = value(text, "sds_mass_g") / 1000.0
        clip_m = value(text, "thd_mass_g") / 1000.0
        pad_w = value(text, "pad_w")
        span_w = value(text, "outer") + 2 * value(text, "bar_t")
        screw_len = value(text, "min_screw_len")

        # Only the interfaces this variant actually carries.
        loads = []
        if variant in ("sds", "combined"):
            loads.append(("SDS150", sds_m, sds_arm, pad_w))
        if variant in ("clip", "combined"):
            loads.append(("belt-clip radio", clip_m, clip_arm, span_w))

        total_mass = sum(m for _, m, _, _ in loads)
        # Moment about the horizontal axis through the screw pattern.  The
        # radios sit on the same side, so their moments add.
        arm_moment = sum(m * a for _, m, a, _ in loads)   # kg.mm

        print(f"  {variant.upper()} / {orientation}"
              f"   AMPS {amps_x:.2f} x {amps_z:.2f}")
        for name, mass, arm, _ in loads:
            print(f"    {name:<16} {mass * 1000:.0f} g at {arm:.1f} mm "
                  "off the ProClip face")

        print(f"    {'load':<14}{'moment':>10}{'screw tension':>15}"
              f"{'bending':>11}{'FoS':>8}")
        for label, accel in ACCELERATIONS:
            moment_nmm = arm_moment * G * accel          # N.mm
            # Reacted as a couple over the screw pattern's height: the top
            # pair pulls, the bottom edge of the plate bears.
            tension_total = moment_nmm / amps_z
            tension_each = tension_total / 2.0

            # Out-of-plane bending in the plain 5mm plate.  Each interface
            # hands its own moment to its own local width, so the worst
            # section is the one with the least width per unit moment.
            stress = max(
                (m * G * accel * a) / (w * plate_t ** 2 / 6.0)
                for _, m, a, w in loads)
            fos = PLA_STRENGTH_MPA / stress if stress > 0 else float("inf")
            if worst_fos is None or fos < worst_fos:
                worst_fos = fos
                worst_case = f"{variant}/{orientation} at {label}"
            print(f"    {label:<14}{moment_nmm:>8.0f} Nmm"
                  f"{tension_each:>12.1f} N"
                  f"{stress:>9.2f} MPa{fos:>8.1f}")

        print(f"    total hanging mass {total_mass * 1000:.0f} g, "
              f"weight {total_mass * G:.2f} N")
        print(f"    M4 countersunk length: {screw_len:.0f} mm minimum "
              "(ProClip plate thickness ESTIMATED)")
        print()

    print(f"  worst factor of safety anywhere: {worst_fos:.1f} "
          f"({worst_case})")
    if worst_fos < FOS_TARGET:
        print(f"=== FAIL ===")
        print(f"  below the {FOS_TARGET:.0f}x target for the printed plate")
        return 1

    print()
    print("=== PASS ===")
    print("  the printed plate and the M4s are not the weak link at 5g.")
    print()
    print("  READ THIS.  The weak link is the ProClip itself.  It retains a")
    print("  dashboard by clipping into panel seams, Brodit publish no load")
    print("  rating for it, and it was designed around phones and GPS units")
    print("  of a fraction of a loaded SDS150's 400 g.  Nothing above says")
    print("  the mount will stay on the dash - only that the plate will not")
    print("  be what breaks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
