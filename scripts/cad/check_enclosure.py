"""Probe the finished enclosure solid for the things a render will not show.

The model asserts a great deal about itself, and every one of those
asserts is checked against numbers the model also computed.  That catches
arithmetic mistakes and nothing else.  It cannot catch a feature that was
computed correctly and then removed by a later operation, which is the
failure this project keeps meeting: the ear fillets that a hull() quietly
erased, the scallops it filled in, the floor that ended up buried inside
a flange.  All of those passed every assert in the file.

So this measures the EXPORTED MESH, downstream of every boolean.

  seal        the labyrinth.  There is no gasket - the lid keeps water
              out by making it climb.  Rain has to get past the skirt,
              up over the shoulder, and then down over a rib that hangs
              into the mouth.  Measured here as the rib's real depth and
              its real clearance, read off the lid.

  weep        the drain holes.  A blind weep hole is worse than none:
              it collects water and holds it against the floor, and it
              looks perfect from every camera angle because the entry is
              there.  Probed with a rod driven along the hole's axis.

  ears        the carabiner holes, probed the same way.

  floor       the crown.  The floor is domed so water runs outward to
              the gutter and out of the weeps.  A floor that came out
              flat, or crowned the wrong way, would pool in the middle.

Each probe that must pass freely is paired with an oversized one that
must jam.  A harness that measures nothing reports a clean sweep, and
this is the only way to tell that apart from a part that is actually
right.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_enclosure.py
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models"
TMP = ROOT / ".tmp-cad"

OPENSCAD_CANDIDATES = [
    Path(r"C:\Program Files\OpenSCAD\openscad.exe"),
    Path("/usr/bin/openscad"),
    Path("/usr/local/bin/openscad"),
]

# A rod driven down a hole of nearly its own size touches the wall along
# a line, and a tessellated wall turns that into a row of slivers.  This
# is the amount of that noise being tolerated, not real interference.
CLEAR_TOL = 10.0      # mm^3

# How much louder a control has to be than that tolerance before it counts
# as having detected something.
#
# Expressed as a MULTIPLE rather than as a fixed volume, because the two
# features are nothing like the same size: a weep hole is 3mm across and
# only 5mm long, so an oversized rod in one can only ever overlap about
# 60mm^3 no matter how badly it fits.  A flat floor high enough to be
# meaningful for the 8mm ears is one the weep holes could never reach,
# and the check would fail on a part that is perfectly correct.
#
# What actually matters is not the absolute figure but the separation:
# the control has to be far enough clear of the noise that no amount of
# tessellation could produce it.
CONTROL_RATIO = 5.0

# How much the mesh may differ from what the model intended.  A tenth of
# a millimetre is below what the printer can resolve, so anything inside
# this is agreement.
DIM_TOL = 0.10        # mm

# Undersize applied to a probe so it is testing the hole rather than the
# tessellation of its own surface.
PROBE_UNDER = 0.50    # mm


def find_openscad() -> Path:
    for path in OPENSCAD_CANDIDATES:
        if path.exists():
            return path
    raise SystemExit("OpenSCAD not found - install it or edit OPENSCAD_CANDIDATES")


def run_scad(openscad: Path, body: str, out: Path | None) -> str:
    scad = MODELS / ".encaudit.scad"
    scad.write_text(body, encoding="utf-8")
    args = [str(openscad)]
    args += ["-o", str(out if out else TMP / "_null.stl"), str(scad)]
    try:
        result = subprocess.run(args, capture_output=True, text=True)
    finally:
        scad.unlink(missing_ok=True)
    return result.stderr or ""


def read_dimensions(openscad: Path) -> dict[str, float]:
    """Ask the model for its own numbers instead of restating them here.

    Copying them in would let the check and the thing being checked drift
    apart silently, and the check would go on passing while they did.
    """
    names = [
        "neck_ir", "lip_or", "lip_ir", "lip_h", "lip_clr",
        "z_lid_inner", "z_neck_top", "z_shoulder", "overall_h",
        "weep_entry_r", "weep_exit_r", "weep_d", "weep_count", "weep_tilt",
        "z_floor_top", "z_floor_apex", "floor_crown",
        "ear_hole_r", "ear_hole_d", "ear_count",
        "interior_r", "body_or",
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
        f"include <efhw_enclosure.scad>\nvariant_render_mode = \"{mode}\";\n",
        out,
    )
    if not out.exists() or out.stat().st_size < 200:
        sys.stderr.write(err[-2000:])
        raise SystemExit(f"OpenSCAD produced nothing for {mode}")
    mesh = trimesh.load(out)
    if not mesh.is_watertight:
        raise SystemExit(
            f"the {mode} came out not watertight - every measurement "
            f"below would be meaningless")
    return mesh


def shared(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    try:
        both = a.intersection(b)
    except Exception:
        return float("nan")
    if both is None or both.is_empty:
        return 0.0
    return abs(float(both.volume))


def rod(dia: float, p0, p1) -> trimesh.Trimesh:
    """A cylindrical probe between two points."""
    return trimesh.creation.cylinder(
        radius=dia / 2.0, segment=[np.asarray(p0, float), np.asarray(p1, float)])


def spun(mesh: trimesh.Trimesh, deg: float) -> trimesh.Trimesh:
    out = mesh.copy()
    out.apply_transform(trimesh.transformations.rotation_matrix(
        math.radians(deg), [0, 0, 1]))
    return out


def radii(mesh: trimesh.Trimesh) -> np.ndarray:
    return np.hypot(mesh.vertices[:, 0], mesh.vertices[:, 1])


def weep_probe(dia: float, dim: dict[str, float]) -> trimesh.Trimesh:
    """A rod lying along one weep hole's axis, over-run at both ends.

    Built from the entry and exit the model computed, so the probe follows
    the hole's real slope rather than a slope restated here.  Over-running
    both ends is what makes this a through-hole test: a rod that stops
    inside the floor would report clear whether or not it broke out.
    """
    entry = np.array([dim["weep_entry_r"], 0.0, dim["z_floor_top"]])
    exit_ = np.array([dim["weep_exit_r"], 0.0, 0.0])
    step = (exit_ - entry) / np.linalg.norm(exit_ - entry)
    return rod(dia, entry - step * 2.0, exit_ + step * 2.0)


def ear_probe(dia: float, dim: dict[str, float]) -> trimesh.Trimesh:
    """A vertical rod down one carabiner hole.

    The ears stand outboard of the wall, so a rod at this radius can only
    ever meet ear material.  Nothing else in the part reaches it.
    """
    r = dim["ear_hole_r"]
    return rod(dia, [r, 0.0, -2.0], [r, 0.0, dim["overall_h"] + 2.0])


def band_z(mesh: trimesh.Trimesh, r_lo: float, r_hi: float) -> tuple[float, float]:
    """The z range of whatever mesh lives in a radial band.

    The band has to be drawn slightly WIDER than the feature, not
    narrower.  A revolved flat annulus has vertices only at its inner and
    outer edges - there is nothing in between to find - so insetting the
    band to avoid edge effects is exactly how to miss the feature
    entirely and measure something unrelated further up the part.
    """
    r = radii(mesh)
    keep = (r >= r_lo) & (r <= r_hi)
    if not keep.any():
        return float("nan"), float("nan")
    z = mesh.vertices[keep, 2]
    return float(z.min()), float(z.max())


def main() -> int:
    openscad = find_openscad()
    TMP.mkdir(exist_ok=True)

    dim = read_dimensions(openscad)

    print("=== enclosure audit ===")
    body = render(openscad, "body", TMP / "audit_body.stl")
    lid = render(openscad, "lid_placed", TMP / "audit_lid.stl")
    print(f"  body {body.volume / 1000:6.1f} cm^3, "
          f"{body.body_count} body, {len(body.faces)} faces")
    print(f"  lid  {lid.volume / 1000:6.1f} cm^3, "
          f"{lid.body_count} body, {len(lid.faces)} faces")

    problems: list[str] = []

    # ---- the labyrinth --------------------------------------------------
    #
    # Measured on the lid, in the radial band the rib occupies.  Its
    # lowest point is the bottom of the rib, and how far that sits below
    # the top of the neck is the engagement - the height water would have
    # to climb to get in.
    print()
    print("  SEAL - THE LABYRINTH")
    lip_lo, _ = band_z(lid, dim["lip_ir"] - 0.05, dim["lip_or"] + 0.05)
    rib_h = dim["z_lid_inner"] - lip_lo
    engage = dim["z_neck_top"] - lip_lo
    gap = dim["neck_ir"] - dim["lip_or"]

    print(f"    rib depth, as built        : {rib_h:8.2f} mm "
          f"(drawn {dim['lip_h']:.2f})")
    print(f"    reaches below the neck top : {engage:8.2f} mm")
    print(f"    clearance to the mouth     : {gap:8.2f} mm per face")
    print(f"    path length : clearance    : {rib_h / gap:8.1f} : 1")

    if abs(rib_h - dim["lip_h"]) > DIM_TOL:
        problems.append(
            f"the sealing rib measures {rib_h:.2f}mm but was drawn "
            f"{dim['lip_h']:.2f}mm - something cut it back after it was "
            f"made, and the labyrinth is shorter than the model believes.")
    if engage <= 0.5:
        problems.append(
            f"the rib only reaches {engage:.2f}mm below the top of the "
            f"neck, so it is barely inside the mouth.  There is no "
            f"labyrinth - water has a straight path in.")

    # ---- drainage -------------------------------------------------------
    print()
    print("  WEEP HOLES")
    clear_d = dim["weep_d"] - PROBE_UNDER
    worst, worst_at = 0.0, 0.0
    for i in range(int(dim["weep_count"])):
        deg = 22.5 + i * 360.0 / dim["weep_count"]
        vol = shared(spun(weep_probe(clear_d, dim), deg), body)
        if vol > worst:
            worst, worst_at = vol, deg
    print(f"    {clear_d:.1f} mm rod through all "
          f"{int(dim['weep_count'])}    : {worst:8.1f} mm^3 "
          f"(worst at {worst_at:.1f} deg)")
    if worst > CLEAR_TOL:
        problems.append(
            f"a {clear_d:.1f}mm rod driven down the weep hole at "
            f"{worst_at:.0f} degrees hits {worst:.0f}mm^3 of body - the "
            f"hole is blind, and the box will hold water rather than "
            f"drain it.")

    fat = dim["weep_d"] + 2.0
    fat_vol = shared(spun(weep_probe(fat, dim), 22.5), body)
    print(f"    control, {fat:.1f} mm rod       : {fat_vol:8.1f} mm^3")
    if fat_vol < CLEAR_TOL * CONTROL_RATIO:
        problems.append(
            f"a {fat:.1f}mm rod in a {dim['weep_d']:.1f}mm hole reported "
            f"only {fat_vol:.0f}mm^3 - this probe is not measuring "
            f"anything, so the pass above means nothing either.")

    # ---- carabiner ears -------------------------------------------------
    print()
    print("  CARABINER HOLES")
    clear_d = dim["ear_hole_d"] - PROBE_UNDER
    worst, worst_at = 0.0, 0.0
    for i in range(int(dim["ear_count"])):
        deg = 45.0 + i * 360.0 / dim["ear_count"]
        vol = shared(spun(ear_probe(clear_d, dim), deg), body)
        if vol > worst:
            worst, worst_at = vol, deg
    print(f"    {clear_d:.1f} mm rod through all "
          f"{int(dim['ear_count'])}    : {worst:8.1f} mm^3 "
          f"(worst at {worst_at:.1f} deg)")
    if worst > CLEAR_TOL:
        problems.append(
            f"a {clear_d:.1f}mm rod through the ear at {worst_at:.0f} "
            f"degrees hits {worst:.0f}mm^3 - the hole did not break "
            f"through and no carabiner will pass it.")

    # The control has to be spun onto a real ear, the same as the probe
    # above.  Left at zero degrees it hangs in the air between two of
    # them, reports nothing, and looks exactly like a probe that is not
    # working - which is what it did on the first run.
    fat = dim["ear_hole_d"] + 3.0
    fat_vol = shared(spun(ear_probe(fat, dim), 45.0), body)
    print(f"    control, {fat:.1f} mm rod       : {fat_vol:8.1f} mm^3")
    if fat_vol < CLEAR_TOL * CONTROL_RATIO:
        problems.append(
            f"a {fat:.1f}mm rod in a {dim['ear_hole_d']:.1f}mm hole "
            f"reported only {fat_vol:.0f}mm^3 - the ear probe is not "
            f"measuring anything.")

    # ---- the floor ------------------------------------------------------
    #
    # Read as the difference between the middle of the floor and its
    # edge.  If it came out flat the two are equal, and water sits where
    # it lands instead of running to the weeps.
    print()
    print("  FLOOR CROWN")
    _, apex = band_z(body, 0.0, 6.0)
    edge_lo, _ = band_z(body, dim["weep_entry_r"] - 1.0,
                        dim["weep_entry_r"] + 1.0)
    crown = apex - dim["z_floor_top"]
    print(f"    middle of the floor        : {apex:8.2f} mm")
    print(f"    gutter at the wall         : {dim['z_floor_top']:8.2f} mm")
    print(f"    fall, as built             : {crown:8.2f} mm "
          f"(drawn {dim['floor_crown']:.2f})")
    if abs(crown - dim["floor_crown"]) > DIM_TOL:
        problems.append(
            f"the floor falls {crown:.2f}mm from the middle to the gutter "
            f"but was drawn to fall {dim['floor_crown']:.2f}mm - it is not "
            f"the shape the model thinks, and may not drain.")
    if crown <= 0:
        problems.append(
            "the floor does not fall outward at all - water would pool in "
            "the middle instead of reaching the weep holes.")

    print()
    if problems:
        print("=== FAIL ===")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("=== PASS ===")
    print("  the labyrinth is the depth it was drawn, both sets of holes")
    print("  break clean through, and the floor falls to the weeps.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
