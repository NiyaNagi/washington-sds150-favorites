"""Size the compliant release lever, and check it survives daily use.

BACKGROUND
----------
The first release design failed because it was a plain cantilever: a
uniform beam deflects as x^2(3L-x), so a point partway along moves far
less than the tip.  Pressing a tab beyond the detent bump mostly just bent
the far end.

The fix is a **small-length flexural pivot** (Howell, *Compliant
Mechanisms*, 2001).  A short thin flexure joining two stiff segments
behaves like a pin joint with a torsional spring: the arm then rotates as
a rigid body, so displacement is LINEAR in distance from the pivot rather
than cubic.  The usual design rules are that the flexure should be much
shorter and much thinner than the rigid segments it joins, so that
essentially all the compliance - and all the strain - lives in the flexure
where it can be controlled.

That buys two things here:
  * a much better travel ratio between tab and bump
  * strain concentrated in one known place, so it can be checked

WHAT THIS SCRIPT CHECKS
-----------------------
  travel  - how far the tab must move to retract the bump
  strain  - peak strain in the flexure, against PLA's limits
  force   - how hard the tab is to press, and how firmly the bump is held

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/design_lever.py
"""

from __future__ import annotations

import math

# Printed PLA along the layer plane.
E_PLA = 2800.0          # Young's modulus, MPa

# PLA is not a living-hinge material the way PP is; it has poor fatigue
# life in repeated flexure.  Keeping peak strain well under 1% is what
# makes daily use reasonable.
STRAIN_COMFORTABLE = 0.008   # 0.8%, target for daily use
STRAIN_YIELD = 0.02          # PLA starts yielding around 2%

# Fixed by the socket geometry.
STUD_HEAD_D = 15.5
CLR_SLIDE = 0.30
DETENT_STANDOFF = 0.50

CHAN_BACK = STUD_HEAD_D / 2 + CLR_SLIDE
BUMP_X = STUD_HEAD_D / 2 + DETENT_STANDOFF

# The click-only variants use a 1.4mm bump, because a firm deliberate pull
# is the only way off and it has to resist vibration on its own.  The lever
# variants use the same depth: the stud head is 3mm thick, so 1.4mm blocks
# just under half its edge - a positive catch rather than a token one.
DETENT_BUMP = 1.40      # mm

# Lever design parameters - these are what get tuned.
FLEX_OFFSET = 4.0       # pivot sits this far behind the chamber's closed end
FLEX_LEN = 6.0          # flexure length, mm - longer spreads the bending
FLEX_T = 1.3            # flexure thickness, mm - the main tuning knob
ROCKER_W = 22.0         # width of the arm, mm
TAB_PROTRUDE = 10.0     # how far the tab sticks past the block edge, mm

# Where the tab passes out through the block wall, per variant.
WALL = 3.6
ENTRY_D = STUD_HEAD_D + 2 * CLR_SLIDE + 0.25
VARIANTS = {"lengthwise": 18.0, "crosswise": 24.0}   # slot travel, mm


def analyse(name: str, travel: float) -> None:
    pivot_x = -(CHAN_BACK + FLEX_OFFSET)
    chamber_front = travel + ENTRY_D / 2 + 0.5
    tab_x = chamber_front + WALL + TAB_PROTRUDE

    arm_bump = BUMP_X - pivot_x
    arm_tab = tab_x - pivot_x
    ratio = arm_bump / arm_tab

    tab_travel = DETENT_BUMP / ratio
    angle = tab_travel / arm_tab            # radians, small-angle

    # Strain at the flexure surface: the flexure bends through `angle`
    # over its length, so curvature = angle / length.
    strain = (angle / FLEX_LEN) * (FLEX_T / 2)

    # Torsional stiffness of a short flexure, K = E I / L.
    inertia = ROCKER_W * FLEX_T ** 3 / 12.0
    stiffness = E_PLA * inertia / FLEX_LEN     # N mm / rad

    torque = stiffness * angle
    tab_force = torque / arm_tab
    bump_force = torque / arm_bump

    print(f"{name}  (slot travel {travel:.1f} mm)")
    print(f"  pivot at {pivot_x:6.2f} mm, bump at {BUMP_X:5.2f}, tab at {tab_x:6.2f}")
    print(f"  lever arms: bump {arm_bump:5.2f} mm, tab {arm_tab:5.2f} mm")
    print(f"  tab moves the bump {100 * ratio:5.1f}% as much  "
          f"(a plain cantilever gave 34%)")
    print(f"  tab travel to unlock   = {tab_travel:5.2f} mm  "
          f"(free air below, so unrestricted)")
    print(f"  rotation at the pivot  = {math.degrees(angle):5.2f} deg")
    print(f"  peak flexure strain    = {100 * strain:5.2f} %  "
          f"(target under {100 * STRAIN_COMFORTABLE:.1f}%, "
          f"yield about {100 * STRAIN_YIELD:.0f}%)")
    print(f"  press force at the tab = {tab_force:5.2f} N  "
          f"({tab_force / 9.81 * 1000:.0f} gf)")
    print(f"  holding force at bump  = {bump_force:5.2f} N")

    if strain > STRAIN_YIELD:
        print("  *** would yield or snap ***")
    elif strain > STRAIN_COMFORTABLE:
        print("  ** strain is high for daily use - thin the flexure or "
              "lengthen it **")
    else:
        print("  -> strain is comfortable for daily use in PLA")
    print()


def main() -> None:
    print(f"flexure: {FLEX_LEN:.1f} mm long, {FLEX_T:.1f} mm thick, "
          f"{ROCKER_W:.1f} mm wide")
    print(f"bump must retract {DETENT_BUMP:.2f} mm to release\n")
    for name, travel in VARIANTS.items():
        analyse(name, travel)


if __name__ == "__main__":
    main()
