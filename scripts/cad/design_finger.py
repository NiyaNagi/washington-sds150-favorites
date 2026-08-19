"""Size the Peak Design bracket's in-plane finger latch.

BACKGROUND
----------
This is the same small-length flexural pivot used by the visor mount's
lever (see design_lever.py), turned on its side.  A short thin ligament
joining two stiff segments behaves like a pin joint with a torsional
spring: the arm rotates as a rigid body, so displacement is LINEAR in
distance from the pivot.

The tab and the tooth sit on OPPOSITE sides of that pivot, which is the
whole point.  A plain cantilever moves its tip and its tooth the same way,
so pressing it would only drive the tooth further into the slot - that
mistake cost the visor mount a full redesign.  Here, pressing the tab
inward swings the tooth outward and frees the stud.

Where this differs from the visor mount is the direction of bending.  The
latch bar is full plate depth and flexes sideways, in the plane of the
plate, so it needs no clearance underneath.  That is what keeps the
bracket under 10mm thick.  It also means the flexure bends about its THIN
dimension while its stiff depth resists everything else, so the numbers
below use plate thickness as the beam width.

WHAT THIS SCRIPT CHECKS
-----------------------
  travel  - how far the tab must move to retract the tooth
  strain  - peak strain in the flexure, against PLA's limits
  force   - how hard the tab is to press, and how firmly the tooth holds

The forces matter less here than on the visor mount, because gravity does
most of the work: the entry hole is at the top and the locked position at
the bottom, so the radio's weight holds the stud away from the only way
out.  The latch only has to cope with knocks and with the bracket being
inverted, not with carrying the radio.

Values are read from the model rather than restated, so this cannot drift
out of step with what actually gets printed.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/design_finger.py
"""

from __future__ import annotations

import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models"

# Printed PLA along the layer plane.
E_PLA = 2800.0          # Young's modulus, MPa

# PLA has poor fatigue life in repeated flexure - it is not a living-hinge
# material the way PP is.  Keeping peak strain well under 1% is what makes
# daily use reasonable rather than a countdown to a snapped hinge.
STRAIN_COMFORTABLE = 0.008   # 0.8%, target for daily use
STRAIN_YIELD = 0.02          # PLA starts yielding around 2%

# A latch needs enough spring to snap back and hold, but has to stay
# pressable with a thumb on a bracket held in one hand.
PRESS_COMFORTABLE = 15.0     # N, roughly what a thumb gives easily


def read_params(path: Path, names: list[str]) -> dict[str, float]:
    """Pull top-level numeric assignments out of a .scad file.

    Reading the real model is deliberate.  Restating these numbers here
    would let the two drift apart, which during the visor mount's
    development produced three separate confident, entirely false test
    results before the cause was found.

    Only literal assignments can be read this way, so ask for parameters
    rather than derived values.  Requesting a name that later becomes
    derived fails loudly here rather than silently reading a stale figure -
    which is what happened to plate_x_hi when the plate outline started
    being computed from what it has to contain.
    """
    text = path.read_text(encoding="utf-8")
    out: dict[str, float] = {}
    for name in names:
        match = re.search(
            rf"^{name}\s*=\s*(-?[0-9.]+)\s*;", text, re.MULTILINE
        )
        if not match:
            raise SystemExit(f"could not find '{name}' in {path.name}")
        out[name] = float(match.group(1))
    return out


def main() -> None:
    stud = read_params(
        MODELS / "sds150_stud.scad",
        ["stud_neck_d", "stud_neck_h", "stud_head_t", "preload",
         "clr_slide", "head_ch_clr_z_base"],
    )
    br = read_params(
        MODELS / "sds150_pd_bracket.scad",
        ["lever_clr", "lever_w", "flex_len", "flex_t", "pivot_y",
         "detent_bump", "tooth_y0", "tooth_y1", "tab_y0", "tab_y1",
         "base_t", "chan_wall", "press_margin", "head_ch_clr_extra"],
    )

    # Rebuild the derived geometry exactly as the model does.
    #
    # The head channel clearance comes in two parts: a baseline shared with
    # the visor mount, and an addition set by the bracket for its own
    # bridged channel.  Both are read, because using either alone would
    # give a plate thickness the model does not agree with.
    ledge_t = stud["stud_neck_h"] - stud["preload"]
    head_ch_h = (stud["stud_head_t"] + stud["head_ch_clr_z_base"]
                 + br["head_ch_clr_extra"])
    plate_t = ledge_t + head_ch_h + br["base_t"]

    head_ch_w = 15.5 + 2 * stud["clr_slide"]
    neck_w = stud["stud_neck_d"] + 2 * stud["clr_slide"]

    lever_x0 = head_ch_w / 2 + br["chan_wall"] + br["lever_clr"]
    tooth_x = neck_w / 2 - br["detent_bump"]

    # How far the tooth must retract for the neck to pass.  Less than the
    # nominal bump, because the slot is already wider than the neck.
    retract = stud["stud_neck_d"] / 2 - tooth_x

    arm_tooth = (br["tooth_y0"] + br["tooth_y1"]) / 2 - br["pivot_y"]
    arm_tab = br["pivot_y"] - (br["tab_y0"] + br["tab_y1"]) / 2

    angle = math.asin(retract / arm_tooth)          # radians
    tab_travel = arm_tab * math.sin(angle)
    ratio = arm_tooth / arm_tab

    # Strain at the flexure surface: it bends through `angle` over its
    # free length, so curvature = angle / length.
    strain = (angle / br["flex_len"]) * (br["flex_t"] / 2)

    # And at the angle a thumb actually reaches.  Nobody presses a latch
    # to exactly the minimum that frees it, and the relief is cut for the
    # larger angle, so this is the number that decides whether the hinge
    # survives - not the nominal one.
    strain_pressed = strain * br["press_margin"]

    # Torsional stiffness of a short flexure, K = E I / L.  The flexure
    # bends about its thin dimension, and its "width" for this purpose is
    # the full plate thickness, since the bar is full depth.
    inertia = plate_t * br["flex_t"] ** 3 / 12.0
    stiffness = E_PLA * inertia / br["flex_len"]     # N mm / rad

    torque = stiffness * angle
    tab_force = torque / arm_tab
    hold_force = torque / arm_tooth

    # Shear area of the tooth resisting the neck lifting past it.  This is
    # what actually fails if the radio is yanked, not the flexure.
    shear_area = br["detent_bump"] * (br["tooth_y1"] - br["tooth_y0"])

    print("Peak Design bracket - in-plane finger latch")
    print("=" * 62)
    print(f"  plate thickness        = {plate_t:5.2f} mm  "
          f"(ledge {ledge_t:.2f} + channel {head_ch_h:.2f} "
          f"+ back {br['base_t']:.2f})")
    print(f"  flexure                = {br['flex_len']:.1f} mm long, "
          f"{br['flex_t']:.2f} mm thick, {plate_t:.2f} mm deep")
    print()
    print(f"  tooth reaches to x     = {tooth_x:5.2f} mm  "
          f"(neck edge at {stud['stud_neck_d'] / 2:.2f})")
    print(f"  must retract           = {retract:5.2f} mm")
    print(f"  lever arms: tooth {arm_tooth:5.2f} mm, tab {arm_tab:5.2f} mm")
    print(f"  tab moves the tooth    = {100 * ratio:5.1f}% as much")
    print(f"  tab travel to unlock   = {tab_travel:5.2f} mm")
    print(f"  rotation at the pivot  = {math.degrees(angle):5.2f} deg")
    print()
    print(f"  peak flexure strain    = {100 * strain:5.2f} %  "
          f"({100 * strain_pressed:.2f}% at full press)")
    print(f"                           (target under "
          f"{100 * STRAIN_COMFORTABLE:.1f}%, "
          f"yield about {100 * STRAIN_YIELD:.0f}%)")
    print(f"  press force at the tab = {tab_force:5.2f} N  "
          f"({tab_force / 9.81 * 1000:.0f} gf)")
    print(f"  holding force at tooth = {hold_force:5.2f} N")
    print(f"  tooth shear area       = {shear_area:5.2f} mm^2")
    print("=" * 62)

    problems: list[str] = []

    if strain_pressed > STRAIN_YIELD:
        problems.append(
            f"flexure strain {100 * strain_pressed:.2f}% at full press "
            "would yield or snap - lengthen flex_len, thin flex_t, or "
            "move the pivot further from the tooth"
        )
    elif strain_pressed > STRAIN_COMFORTABLE:
        problems.append(
            f"flexure strain {100 * strain_pressed:.2f}% at full press is "
            "high for daily use - it will work, but expect the latch to "
            "soften over time"
        )

    # A throw smaller than the give in a thumb pad reads as "nothing
    # happened", even when the tooth is clearing the neck perfectly.  The
    # first version of this latch moved 1.44mm and felt dead.
    if tab_travel < 2.5:
        problems.append(
            f"paddle travel {tab_travel:.2f} mm is too small to feel - "
            "lengthen the tab arm, which costs no strain at all"
        )

    if tab_force > PRESS_COMFORTABLE:
        problems.append(
            f"press force {tab_force:.1f} N is more than a thumb gives "
            "comfortably - thin the flexure"
        )

    if tab_force < 0.5:
        problems.append(
            f"press force {tab_force:.1f} N is so light the latch may not "
            "spring back reliably - thicken the flexure"
        )

    if tab_travel < 0.4:
        problems.append(
            f"tab travel {tab_travel:.2f} mm is below print tolerance - "
            "the release would be indistinguishable from slop"
        )
    if problems:
        print("NOTES")
        for line in problems:
            print(f"  - {line}")
        raise SystemExit(1)

    print("-> latch is comfortable to press, holds firmly, and stays well "
          "inside PLA's elastic range")


if __name__ == "__main__":
    main()
