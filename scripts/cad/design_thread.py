"""Size a printable thread before any geometry exists.

Threads fail on a 3D printer for reasons that have nothing to do with
whether the CAD is correct.  The crest can be narrower than the nozzle can
lay down.  The flanks can overhang further than the printer can bridge.
The engagement can be strong but take so many turns that nobody wants to
open it.  None of those show up in a render, and all of them are decided
by arithmetic that fits on one page.

So the arithmetic happens here, first, and the model is written to suit.

This project has already thrown away one modelled thread.  The comment in
sds150_pd_bracket.scad records why: a 1/4"-20 form is 0.69mm deep and its
crests come to a knife edge measuring 0.004mm.  The number that mattered
was the crest width, and nobody computed it until after the print failed.
It is the first thing this script prints.

Values are read from models/thread_lib.scad's callers rather than restated
where possible; the defaults here are the library's own.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/design_thread.py
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models"

# Bambu H2C with a 0.4mm nozzle.  Extrusion width is what actually lands
# on the plate, and it is what a crest has to be measured against - not
# the nozzle diameter, which is only the hole it came out of.
EXTRUSION_W = 0.42          # mm
MIN_CREST_EXTRUSIONS = 2.0  # a crest thinner than this is a knife edge

# Overhang measured from vertical.  45 degrees is the usual limit for
# unsupported plastic; a thread flank that exceeds it droops into the
# groove below and the mating part will not go on.
MAX_OVERHANG = 45.0         # degrees

# Printed PLA, along the layer plane.
PLA_SHEAR = 40.0            # MPa, conservative for layer-adjacent shear


def read_params(path: Path, names: list[str]) -> dict[str, float]:
    """Pull literal numeric assignments out of a .scad file.

    Reading the model rather than restating its numbers here is the whole
    point - a second copy of a dimension is a dimension that can drift.

    Only literal assignments can be read this way.  Asking for a derived
    value fails loudly, which is the correct outcome: it means the model
    computes that value and this script should too.
    """
    text = path.read_text(encoding="utf-8")
    out: dict[str, float] = {}
    for name in names:
        match = re.search(rf"^{name}\s*=\s*(-?[0-9.]+)\s*;", text,
                          re.MULTILINE)
        if not match:
            raise SystemExit(f"could not find '{name}' in {path.name}")
        out[name] = float(match.group(1))
    return out


def main() -> int:
    scad = MODELS / "efhw_enclosure.scad"
    if scad.exists():
        p = read_params(scad, [
            "thread_pitch", "thread_starts", "thread_crest_flat",
            "thread_root_flat", "thread_flank_ang", "thread_clr",
            "thread_len", "thread_engage",
        ])
        pitch = p["thread_pitch"]
        starts = int(p["thread_starts"])
        crest_flat = p["thread_crest_flat"]
        root_flat = p["thread_root_flat"]
        flank_ang = p["thread_flank_ang"]
        clr = p["thread_clr"]
        engage = p["thread_engage"]
        r0 = read_params(scad, ["thread_minor_r"])["thread_minor_r"] \
            if re.search(r"^thread_minor_r\s*=\s*-?[0-9.]",
                         scad.read_text(encoding="utf-8"), re.MULTILINE) \
            else 69.2
        source = scad.name
    else:
        # The library's own defaults, so this can be run before the
        # enclosure exists.
        pitch, starts = 4.0, 2
        crest_flat = root_flat = 1.0
        flank_ang = 60.0
        clr = 0.35
        engage = 16.0
        r0 = 69.2
        source = "built-in defaults (efhw_enclosure.scad not present yet)"

    lead = pitch * starts
    run = (pitch - crest_flat - root_flat) / 2
    depth = run * math.tan(math.radians(flank_ang))

    problems: list[str] = []

    print(f"=== thread sizing ===   ({source})")
    print()
    print(f"  pitch                : {pitch:.2f} mm")
    print(f"  starts               : {starts}")
    print(f"  lead                 : {lead:.2f} mm per revolution")
    print(f"  flank angle          : {flank_ang:.0f} deg from the "
          f"perpendicular")
    print(f"  depth                : {depth:.3f} mm")
    print(f"  minor / major radius : {r0:.2f} / {r0 + depth:.2f} mm")
    print(f"  minor / major dia    : {2 * r0:.2f} / {2 * (r0 + depth):.2f} mm")

    # ---- the number that killed the last attempt -----------------------
    print()
    print("  CREST AND ROOT")
    crest_ext = crest_flat / EXTRUSION_W
    root_ext = root_flat / EXTRUSION_W
    print(f"    crest flat         : {crest_flat:.2f} mm "
          f"= {crest_ext:.1f} extrusions")
    print(f"    root flat          : {root_flat:.2f} mm "
          f"= {root_ext:.1f} extrusions")
    if crest_ext < MIN_CREST_EXTRUSIONS:
        problems.append(
            f"the crest is only {crest_flat:.3f}mm - {crest_ext:.1f} "
            f"extrusions at a {EXTRUSION_W}mm width.  This is the knife "
            f"edge that made the 1/4\"-20 thread print mushy.  Raise "
            f"thread_crest_flat or the pitch.")
    if root_ext < MIN_CREST_EXTRUSIONS:
        problems.append(
            f"the root is only {root_flat:.3f}mm - {root_ext:.1f} "
            f"extrusions.  A root narrower than the nozzle fills in, and "
            f"the mating crest then bottoms out before the flanks touch.")

    # ---- overhang ------------------------------------------------------
    #
    # Printed with the cylinder axis vertical, the underside of each
    # thread flank is unsupported.  A flank at `flank_ang` from the
    # perpendicular leans (90 - flank_ang) away from vertical.
    #
    # Steeper flanks are SAFER here, which is the opposite of the usual
    # intuition, and is why this thread uses 60 degrees rather than the
    # 45 that a trapezoidal form would normally get.
    print()
    print("  PRINTABILITY")
    overhang = 90.0 - flank_ang
    print(f"    flank overhang     : {overhang:.0f} deg from vertical")
    if overhang > MAX_OVERHANG:
        problems.append(
            f"the flanks overhang {overhang:.0f} deg from vertical, past "
            f"the {MAX_OVERHANG:.0f} deg limit - they would droop into the "
            f"groove below.  RAISE thread_flank_ang; steeper is safer.")

    # The helix itself tilts the thread, and that tilt is not symmetric:
    # it adds to the overhang on one side of the part and subtracts on the
    # other.  On a large diameter it is tiny, but it is worth printing
    # rather than assuming, because it grows as the diameter shrinks.
    helix_ang = math.degrees(math.atan2(lead, 2 * math.pi * (r0 + depth / 2)))
    print(f"    helix angle        : {helix_ang:.2f} deg")
    print(f"    worst-case overhang: {overhang + helix_ang:.1f} deg")
    if overhang + helix_ang > MAX_OVERHANG:
        problems.append(
            f"with the helix tilt the worst flank overhangs "
            f"{overhang + helix_ang:.1f} deg, past {MAX_OVERHANG:.0f}")

    # ---- clearance -----------------------------------------------------
    print()
    print("  FIT")
    print(f"    clearance per face : {clr:.2f} mm")
    print(f"    backlash, axial    : {2 * clr / math.sin(math.radians(flank_ang)):.2f} mm")
    if clr < 0.15:
        problems.append(
            f"a {clr:.2f}mm clearance will seize on a printed thread this "
            f"large - elephant's foot alone eats more than that")
    if clr > depth / 2:
        problems.append(
            f"clearance {clr:.2f}mm is more than half the {depth:.2f}mm "
            f"depth - the flanks would barely engage")

    # ---- engagement and effort ----------------------------------------
    print()
    print("  ENGAGEMENT")
    crests = engage / pitch
    turns = engage / lead
    print(f"    engaged length     : {engage:.1f} mm")
    print(f"    crests engaged     : {crests:.1f}")
    print(f"    turns to close     : {turns:.2f}")
    if crests < 3:
        problems.append(
            f"only {crests:.1f} thread crests engage - too few to share "
            f"the load; the first one carries most of it and strips")
    if turns > 3.5:
        problems.append(
            f"{turns:.1f} turns to open is tedious with cold hands.  Add "
            f"a start rather than shortening the engagement.")

    # ---- strength ------------------------------------------------------
    #
    # Not the governing case - nobody hangs a load off this lid - but
    # worth a number, because the failure mode of an over-tightened lid is
    # stripping the threads rather than breaking the wall.
    shear_area = math.pi * 2 * (r0 + depth / 2) * crests * root_flat
    strip_n = shear_area * PLA_SHEAR
    print()
    print("  STRENGTH")
    print(f"    thread shear area  : {shear_area:.0f} mm^2")
    print(f"    axial load to strip: {strip_n / 1000:.1f} kN")

    print()
    print("-" * 62)
    if problems:
        print("FAIL")
        for line in problems:
            print(f"  - {line}")
        return 1

    print("PASS - the thread is printable, engages properly, and opens "
          "in a reasonable number of turns")
    return 0


if __name__ == "__main__":
    sys.exit(main())
