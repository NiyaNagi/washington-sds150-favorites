"""Lay a coax into the cable slot and screw the lid down on top of it.

The slots are open at the top so a cable that already has a PL-259 on it
can be dropped in sideways, instead of being threaded through a hole the
plug will not pass.  That convenience is the whole point of the feature,
and it is also what makes it easy to get wrong, because two different
things have to be true at once and neither is visible in a render:

  the cable must be able to get IN     - nothing may overhang the slot
                                         on the way down, and the neck's
                                         thread crest stands 0.65mm
                                         further out than the bore, so
                                         this is a real risk and not a
                                         theoretical one

  the lid must not touch it once in    - the lid turns one and a half
                                         times to close.  A cable it
                                         caught would not simply be
                                         squashed, it would be WOUND
                                         around the neck and chafed
                                         through, which is worse

Measurements, in the order a person would do them:

  breaks through   the slot connects the inside to the outside.  Cheap,
                   but a slot cut 1mm short of the bore looks perfect
                   from every camera angle.

  drop in          the cable lowered down the slot in steps.  Shared
                   volume must stay ~0 the whole way.  A single step
                   that spikes is a ledge, and a ledge means the cable
                   has to be forced or fed from the end.

  seated           the seat's width, measured rather than asserted.  A
                   0.2mm squeeze on a 5mm cable is a firm grip in the
                   hand and about one cubic millimetre of shared volume
                   on paper, so asking "do they overlap enough" answers
                   nothing.  Instead the seat is probed with cylinders
                   until the largest one that passes freely is found,
                   which is the width the slot actually came out at.

  lid closed       the assembled lid against the seated cable.  Must be
                   EXACTLY zero.  This is the one that matters.

  oversize         a cable too fat for the slot, run through the same
                   drop-in test.  Must fail loudly.  Without it, a
                   harness that silently measures nothing would report
                   four passes and mean none of them.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_cable_slot.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models"
TMP = ROOT / ".tmp-cad"

OPENSCAD_CANDIDATES = [
    Path(r"C:\Program Files\OpenSCAD\openscad.exe"),
    Path("/usr/bin/openscad"),
    Path("/usr/local/bin/openscad"),
]

# A cylinder laid against a flat wall touches it along a LINE, and a
# tessellated cylinder turns that line into a row of shallow slivers.
# Over 30mm of buried length there is enough of it to register, so
# "not touching" cannot mean literally zero here.
TOUCH_TOL = 15.0      # mm^3

# The lid is different.  It is nowhere near the cable by design, so any
# shared volume at all means the clearance calculation is wrong.
LID_TOL = 1.0         # mm^3

# A cylinder in a slot barely narrower than itself shares almost no
# volume - a tenth of a millimetre each side over five millimetres of
# wall is about one cubic millimetre in total.  So the seat is measured
# by width instead, and this is only used to decide "does it touch at
# all" while narrowing in on that width.
SEAT_TOUCH = 0.5      # mm^3

# How close the measured seat has to land on the drawing.  One layer
# width, since that is the finest distinction the printer can make
# anyway.
SEAT_TOL = 0.42       # mm

# How far down the slot to sample.  Twelve steps over the descent is
# enough to catch a ledge without spending a minute per run.
DROP_STEPS = 12


def find_openscad() -> Path:
    for path in OPENSCAD_CANDIDATES:
        if path.exists():
            return path
    raise SystemExit("OpenSCAD not found - install it or edit OPENSCAD_CANDIDATES")


def run_scad(openscad: Path, body: str, out: Path | None) -> str:
    """Render or evaluate a scratch file that includes the enclosure."""
    scad = MODELS / ".cableslot.scad"
    scad.write_text(body, encoding="utf-8")
    args = [str(openscad)]
    args += ["-o", str(out)] if out else ["-o", str(TMP / "_null.stl")]
    args += [str(scad)]
    try:
        result = subprocess.run(args, capture_output=True, text=True)
    finally:
        scad.unlink(missing_ok=True)
    return result.stderr or ""


def read_dimensions(openscad: Path) -> dict[str, float]:
    """Ask the model for its own numbers rather than restating them.

    Copying the derived values into this file would mean the check and
    the thing being checked could drift apart, and the check would keep
    passing while it did.
    """
    names = [
        "z_cable_ctr", "z_cable_top", "z_cable_bot", "z_shoulder",
        "cable_d", "cable_slot_w", "cable_mouth_w",
        "body_or", "interior_r", "cable_reach_r", "neck_ir",
        "z_neck_top", "z_cable_slot_top", "cable_slot_count",
    ]
    listing = ", ".join(f'"{n}", {n}' for n in names)
    err = run_scad(
        openscad,
        "include <efhw_enclosure.scad>\n"
        'variant_render_mode = "none";\n'
        f'echo("DIMS", {listing});\n',
        None,
    )
    values: dict[str, float] = {}
    for line in err.splitlines():
        if not line.startswith('ECHO: "DIMS"'):
            continue
        fields = [f.strip().strip('"') for f in line.split(",")[1:]]
        for name, value in zip(fields[0::2], fields[1::2]):
            values[name] = float(value)
    missing = [n for n in names if n not in values]
    if missing:
        sys.stderr.write(err[-2000:])
        raise SystemExit(f"could not read {missing} out of the model")
    return values


def render(openscad: Path, mode: str, out: Path) -> trimesh.Trimesh:
    err = run_scad(
        openscad,
        "include <efhw_enclosure.scad>\n"
        f'variant_render_mode = "{mode}";\n',
        out,
    )
    if not out.exists() or out.stat().st_size < 200:
        sys.stderr.write(err[-2000:])
        raise SystemExit(f"OpenSCAD produced nothing for {mode}")
    mesh = trimesh.load(out)
    if not mesh.is_watertight:
        raise SystemExit(
            f"the {mode} came out not watertight - every volume measured "
            f"against it below would be meaningless")
    return mesh


def cable(dia: float, dim: dict[str, float], z: float,
          inner: float | None = None) -> trimesh.Trimesh:
    """A length of coax lying in one slot, pointing out along +X.

    The slots sit at 0 and 180 degrees.  Testing the one at 0 is enough:
    they are the same geometry rotated, so a fault in one is a fault in
    both, and rendering half as much intersection keeps this quick.
    """
    if inner is None:
        # Started inboard of where the slot is supposed to reach, so a
        # slot that stops short of breaking through shows as a collision.
        inner = dim["cable_reach_r"] + 0.5
    outer = dim["body_or"] + 15.0
    rod = trimesh.creation.cylinder(radius=dia / 2.0, height=outer - inner)
    rod.apply_transform(trimesh.transformations.rotation_matrix(
        1.5707963267948966, [0, 1, 0]))
    rod.apply_translation([(inner + outer) / 2.0, 0.0, z])
    return rod


def shared(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    try:
        both = a.intersection(b)
    except Exception:
        return float("nan")
    if both is None or both.is_empty:
        return 0.0
    return abs(float(both.volume))


def drop_in(body: trimesh.Trimesh, dim: dict[str, float],
            dia: float) -> tuple[float, float]:
    """Lower the cable down the slot and return the worst step and its z.

    Starts above the top of the neck, because that is where a hand would
    start: the whole point of the channel is that the cable goes in from
    open air, not from somewhere it has already been threaded to.

    Sampled rather than swept.  A swept solid would answer "does it fit
    anywhere along the path" as one number, which is what we want, but it
    would not say WHERE it fouled, and where is the only part that helps
    you fix it.
    """
    top = dim["z_cable_slot_top"] + dia / 2.0 + 1.0
    bottom = dim["z_cable_ctr"] + 0.6      # stop just above the grip
    worst, worst_z = 0.0, top
    for i in range(DROP_STEPS + 1):
        z = top + (bottom - top) * i / DROP_STEPS
        vol = shared(cable(dia, dim, z), body)
        if vol > worst:
            worst, worst_z = vol, z
    return worst, worst_z


def seat_width(body: trimesh.Trimesh, dim: dict[str, float]) -> float:
    """The widest cylinder that sits in the seat without touching.

    Bisection on diameter.  This is the slot's built width, read off the
    mesh, and it is worth more than any number this script could be told:
    it is measured downstream of the hull, the radial sweep and the
    difference, so it catches a slot that was drawn correctly and then
    quietly altered by one of them.
    """
    lo, hi = 1.0, dim["cable_mouth_w"] + 2.0
    for _ in range(9):
        mid = (lo + hi) / 2.0
        if shared(cable(mid, dim, dim["z_cable_ctr"]), body) > SEAT_TOUCH:
            hi = mid
        else:
            lo = mid
    return lo


def main() -> int:
    openscad = find_openscad()
    TMP.mkdir(exist_ok=True)

    dim = read_dimensions(openscad)
    dia = dim["cable_d"]

    print("=== cable slot ===")
    print(f"  {int(dim['cable_slot_count'])} slots, open at the top, "
          f"for {dia:.1f} mm cable")
    print(f"  mouth {dim['cable_mouth_w']:.2f} closing to "
          f"{dim['cable_slot_w']:.2f} at the seat "
          f"({dia - dim['cable_slot_w']:+.2f} mm of grip)")
    print(f"  seat at z {dim['z_cable_ctr']:.2f}, cable crown at "
          f"{dim['z_cable_top']:.2f}, lid lands at "
          f"{dim['z_shoulder']:.2f}")
    print(f"  channel runs up to z {dim['z_cable_slot_top']:.2f}, clear of "
          f"the neck top at {dim['z_neck_top']:.2f}")
    print()

    body = render(openscad, "body", TMP / "cable_body.stl")
    lid = render(openscad, "lid_placed", TMP / "cable_lid_placed.stl")
    print(f"  body {body.volume / 1000:6.1f} cm^3, "
          f"{body.body_count} body, watertight")
    print(f"  lid  {lid.volume / 1000:6.1f} cm^3, "
          f"{lid.body_count} body, watertight")

    problems: list[str] = []

    # ---- does it go all the way through -------------------------------
    print()
    print("  BREAKS THROUGH THE WALL")
    probe = cable(1.0, dim, dim["z_cable_ctr"])
    blocked = shared(probe, body)
    print(f"    1mm probe, bore to outside : {blocked:8.1f} mm^3")
    if blocked > 2.0:
        problems.append(
            f"a 1mm probe laid along the slot still hits {blocked:.0f}mm^3 "
            f"of body - the slot does not reach the bore.  Lower "
            f"cable_reach_r.")

    # ---- lowering it in ------------------------------------------------
    print()
    print("  DROPPING THE CABLE IN")
    worst, worst_z = drop_in(body, dim, dia)
    print(f"    worst of {DROP_STEPS + 1} steps      : {worst:8.1f} mm^3 "
          f"at z {worst_z:.1f}")
    if worst > TOUCH_TOL:
        problems.append(
            f"the cable fouls the body by {worst:.0f}mm^3 at z {worst_z:.1f} "
            f"on the way down - something overhangs the slot and the cable "
            f"cannot be laid in, only threaded through from the end.")

    # ---- sitting in the bottom -----------------------------------------
    print()
    print("  SEATED")
    built = seat_width(body, dim)
    print(f"    seat width, as built       : {built:8.2f} mm "
          f"(drawn {dim['cable_slot_w']:.2f})")
    print(f"    grip on a {dia:.1f} mm cable    : "
          f"{dia - built:8.2f} mm")
    if abs(built - dim["cable_slot_w"]) > SEAT_TOL:
        problems.append(
            f"the seat measures {built:.2f}mm but was drawn "
            f"{dim['cable_slot_w']:.2f}mm.  Something between the profile "
            f"and the finished body changed its width.")
    elif built >= dia:
        problems.append(
            f"the seat measures {built:.2f}mm against a {dia:.1f}mm cable - "
            f"it does not grip, and the cable will fall out while the lid "
            f"is being screwed on.  Raise cable_grip.")

    # ---- the lid on top -------------------------------------------------
    print()
    print("  LID SCREWED DOWN")
    caught = shared(cable(dia, dim, dim["z_cable_ctr"]), lid)
    print(f"    lid against the cable      : {caught:8.1f} mm^3")
    if caught > LID_TOL:
        problems.append(
            f"the lid overlaps the seated cable by {caught:.0f}mm^3.  It "
            f"turns 1.5 times to close, so it would wind the cable around "
            f"the neck rather than just pinch it.  Raise cable_lid_clr.")

    # ---- and prove the test can fail ------------------------------------
    print()
    print("  CONTROL - A CABLE THAT SHOULD NOT FIT")
    fat = dim["cable_mouth_w"] + 3.0
    fat_worst, fat_z = drop_in(body, dim, fat)
    print(f"    {fat:.1f} mm cable, worst step   : {fat_worst:8.1f} mm^3 "
          f"at z {fat_z:.1f}")
    if fat_worst <= TOUCH_TOL:
        problems.append(
            f"a {fat:.1f}mm cable dropped into a {dim['cable_mouth_w']:.1f}mm "
            f"mouth reported only {fat_worst:.0f}mm^3 - this harness is not "
            f"measuring anything, so the passes above mean nothing either.")

    print()
    if problems:
        print("=== FAIL ===")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("=== PASS ===")
    print("  the cable drops in from above, the slot holds it, and the")
    print("  lid closes over it without touching.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
