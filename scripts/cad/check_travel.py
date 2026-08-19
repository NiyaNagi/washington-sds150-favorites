"""Check the keyhole geometry actually captures the stud head.

A keyhole only holds if, once slid to the locked position, the head has
moved far enough that none of it still sits under the open entry hole.
Otherwise the head can lift into the hole and tilt out.

Required travel is therefore at least half the entry diameter plus half
the head diameter, plus a margin.  This prints the numbers so the choice
of slot_travel can be justified rather than guessed.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_travel.py [travel_mm]
"""

from __future__ import annotations

import sys

# Mirrored from models/sds150_mount_common.scad.
STUD_HEAD_D = 15.5
STUD_NECK_D = 8.3
CLR_SLIDE = 0.30
HOLE_COMP = 0.25

MARGIN = 1.5   # how far past "just clear" we want to be, mm


def main() -> None:
    travel = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0

    entry_d = STUD_HEAD_D + 2 * CLR_SLIDE + HOLE_COMP
    neck_w = STUD_NECK_D + 2 * CLR_SLIDE

    print(f"entry hole diameter   = {entry_d:6.2f} mm")
    print(f"stud head diameter    = {STUD_HEAD_D:6.2f} mm")
    print(f"neck slot width       = {neck_w:6.2f} mm")

    # Put the entry hole at x = 0; the locked stud sits at x = -travel.
    head_near_edge = -travel + STUD_HEAD_D / 2
    hole_near_edge = -entry_d / 2

    print(f"\nwith slot_travel = {travel:.2f} mm:")
    print(f"  head spans        {-travel - STUD_HEAD_D / 2:7.2f} .. {head_near_edge:6.2f}")
    print(f"  entry hole spans  {hole_near_edge:7.2f} .. {entry_d / 2:6.2f}")

    overlap = head_near_edge - hole_near_edge
    if overlap > 0:
        print(f"  OVERLAP of {overlap:.2f} mm - part of the head still sits under")
        print("  the open entry hole, so it can lift and tilt free.")
    else:
        print(f"  clear by {-overlap:.2f} mm - the head is fully under the ledge.")

    needed = (entry_d + STUD_HEAD_D) / 2
    print(f"\ntravel to just clear      = {needed:6.2f} mm")
    print(f"travel with {MARGIN} mm margin = {needed + MARGIN:6.2f} mm  <-- recommended")


if __name__ == "__main__":
    main()
