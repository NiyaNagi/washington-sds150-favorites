"""Find the longest keyhole slot each variant can accommodate.

Two things compete for room along the slide axis:

  the pedestal pocket - the radio's raised pedestal has to traverse the
                        full travel inside its pocket, so the pocket grows
                        with travel and must still fit inside the block
                        with walls around it

  the socket chamber  - the head channel runs from the closed end past the
                        entry hole, which also grows with travel

The block outline is inherited from the visor clamp's jaw, so its size is
fixed.  This reports the largest travel that still fits, for each variant.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/max_travel.py
"""

from __future__ import annotations

# Mirrored from models/sds150_mount_common.scad.
STUD_HEAD_D = 15.5
CLR_SLIDE = 0.30
HOLE_COMP = 0.25
CLR_BOSS = 0.40

BOSS_W = 25.0
BOSS_L = 35.0

WALL = 3.6           # material around the socket cavity
POCKET_WALL = 2.4    # material around the pedestal pocket
TAPER = 0.4          # block inset from the jaw outline

# Jaw top face, measured by probing the source mesh.
JAW_X = 59.70
JAW_Y = 64.85

ENTRY_D = STUD_HEAD_D + 2 * CLR_SLIDE + HOLE_COMP
CHAN_BACK = STUD_HEAD_D / 2 + CLR_SLIDE

# Below this the stud head still overlaps the open entry hole.
MIN_TRAVEL = (ENTRY_D + STUD_HEAD_D) / 2


def limits(name: str, block_along: float, boss_along: float) -> float:
    """Report and return the largest workable travel for one variant."""
    usable = block_along - 2 * TAPER

    # Pedestal pocket: boss + travel + clearance, plus a wall each side.
    pocket_max = usable - 2 * POCKET_WALL
    travel_pocket = pocket_max - boss_along - 2 * CLR_BOSS

    # Socket chamber: closed end + travel + half the entry hole, plus walls.
    chamber_max = usable - 2 * WALL
    travel_chamber = chamber_max - CHAN_BACK - ENTRY_D / 2 - 0.5

    travel = min(travel_pocket, travel_chamber)
    binding = "pedestal pocket" if travel_pocket < travel_chamber else "socket chamber"

    print(f"{name}:")
    print(f"  block along slide axis   = {block_along:6.2f} mm")
    print(f"  pedestal along that axis = {boss_along:6.2f} mm")
    print(f"  travel limited by pocket = {travel_pocket:6.2f} mm")
    print(f"  travel limited by chamber= {travel_chamber:6.2f} mm")
    print(f"  -> maximum travel        = {travel:6.2f} mm  (limited by the {binding})")
    print(f"  -> minimum that locks    = {MIN_TRAVEL:6.2f} mm")

    headroom = travel - MIN_TRAVEL
    if headroom < 0:
        print("  *** will not lock at all in this direction ***")
    else:
        print(f"  -> headroom over minimum = {headroom:6.2f} mm")
    print()
    return travel


def main() -> None:
    print(f"entry hole = {ENTRY_D:.2f} mm, stud head = {STUD_HEAD_D:.2f} mm")
    print(f"head clears the entry hole once travel >= {MIN_TRAVEL:.2f} mm\n")

    # Lengthwise slides along the radio's length, which lies across the
    # visor (the block's X axis).  Crosswise slides along the block's Y.
    limits("lengthwise", JAW_X, BOSS_L)
    limits("crosswise", JAW_Y, BOSS_W)


if __name__ == "__main__":
    main()
