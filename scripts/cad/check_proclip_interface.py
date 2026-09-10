"""Verify the ProClip/AMPS interface on all six plates.

The ProClip side of this design is the part nobody has measured, so the
checks here are deliberately about the things a wrong assumption would
break in a way that is invisible on screen:

* every countersink opens onto a FLAT land - nothing raised is sitting on
  a screw head, and a driver can reach all four;
* the M4 clearance envelope never comes near the SDS150 keyhole.  A screw
  hole 1.48mm from the stud channel is a bug this project has already
  shipped once;
* the pedestal lands flat on its pad, and - since the plates ship with
  the pedestal channel OFF - that a twisted pedestal really is free,
  while enabling sds_guide really does block it.  The shipped part is
  reported as it is; the option is kept under test so it cannot rot;
* every plate is one watertight solid.

Each check carries an injected fault, because a harness that cannot fail
is not evidence.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_proclip_interface.py
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

VARIANTS = ["sds", "clip", "combined"]
ORIENTATIONS = ["landscape", "portrait"]

TOUCH_TOL = 5.0        # mm^3 of tessellation noise on curved intersections
CONTROL_MIN = 25.0     # an injected fault must be unmistakable
KEYHOLE_CLR = 1.60     # mm the screw envelope must keep from the keyhole

# Twist to test the pedestal channel with.  At 3 degrees a 35mm pedestal
# corner sweeps 17.5*sin(3) = 0.92mm sideways against 0.40mm of channel
# clearance, so a working channel MUST be hit.  The volume that produces
# is small - a shallow wedge - so the proof is not "a big number", it is
# that the same twist is free once the channel is switched off.
ROT_PROOF_DEG = 3.0


def render(tag: str, mode: str, variant: str, orientation: str,
           **values: float | str) -> trimesh.Trimesh:
    out = TMP / f"pcif_{tag}.stl"
    out.unlink(missing_ok=True)
    assigns = [
        f'variant_render_mode = "{mode}";',
        f'variant = "{variant}";',
        f'amps_orientation = "{orientation}";',
    ]
    for key, value in values.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, str):
            rendered = f'"{value}"'
        else:
            rendered = str(value)
        assigns.append(f"{key} = {rendered};")
    wrapper = MODELS / f".pcif_{tag}.scad"
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


def echo(variant: str, orientation: str) -> str:
    result = subprocess.run(
        [str(OPENSCAD), "-o", str(TMP / "_pcif_null.stl"),
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

    print("=== ProClip AMPS interface ===")
    text = echo("sds", "landscape")
    print(f"  AMPS pattern      : {value(text, 'amps_x'):.2f} x "
          f"{value(text, 'amps_z'):.2f} mm centre-to-centre (landscape)")
    print(f"  countersink       : {value(text, 'cs_head_d'):.2f} mm head, "
          f"{value(text, 'cs_depth'):.2f} mm deep, "
          f"{value(text, 'cs_land'):.2f} mm of plate under it")
    print(f"  flat land radius  : {value(text, 'pad_r'):.2f} mm")
    print(f"  screw length      : {value(text, 'min_screw_len'):.1f} mm "
          "minimum, on an ESTIMATED ProClip plate thickness")
    print()

    failures: list[str] = []

    for variant in VARIANTS:
        for orientation in ORIENTATIONS:
            tag = f"{variant}_{orientation}"
            print(f"  {variant.upper()} / {orientation}")
            body = render(f"body_{tag}", "plate", variant, orientation)
            if not body.is_watertight or body.body_count != 1:
                failures.append(
                    f"{tag}: not one watertight solid "
                    f"(watertight={body.is_watertight}, "
                    f"bodies={body.body_count})")
            dims = body.bounds[1] - body.bounds[0]
            print(f"    solid                     : "
                  f"{body.volume/1000:6.1f} cm^3  "
                  f"{dims[0]:.1f}x{dims[1]:.1f}x{dims[2]:.1f} mm")

            # 1. Every countersink opens onto a flat land.
            probe = render(f"probe_{tag}", "amps_land_probe",
                           variant, orientation)
            land = shared(body, probe)
            print(f"    material over the heads   : {land:8.2f} mm^3")
            if land > TOUCH_TOL:
                failures.append(
                    f"{tag}: {land:.1f}mm^3 of raised material sits on the "
                    "countersinks; a driver cannot reach those screws")

            # Injected fault: shrink the keep-out so it no longer clears
            # the raised features.  On some layouts nothing reaches a land
            # in the first place, and then this control is vacuous rather
            # than failed - so ask the geometry which case this is instead
            # of assuming.
            blind = render(f"blind_{tag}", "plate", variant, orientation,
                           amps_keepout_scale=0.20)
            keepout_work = blind.volume - body.volume
            blind_v = shared(blind, probe)
            if keepout_work <= TOUCH_TOL:
                print(f"    (fault) keep-out at 20%   : "
                      f"inert - no raised feature reaches a land")
            else:
                print(f"    (fault) keep-out at 20%   : {blind_v:8.2f} mm^3 "
                      f"(keep-out removes {keepout_work:.1f} mm^3)")
                if blind_v <= TOUCH_TOL:
                    failures.append(
                        f"{tag}: the keep-out removes "
                        f"{keepout_work:.1f}mm^3 of material over the lands, "
                        f"but disabling it showed only {blind_v:.1f}mm^3; "
                        "the land probe cannot see material it should")

            if variant in ("sds", "combined"):
                # 2. The screws keep clear of the keyhole.
                void = render(f"void_{tag}", "sds_void", variant, orientation)
                envelope = render(f"env_{tag}", "screw_clearance",
                                  variant, orientation,
                                  screw_check_grow=KEYHOLE_CLR)
                near = shared(void, envelope)
                print(f"    screw envelope vs keyhole : {near:8.2f} mm^3 "
                      f"(at {KEYHOLE_CLR:.2f} mm clearance)")
                if near > 0.0:
                    failures.append(
                        f"{tag}: the M4 clearance envelope reaches the "
                        f"keyhole ({near:.1f}mm^3)")

                gross = render(f"gross_{tag}", "screw_clearance",
                               variant, orientation, screw_check_grow=12.0)
                gross_v = shared(void, gross)
                print(f"    (fault) envelope +12 mm   : {gross_v:8.2f} mm^3")
                if gross_v < CONTROL_MIN:
                    failures.append(
                        f"{tag}: a 12mm-oversize screw envelope produced only "
                        f"{gross_v:.1f}mm^3; the clearance check is blind")

                # 3. The pedestal lands flat on the pad.  As shipped the
                # channel is OFF, so this is a bearing check, not an
                # anti-rotation one - see below.
                square = render(f"ped_{tag}", "pedestal", variant,
                                orientation, check_rot=0.0)
                square_v = shared(body, square)
                print(f"    pedestal seated square    : {square_v:8.2f} mm^3")
                if square_v > TOUCH_TOL:
                    failures.append(
                        f"{tag}: the seated pedestal fouls the pad by "
                        f"{square_v:.1f}mm^3")

                # 4. The channel option still does what it claims.  It is
                # not in the shipped plates, so what is verified here is
                # the OPTION, and the shipped state is reported honestly
                # rather than being quietly asserted to be safe.
                guided = render(f"gbody_{tag}", "plate", variant,
                                orientation, sds_guide=True)
                guided_twist = render(f"gped_{tag}", "pedestal", variant,
                                      orientation, sds_guide=True,
                                      check_rot=ROT_PROOF_DEG)
                guided_v = shared(guided, guided_twist)
                plain_twist = render(f"rot_{tag}", "pedestal", variant,
                                     orientation, check_rot=ROT_PROOF_DEG)
                plain_v = shared(body, plain_twist)
                print(f"    twist {ROT_PROOF_DEG:.0f} deg, as shipped   : "
                      f"{plain_v:8.2f} mm^3  (free - no anti-rotation)")
                print(f"    twist {ROT_PROOF_DEG:.0f} deg, sds_guide=true: "
                      f"{guided_v:8.2f} mm^3  (blocked)")
                if plain_v > TOUCH_TOL:
                    failures.append(
                        f"{tag}: the shipped flat pad still met "
                        f"{plain_v:.1f}mm^3 on a {ROT_PROOF_DEG:.0f} degree "
                        "twist; something other than a channel is fouling "
                        "the pedestal")
                if guided_v <= TOUCH_TOL:
                    failures.append(
                        f"{tag}: enabling sds_guide no longer blocks a "
                        f"{ROT_PROOF_DEG:.0f} degree twist "
                        f"({guided_v:.1f}mm^3); the option has rotted")
            print()

    # The combined plate is the only one where two radios share a face, so
    # it is the only one that can have them foul each other or the plate.
    # 8 mm of drawn air between two envelopes is not evidence.
    print("  COMBINED PLATE, BOTH RADIOS FITTED")
    for orientation in ORIENTATIONS:
        tag = f"combined_{orientation}"
        body = render(f"cbody_{tag}", "plate", "combined", orientation)
        sds = render(f"csds_{tag}", "sds_envelope", "combined", orientation)
        thd = render(f"cthd_{tag}", "thd_envelope", "combined", orientation)

        pair = shared(sds, thd)
        sds_plate = shared(sds, body)
        thd_plate = shared(thd, body)
        print(f"    {orientation}: radio vs radio {pair:7.2f} mm^3, "
              f"SDS vs plate {sds_plate:7.2f} mm^3, "
              f"clip radio vs plate {thd_plate:7.2f} mm^3")
        if pair > TOUCH_TOL:
            failures.append(
                f"{tag}: the two radios overlap by {pair:.1f}mm^3")
        if sds_plate > TOUCH_TOL:
            failures.append(
                f"{tag}: the SDS150 body fouls the plate by "
                f"{sds_plate:.1f}mm^3")
        if thd_plate > TOUCH_TOL:
            failures.append(
                f"{tag}: the belt-clip radio fouls the plate by "
                f"{thd_plate:.1f}mm^3")

    # Injected fault: slide one radio 40 mm toward the other and they must
    # collide.  Done by moving the rendered mesh rather than by shrinking
    # combined_gap, because that is a derived driver and the model's own
    # asserts stop it long before a mesh comes out - which is correct
    # behaviour, and useless as a control.
    sds = render("fsds", "sds_envelope", "combined", "landscape")
    thd = render("fthd", "thd_envelope", "combined", "landscape")
    thd.apply_translation([-40.0, 0.0, 0.0])
    tight_v = shared(sds, thd)
    print(f"    (fault) one radio slid 40 mm inboard: {tight_v:9.0f} mm^3")
    if tight_v < CONTROL_MIN:
        failures.append(
            f"sliding a radio 40mm inboard produced only "
            f"{tight_v:.1f}mm^3; the assembly check cannot see an overlap")
    print()

    if failures:
        print("=== FAIL ===")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("=== PASS ===")
    print("  all six plates are single watertight solids;")
    print("  every countersink lands flat and clear of the keyhole;")
    print("  the pedestal seats flat on its pad, free to rotate as shipped")
    print("  and blocked when sds_guide is enabled;")
    print("  and on the combined plates neither radio fouls the other")
    print()
    print("  NOTE: this proves the plates are self-consistent.  It cannot")
    print("  prove the ProClip's own pattern is AMPS - print the gauge.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
