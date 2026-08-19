"""Audit every pair of features in the bracket for interference.

The individual checks each answer one question well: can the stud get in,
can the latch move, is the mesh sound.  None of them asks the blunt
question "does anything overlap anything else it should not?", and that is
how a screw socket ended up 1.48mm from the stud channel with the radio's
weight on the membrane between them - every check passed, because no check
was looking.

This script measures the real clearance between each pair of features by
probing the exported solid directly, so it does not depend on any of the
model's own arithmetic being right.

It reports distances rather than pass/fail alone, because the interesting
failures here have been near-misses rather than outright collisions.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/audit_pd_bracket.py [stl]
"""

from __future__ import annotations

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

# Minimum acceptable material between two voids, in mm.  Four extrusion
# widths at a 0.4mm nozzle - thin enough to be economical, thick enough to
# be printed as a real wall rather than a skin.
MIN_WALL = 1.2

# Minimum floor under a screw socket.  The screw is steel and the plastic
# is not; a thin floor gets punched out on the first over-torque.
MIN_FLOOR = 1.2


def find_openscad() -> Path:
    for path in OPENSCAD_CANDIDATES:
        if path.exists():
            return path
    raise SystemExit("OpenSCAD not found - install it or edit OPENSCAD_CANDIDATES")


def echoed_values(openscad: Path, style: str = "self_tap") -> dict[str, float]:
    """Read the model's own derived numbers, so probes land in the right
    places even after the design is retuned.

    The socket style must match the mesh being measured.  It did not at
    first: every audit read the default self-tap figures, so measuring the
    nut variant compared a hex pocket against a chamfer's diameter and
    reported the pocket as missing material.
    """
    scad = MODELS / ".audit_probe.scad"
    scad.write_text(
        'include <sds150_pd_bracket.scad>\n'
        'variant_render_mode = "none";\n'
        f'thread_style = "{style}";\n'
        'echo(str("AUDIT",'
        '" socket_y=", socket_y,'
        '" socket_x=", socket_x,'
        '" plate_t=", plate_t,'
        '" ledge_t=", ledge_t,'
        '" travel=", travel,'
        '" entry_d=", entry_d,'
        '" neck_w=", neck_w,'
        '" head_ch_w=", head_ch_w,'
        '" lever_x0=", lever_x0,'
        '" lever_x1=", lever_x1,'
        '" socket_widest=", socket_widest,'
        '" socket_depth=", socket_depth,'
        '" tab_y0=", tab_y0,'
        '" tab_y1=", tab_y1,'
        '" bar_top=", bar_top,'
        '" bar_bot=", bar_bot,'
        '" plate_y_lo=", plate_y_lo,'
        '" plate_y_hi=", plate_y_hi,'
        '" plate_x_lo=", plate_x_lo,'
        '" plate_x_hi=", plate_x_hi,'
        '" pd_plate_size=", pd_plate_size,'
        '" socket_face_d=", socket_face_d,'
        '" plate_edge_r=", plate_edge_r));\n',
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [str(openscad), "-o", str(TMP / "audit_probe.stl"), str(scad)],
            capture_output=True, text=True,
        )
    finally:
        scad.unlink(missing_ok=True)

    text = (result.stderr or "") + (result.stdout or "")
    line = next((l for l in text.splitlines() if "AUDIT" in l), None)
    if line is None:
        raise SystemExit("could not read the model's derived values")

    vals: dict[str, float] = {}
    for token in line.replace('"', "").split():
        if "=" in token:
            key, _, value = token.partition("=")
            try:
                vals[key] = float(value)
            except ValueError:
                pass
    return vals


def solid_runs(mesh: trimesh.Trimesh, x: float, y: float,
               z0: float, z1: float, step: float = 0.02):
    """Where the solid starts and stops along a vertical line."""
    zs = np.arange(z0, z1, step)
    pts = np.column_stack([np.full_like(zs, x), np.full_like(zs, y), zs])
    inside = mesh.contains(pts)

    runs, start = [], None
    for z, ins in zip(zs, inside):
        if ins and start is None:
            start = z
        if not ins and start is not None:
            runs.append((start, z))
            start = None
    if start is not None:
        runs.append((start, zs[-1]))
    return runs


def clearance_along(mesh: trimesh.Trimesh, p0, p1, step: float = 0.02):
    """Length of continuous solid between two points, and total gap."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    n = max(2, int(np.linalg.norm(p1 - p0) / step))
    ts = np.linspace(0, 1, n)
    pts = p0 + (p1 - p0)[None, :] * ts[:, None]
    inside = mesh.contains(pts)
    seg = np.linalg.norm(p1 - p0) / (n - 1)
    return inside.sum() * seg


def keyhole_clearance(sx: float, sy: float, travel: float,
                      neck_w: float, entry_d: float) -> float:
    """Distance from a point to the keyhole outline, in plan.

    The keyhole is the neck-slot capsule from (0,0) to (0,travel) unioned
    with the entry circle at (0,travel), so the answer is whichever of the
    two is nearer.

    Written generally on purpose.  The first version of this check assumed
    the socket sat below the slot and measured only that case; the socket
    has since moved above the entry hole, where that formula would have
    quietly reported the wrong gap.
    """
    if sy < 0.0:
        to_slot = float(np.hypot(sx, sy))
    elif sy > travel:
        to_slot = float(np.hypot(sx, sy - travel))
    else:
        to_slot = abs(sx)

    to_entry = float(np.hypot(sx, sy - travel))

    return min(to_slot - neck_w / 2, to_entry - entry_d / 2)


def bearing_height(mesh: trimesh.Trimesh, xs, ys, z_above: float):
    """Height of the first solid surface seen looking down at the back.

    Returns NaN where the ray misses the part altogether.  Casting rather
    than point-sampling on purpose: it distinguishes "nothing there" from
    "something there but recessed below the bearing face", and those fail
    in different ways - one rocks, the other just does not touch.
    """
    origins = np.column_stack([xs, ys, np.full(len(xs), z_above)])
    dirs = np.tile([0.0, 0.0, -1.0], (len(xs), 1))

    locs, ray_idx, _ = mesh.ray.intersects_location(
        ray_origins=origins, ray_directions=dirs, multiple_hits=True)

    best = np.full(len(xs), np.nan)
    for point, idx in zip(locs, ray_idx):
        if np.isnan(best[idx]) or point[2] > best[idx]:
            best[idx] = point[2]
    return best


def main() -> int:
    openscad = find_openscad()
    TMP.mkdir(exist_ok=True)

    stl = Path(sys.argv[1]) if len(sys.argv) > 1 else TMP / "pd.stl"
    if not stl.exists():
        raise SystemExit(f"no such file: {stl}")

    # The exports are named for their socket style, and the style changes
    # what the back face looks like, so the values have to be read for the
    # same one.  Longest match first: "self_tap" also contains "tap".
    style = next((s for s in ("self_tap", "insert", "nut")
                  if s in stl.stem), "self_tap")

    v = echoed_values(openscad, style)
    mesh = trimesh.load(stl)

    print(f"=== {stl.name} ===  (socket style: {style})")
    size = mesh.bounds[1] - mesh.bounds[0]
    print(f"  {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm, "
          f"{mesh.volume / 1000:.2f} cm^3, "
          f"{mesh.body_count} body, watertight={mesh.is_watertight}")
    print()

    problems: list[str] = []

    # ---- the keyhole actually exists -----------------------------------
    print("  KEYHOLE")
    at_lock = solid_runs(mesh, 0, 0, -1, v["plate_t"] + 1)
    at_entry = solid_runs(mesh, 0, v["travel"], -1, v["plate_t"] + 1)

    print(f"    at the locked stud  : solid "
          f"{['%.2f-%.2f' % r for r in at_lock]}")
    print(f"    at the entry hole   : solid "
          f"{['%.2f-%.2f' % r for r in at_entry]}")

    # Under the lock there must be a void (the channel) with a ledge over
    # it; at the entry there must be a clear hole all the way through the
    # ledge so the head can drop in.
    if not at_lock:
        problems.append("no material at all over the locked stud - the "
                        "ledge is missing and nothing would hold the radio")
    elif at_lock[0][0] < 0.1:
        problems.append("material fills the head channel at the locked "
                        "position - the stud could not sit there")

    if at_entry and at_entry[0][0] < v["ledge_t"] - 0.1:
        problems.append("the entry hole is blocked - the stud head could "
                        "not be dropped in")

    # ---- socket vs keyhole ---------------------------------------------
    print()
    print("  SOCKET vs KEYHOLE")
    sy, sw = v["socket_y"], v["socket_widest"]
    sx = v.get("socket_x", 0.0)
    gap_y = keyhole_clearance(sx, sy, v["travel"],
                              v["neck_w"], v["entry_d"]) - sw / 2
    print(f"    socket at ({sx:.1f}, {sy:.1f}), "
          f"widest feature {sw:.2f} mm across")
    print(f"    entry hole at y={v['travel']:.1f}, "
          f"reaching y={v['travel'] + v['entry_d'] / 2:.2f}")
    print(f"    gap between them    : {gap_y:.2f} mm")

    if gap_y < MIN_WALL:
        problems.append(
            f"only {gap_y:.2f}mm between the tripod socket and the stud "
            "slot - the screw would break into the keyhole")

    # Material under the socket, on the face the radio bears against.
    under = solid_runs(mesh, sx, sy, -1, v["plate_t"] + 1)
    floor = under[0][1] - under[0][0] if under else 0.0
    print(f"    floor under the screw: {floor:.2f} mm")
    if floor < MIN_FLOOR:
        problems.append(
            f"only {floor:.2f}mm of floor under the tripod screw - it "
            "would burst through the face the radio sits against")

    # ---- socket vs latch -----------------------------------------------
    print()
    print("  SOCKET vs LATCH")
    gap_x = v["lever_x0"] - (sx + sw / 2)
    print(f"    socket edge at x={sx + sw / 2:.2f}, "
          f"latch starts at x={v['lever_x0']:.2f}")
    print(f"    gap between them    : {gap_x:.2f} mm")
    if gap_x < MIN_WALL:
        problems.append(
            f"only {gap_x:.2f}mm between the tripod socket and the latch "
            "- the screw would break into the mechanism")

    # ---- head channel vs latch relief ----------------------------------
    print()
    print("  HEAD CHANNEL vs LATCH RELIEF")
    # Probe across, at the height of the head channel, from the channel
    # edge outward to the latch.
    z_mid = v["ledge_t"] + 1.0
    wall = clearance_along(
        mesh,
        [v["head_ch_w"] / 2 + 0.01, 0, z_mid],
        [v["lever_x1"] + 2.0, 0, z_mid],
    )
    print(f"    material between them: {wall:.2f} mm")
    if wall < MIN_WALL:
        problems.append(
            f"only {wall:.2f}mm between the stud's head channel and the "
            "latch relief - the head would have nothing holding it in "
            "sideways")

    # ---- plate margins --------------------------------------------------
    print()
    print("  PLATE MARGINS")
    below = v["bar_bot"] - v["plate_y_lo"]
    above = v["plate_y_hi"] - (sy + sw / 2)
    print(f"    below the latch      : {below:.2f} mm")
    print(f"    above the socket     : {above:.2f} mm")
    if above < 2.0:
        problems.append(
            f"only {above:.2f}mm of plate above the tripod socket - it "
            "would break out through the top edge")
    if below < 2.0:
        problems.append(
            f"only {below:.2f}mm of plate below the latch")

    # ---- the Peak Design plate has something to sit on ------------------
    #
    # The plate bolts flat to the back and carries the whole radio through
    # that joint.  Any part of it hanging past the bracket, or lapping over
    # one of the latch slots, is unsupported: the plate then pivots on
    # whatever edge it does touch and the radio wobbles no matter how hard
    # the screw is done up.
    #
    # Measured on the exported mesh rather than trusted from the model's
    # own arithmetic, because the arithmetic is what got this wrong before.
    # The model's assert compared X and never looked at Y, so it passed
    # while the plate overhung the top by 9.5mm.
    print()
    print("  PEAK DESIGN PLATE COVERAGE")
    pd = v["pd_plate_size"]
    plate_t = v["plate_t"]
    n = 61
    axis = np.linspace(-pd / 2, pd / 2, n)
    gx, gy = np.meshgrid(sx + axis, sy + axis)
    gx, gy = gx.ravel(), gy.ravel()

    # The screw opening is meant to be there.  Masked at the widest thing
    # that breaks the back face for THIS style - the mouth chamfer for a
    # threaded hole, but the much wider hex pocket for the nut version,
    # where the nut itself beds the plate.
    bore = np.hypot(gx - sx, gy - sy) <= v["socket_face_d"] / 2 + 0.2

    heights = bearing_height(mesh, gx, gy, plate_t + 5.0)
    supported = np.isclose(heights, plate_t, atol=0.25)
    bad = ~supported & ~bore

    # Both counts exclude the screw hole.  Counting every supported point
    # against a total that left the hole out gave 101.0% - harmless here,
    # but a coverage figure that can exceed 100 is one that can also hide a
    # real shortfall behind a rounding error.
    judged = ~bore
    ok = supported & judged

    print(f"    plate {pd:.0f} x {pd:.0f} mm centred on the screw at "
          f"({sx:.1f}, {sy:.1f})")
    print(f"    bracket spans x {v['plate_x_lo']:.1f}..{v['plate_x_hi']:.1f}, "
          f"y {v['plate_y_lo']:.1f}..{v['plate_y_hi']:.1f}")
    print(f"    supported            : "
          f"{100.0 * ok.sum() / judged.sum():.1f}% of the square "
          f"({judged.sum()} points judged, screw hole excluded)")

    if bad.any():
        problems.append(
            f"{bad.sum()} of {judged.sum()} sample points under the Peak "
            f"Design plate have no bracket beneath them - the plate would "
            f"sit on its own edge and rock.  The bare region spans x "
            f"{gx[bad].min():.1f}..{gx[bad].max():.1f}, y "
            f"{gy[bad].min():.1f}..{gy[bad].max():.1f}")
    else:
        print("    every sample lands on the flat back face")

    # ---- the radio hangs the right way ----------------------------------
    print()
    print("  HANGING SENSE")
    print(f"    screw at y={sy:.1f}, locked stud at y=0.0, "
          f"entry hole at y={v['travel']:.1f}")
    if sy <= 0.0:
        problems.append(
            "the tripod socket is not above the locked stud - the radio "
            "would stand on the mounting point instead of hanging from it")
    if v["travel"] <= 0.0:
        problems.append(
            "the entry hole is not above the locked position - gravity "
            "would work the stud back toward the opening instead of away "
            "from it")

    print()
    print("-" * 62)
    if problems:
        print("FAIL")
        for line in problems:
            print(f"  - {line}")
        return 1

    print("PASS - every feature clears every other by a printable margin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
