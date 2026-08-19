"""Sanity-check the release mechanism as a cantilever spring.

The detent is a bump on a flat printed tongue.  To release the radio the
bump has to drop far enough to clear the stud head, and the user has to be
able to make that happen by pressing a tab somewhere else on the tongue.

Two things decide whether that works:

  leverage  - a cantilever's deflection grows with the CUBE of the distance
              from its anchor.  If the push tab is far from the anchor and
              the bump is close to it, pressing the tab mostly just bends
              the far end: the bump barely moves.  The ratio below says how
              much of the tab's travel actually reaches the bump.

  force     - how hard you have to press to move the bump far enough.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_release.py
"""

from __future__ import annotations

# Printed PLA, along the layer plane.  Conservative working figure.
E_PLA = 2800.0        # Young's modulus, MPa (N/mm^2)
YIELD_STRAIN = 0.02   # strain at which PLA starts to yield

# Geometry mirrored from models/sds150_mount_common.scad.
TONGUE_T = {"crosswise": 2.4, "lengthwise": 3.0}
TONGUE_W = 16.1        # head_ch_w
DETENT_BUMP = 1.40

STUD_HEAD_D = 15.5
CLR_SLIDE = 0.30
DETENT_STANDOFF = 0.50

CHAN_BACK = STUD_HEAD_D / 2 + CLR_SLIDE   # closed end of the chamber
ROOT_EMBED = 3.0                          # how far the root is buried

# Distances measured from the tongue's anchor.
BUMP_POS = CHAN_BACK + ROOT_EMBED + STUD_HEAD_D / 2 + DETENT_STANDOFF
TAB_POS = 37.0        # roughly where the tab reaches the block edge
TONGUE_GAP = 2.4      # room beneath the tongue to flex into, mm


def deflection_shape(x: float, length: float) -> float:
    """Relative deflection at x for a cantilever loaded at its tip."""
    # y(x) = F x^2 (3L - x) / 6EI ; we only need the shape term.
    return x * x * (3 * length - x)


def main() -> None:
    print(f"tongue anchor at 0 mm")
    print(f"detent bump   at {BUMP_POS:5.1f} mm from the anchor")
    print(f"push tab      at {TAB_POS:5.1f} mm from the anchor")
    print(f"bump must drop {DETENT_BUMP:.2f} mm to release the head\n")

    shape_bump = deflection_shape(BUMP_POS, TAB_POS)
    shape_tab = deflection_shape(TAB_POS, TAB_POS)
    ratio = shape_bump / shape_tab
    tab_travel = DETENT_BUMP / ratio

    print(f"pressing the tab moves the bump by {100 * ratio:.1f}% as much")
    print(f"  -> to drop the bump {DETENT_BUMP:.2f} mm, the tab must travel "
          f"{tab_travel:.1f} mm")
    print(f"  -> but there is only {TONGUE_GAP:.1f} mm of room beneath it")

    if tab_travel > TONGUE_GAP:
        print(f"\n  *** THE TAB BOTTOMS OUT AFTER {TONGUE_GAP:.1f} mm ***")
        reached = ratio * TONGUE_GAP
        print(f"      at which point the bump has only dropped "
              f"{reached:.2f} mm of the {DETENT_BUMP:.2f} mm needed.")
        print("      The radio cannot be released.\n")
    else:
        print("  -> fits within the available gap\n")

    for name, thickness in TONGUE_T.items():
        inertia = TONGUE_W * thickness ** 3 / 12.0

        # Force at the tab to achieve that tip deflection.
        force = 3 * E_PLA * inertia * tab_travel / TAB_POS ** 3

        # Peak bending strain at the root, to see if it survives.
        curvature = 6 * force * TAB_POS / (E_PLA * TONGUE_W * thickness ** 3)
        strain = curvature * thickness / 2

        print(f"{name} (tongue {thickness} mm thick):")
        print(f"  tab travel needed  = {tab_travel:6.1f} mm")
        print(f"  press force        = {force:6.1f} N  "
              f"({force / 9.81:.1f} kgf)")
        print(f"  peak strain        = {strain * 100:6.2f} %  "
              f"(PLA yields around {YIELD_STRAIN * 100:.0f} %)")
        if strain > YIELD_STRAIN:
            print("  -> WOULD SNAP OR TAKE A PERMANENT SET")
        print()


if __name__ == "__main__":
    main()
