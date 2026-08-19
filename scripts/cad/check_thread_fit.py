"""Screw a printed thread together and measure whether it binds.

A thread is the one feature in this project where being "obviously right"
in CAD means nothing.  The male and female are generated from the same
profile, so an error in the clearance appears in BOTH and they still nest
perfectly.  That is exactly how the Peak Design bracket ended up with a
latch that could not move: the part and its relief came from one outline,
so the mistake cancelled itself out of every check that existed.

So this builds the two halves as SEPARATE solids and physically assembles
them, the same way check_pd_sweep.py rotates the latch against the body.

Four measurements, and the last one is the important one:

  free        assembled at rest.  Shared volume must be ~0, or the
              thread is a press fit and will not turn.

  screwed     driven down the helix through a full engagement.  Still
              ~0, or something binds part way in - usually a lead-in
              chamfer, since a helix is otherwise invariant under its
              own screw motion and the middle cannot bind if the ends
              do not.

  lifted      pulled straight up WITHOUT rotating.  Must be LARGE.
              This is what proves the flanks actually interlock.  A
              thread with far too much clearance passes the first two
              tests perfectly and then pulls apart in your hand.

  miscoupled  rotated but deliberately NOT lifted by the matching
              amount.  Must also be large.  This one tests the TEST:
              it is a fault injected on purpose, and if the harness
              cannot see it then a real lead or handedness error would
              go unnoticed too.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_thread_fit.py
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

# Shared volume below this counts as "not touching".  Two surfaces held
# apart by a real clearance still register a few cubic millimetres once
# they are tessellated into flat triangles, and on a 140mm thread there is
# a lot of surface for that to accumulate over.
TOUCH_TOL = 40.0     # mm^3

# And this much shared volume means the parts are genuinely interfering.
BLOCK_MIN = 400.0    # mm^3

TEST_LEN = 12.0      # mm of thread on the test article - enough for
                     # 1.5 turns at an 8mm lead, so end effects are in


def find_openscad() -> Path:
    for path in OPENSCAD_CANDIDATES:
        if path.exists():
            return path
    raise SystemExit("OpenSCAD not found - install it or edit OPENSCAD_CANDIDATES")


def render(openscad: Path, part: str, params: dict, out: Path) -> trimesh.Trimesh:
    """Build one half of the pair straight from thread_lib."""
    args = "\n".join(f"{k} = {v};" for k, v in params.items())
    scad = MODELS / f".threadfit_{part}.scad"
    scad.write_text(
        "include <thread_lib.scad>\n"
        f"{args}\n"
        f'thread_lib_demo = "none";\n'
        f"_fit_{part}();\n"
        "\n"
        # Named arguments throughout.  These two modules have different
        # signatures - female_thread_void takes a clearance where
        # male_thread takes crest_flat - so a positional call silently
        # feeds the wrong number into the wrong slot.
        "module _fit_plug() {\n"
        "    union() {\n"
        "        cylinder(r = r0, h = tlen + 4);\n"
        "        male_thread(r0 = r0, pitch = pitch, length = tlen,\n"
        "                    starts = starts, crest_flat = crest_flat,\n"
        "                    root_flat = root_flat, flank_ang = flank_ang,\n"
        "                    seg = seg);\n"
        "    }\n"
        "}\n"
        "\n"
        "module _fit_socket() {\n"
        "    depth = thread_depth(pitch, crest_flat, root_flat, flank_ang);\n"
        "    difference() {\n"
        "        cylinder(r = r0 + depth + clr + 3, h = tlen + 4);\n"
        "        translate([0, 0, -0.01])\n"
        "            cylinder(r = r0 + clr, h = tlen + 4.02);\n"
        "        female_thread_void(r0 = r0, pitch = pitch, length = tlen,\n"
        "                           starts = starts, clr = clr,\n"
        "                           crest_flat = crest_flat,\n"
        "                           root_flat = root_flat,\n"
        "                           flank_ang = flank_ang, seg = seg);\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [str(openscad), "-o", str(out), str(scad)],
            capture_output=True, text=True,
        )
    finally:
        scad.unlink(missing_ok=True)

    if not out.exists() or out.stat().st_size < 200:
        sys.stderr.write((result.stderr or "")[-2000:])
        raise SystemExit(f"OpenSCAD produced nothing for {part}")

    mesh = trimesh.load(out)
    if not mesh.is_watertight:
        raise SystemExit(
            f"the {part} came out of OpenSCAD not watertight - the sweep "
            f"has a hole in it, and every measurement below would be "
            f"meaningless")
    return mesh


def shared_volume(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    """How much solid the two parts try to occupy at the same time."""
    try:
        both = a.intersection(b)
    except Exception:
        return float("nan")
    if both is None or both.is_empty:
        return 0.0
    return abs(float(both.volume))


def placed(mesh: trimesh.Trimesh, spin_deg: float, lift: float) -> trimesh.Trimesh:
    """A copy of the socket, spun about Z and raised."""
    out = mesh.copy()
    out.apply_transform(trimesh.transformations.rotation_matrix(
        math.radians(spin_deg), [0, 0, 1]))
    out.apply_translation([0, 0, lift])
    return out


def main() -> int:
    openscad = find_openscad()
    TMP.mkdir(exist_ok=True)

    pitch, starts = 4.0, 2
    crest_flat = root_flat = 1.0
    flank_ang = 60.0
    clr = 0.35
    r0 = 69.2
    lead = pitch * starts

    params = dict(
        r0=r0, pitch=pitch, starts=starts, clr=clr,
        crest_flat=crest_flat, root_flat=root_flat, flank_ang=flank_ang,
        tlen=TEST_LEN, seg=180,
    )

    print("=== thread fit ===")
    print(f"  minor dia {2 * r0:.1f} mm, pitch {pitch} mm, {starts} starts, "
          f"lead {lead} mm, clearance {clr} mm")
    print(f"  test article {TEST_LEN} mm long "
          f"({TEST_LEN / lead:.2f} turns of engagement)")
    print()

    plug = render(openscad, "plug", params, TMP / "thread_plug.stl")
    socket = render(openscad, "socket", params, TMP / "thread_socket.stl")
    print(f"  plug   {plug.volume / 1000:6.2f} cm^3  watertight, "
          f"{plug.body_count} body")
    print(f"  socket {socket.volume / 1000:6.2f} cm^3  watertight, "
          f"{socket.body_count} body")

    problems: list[str] = []

    # ---- free at rest --------------------------------------------------
    print()
    print("  FREE TO TURN")
    free = shared_volume(plug, socket)
    print(f"    at rest            : {free:8.1f} mm^3")
    if free > TOUCH_TOL:
        problems.append(
            f"the halves share {free:.0f}mm^3 sitting still - the thread "
            f"is an interference fit and will not turn.  Raise thread_clr.")

    # ---- driven down the helix ----------------------------------------
    #
    # A helix maps onto itself under its own screw motion, so in the
    # middle of the engagement this cannot bind if the rest fits.  What it
    # DOES catch is the ends: the lead-in chamfers and the square trims
    # are not helical, and they are where a real thread jams.
    print()
    print("  SCREWED DOWN")
    worst_screw = 0.0
    for spin in range(0, 721, 45):
        lift = lead * spin / 360.0
        vol = shared_volume(plug, placed(socket, spin, lift))
        worst_screw = max(worst_screw, vol)
        if spin % 180 == 0:
            print(f"    {spin:4d} deg           : {vol:8.1f} mm^3")
    print(f"    worst over stroke  : {worst_screw:8.1f} mm^3")
    if worst_screw > TOUCH_TOL:
        problems.append(
            f"the halves foul by {worst_screw:.0f}mm^3 part way down the "
            f"helix - almost certainly the lead-in chamfer, since the "
            f"middle of a helix cannot bind on its own")

    # ---- pulled straight up -------------------------------------------
    #
    # The check that proves the thread is a thread.  Clearance alone would
    # sail through everything above.
    print()
    print("  INTERLOCK  (pulled up without turning - must be blocked)")
    worst_lift = float("inf")
    for lift in (0.8, 1.4, 2.0):
        vol = shared_volume(plug, placed(socket, 0, lift))
        worst_lift = min(worst_lift, vol)
        print(f"    lifted {lift:.1f} mm       : {vol:8.1f} mm^3")
    if worst_lift < BLOCK_MIN:
        problems.append(
            f"lifting the socket straight up only meets {worst_lift:.0f}mm^3 "
            f"of resistance - the flanks are not really interlocking and "
            f"the lid would pull off.  Reduce thread_clr or deepen the "
            f"thread.")

    # ---- injected fault ------------------------------------------------
    #
    # Deliberately wrong: spun, but lifted by the wrong amount.  If this
    # does not register, the harness is blind and every PASS above is
    # worthless.  A test that cannot fail has not tested anything.
    print()
    print("  CONTROL  (deliberately miscoupled - the test must SEE this)")
    ctrl = shared_volume(plug, placed(socket, 90, lead * 90 / 360.0 + pitch / 2))
    print(f"    half a pitch out   : {ctrl:8.1f} mm^3")
    if ctrl < BLOCK_MIN:
        problems.append(
            f"a deliberately miscoupled assembly only shows {ctrl:.0f}mm^3 "
            f"of overlap.  The harness cannot see a fault it was handed on "
            f"purpose, so it could not see a real lead or handedness error "
            f"either.  Fix the check before trusting anything above it.")

    print()
    print("-" * 62)
    if problems:
        print("FAIL")
        for line in problems:
            print(f"  - {line}")
        return 1

    print("PASS - turns freely the whole way down, interlocks when pulled,")
    print("       and the harness demonstrably detects a bad assembly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
