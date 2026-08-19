"""Measure the enclosure's seal on the exported mesh, not in the model.

The enclosure seals three different ways out of one groove - a 3mm cord
O-ring, a printed TPU gasket, or nothing at all with the labyrinth tongue
doing the work - and the model asserts all three.  Every one of those
asserts reads the model's own arithmetic, which is precisely the thing
that has been wrong before: the Peak Design bracket's plate overhung the
top by 9.5mm while an assert about the plate passed, because the assert
compared the number it was given rather than the shape that came out.

A seal is a worse place for that to happen than a bracket.  Nothing about
a groove that is 0.4mm too shallow looks wrong on screen, and it is not
discovered until the box is hanging in a tree in the rain.

So this renders the real variants and probes the real solid.  The groove's
width and depth are recovered by walking a line through the mesh and
noting where material starts and stops; the tongue and its channel are
checked by assembling the two parts and intersecting them, the same way
check_thread_fit.py proves the thread.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_seal.py
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

# How far the measured groove may differ from the number the model thinks
# it cut.  A tessellated revolve lands within a couple of hundredths of
# its true radius, so anything approaching two tenths is not sampling
# noise - it is another feature having taken a bite out of the groove.
GROOVE_TOL = 0.15          # mm

# Squeeze windows for a static face seal.  Below the floor the ring never
# beds down; above the ceiling it takes a compression set and stops
# springing back, so the box seals once and then never again.
ORING_SQUEEZE = (0.15, 0.35)
GASKET_SQUEEZE = (0.10, 0.30)

# Spare room the groove must have over the cord's own cross-section.
# Rubber is incompressible - it only changes shape - so a groove with
# nothing to spare cannot accept the ring at all and simply holds the lid
# off its stop.  10% is the usual minimum; most published tables want 15%.
GROOVE_SPARE = 1.10

# The tongue has to be properly inside its channel before the path over it
# is long enough to matter.  Less than a millimetre and a drop that is
# already creeping along the rim face carries straight across.
MIN_ENGAGE = 1.0           # mm

# The land the lid lands on.  This is what makes the squeeze a geometric
# number instead of a matter of grip strength, so it has to be wide enough
# to be a face rather than an edge.
MIN_STOP_W = 2.0           # mm

# Shared volume below this is two surfaces touching, not two solids
# fighting.  Around 150mm of circumference gets tessellated into a lot of
# flat triangles and they do not all land on exactly the same plane.
TOUCH_TOL = 30.0           # mm^3

# Probe step.  Fine enough that a 0.02mm reading error is smaller than
# every tolerance above, coarse enough that contains() stays quick.
STEP = 0.02                # mm

# Angles the radial probes are taken at.  Deliberately not multiples of
# anything in the model: the cable slots sit at 0 and 180, the weep holes
# at 45 and its multiples, and a probe that happened to line up with one
# would read a hole as a missing wall.
PROBE_ANGLES = (17.0, 143.0, 251.0)


def find_openscad() -> Path:
    for path in OPENSCAD_CANDIDATES:
        if path.exists():
            return path
    raise SystemExit("OpenSCAD not found - install it or edit OPENSCAD_CANDIDATES")


def echoed_values(openscad: Path) -> dict[str, float]:
    """Read the model's own derived numbers.

    Used to aim the probes, and as the claim the measurements are then
    tested against.  Never as the measurement itself.

    The tag is SEALPROBE rather than SEAL because the model prints its own
    summary line starting "  SEAL    O-ring squeeze ...", and matching on
    the shorter word picked that up instead - a line full of percentages
    and the word "squeeze", none of which parse, so every value came back
    missing at once.
    """
    scad = MODELS / ".seal_probe.scad"
    scad.write_text(
        "include <efhw_enclosure.scad>\n"
        'variant_render_mode = "none";\n'
        'echo(str("SEALPROBE",'
        '" oring_groove_w=", oring_groove_w,'
        '" oring_groove_d=", oring_groove_d,'
        '" oring_cord=", oring_cord,'
        '" gasket_w=", gasket_w,'
        '" gasket_h=", gasket_h,'
        '" gasket_ir=", gasket_ir,'
        '" groove_ir=", groove_ir,'
        '" groove_or=", groove_or,'
        '" tongue_h=", tongue_h,'
        '" tongue_clr=", tongue_clr,'
        '" z_rim=", z_rim,'
        '" z_tongue_top=", z_tongue_top,'
        '" wall_or=", wall_or,'
        '" interior_r=", interior_r,'
        '" stop_w=", stop_w,'
        '" thread_minor_r=", thread_minor_r,'
        '" oring_squeeze=", oring_squeeze,'
        '" gasket_squeeze=", gasket_squeeze));\n',
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [str(openscad), "-o", str(TMP / "seal_probe.stl"), str(scad)],
            capture_output=True, text=True,
        )
    finally:
        scad.unlink(missing_ok=True)

    text = (result.stderr or "") + (result.stdout or "")
    line = next((l for l in text.splitlines() if "SEALPROBE" in l), None)
    if line is None:
        sys.stderr.write(text[-2000:])
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


def render(openscad: Path, mode: str, out: Path) -> trimesh.Trimesh:
    """Build one variant of the enclosure.

    Re-rendered only when the model is newer than the mesh, because these
    take minutes each and three of them are wanted.  The comparison is
    against every source the model is built from, not just the file named
    in the include: a change to thread_lib.scad moves the thread and with
    it the radius the whole seal stack is stacked out to, and a mesh that
    predates it would be read as a passing model.
    """
    sources = [MODELS / "efhw_enclosure.scad", MODELS / "thread_lib.scad"]
    newest = max(s.stat().st_mtime for s in sources)

    if not (out.exists() and out.stat().st_mtime > newest):
        scad = MODELS / f".seal_{mode}.scad"
        scad.write_text(
            "include <efhw_enclosure.scad>\n"
            f'variant_render_mode = "{mode}";\n',
            encoding="utf-8",
        )
        print(f"  rendering {mode} (minutes) ...", flush=True)
        try:
            result = subprocess.run(
                [str(openscad), "-o", str(out), str(scad)],
                capture_output=True, text=True,
            )
        finally:
            scad.unlink(missing_ok=True)

        if not out.exists() or out.stat().st_size < 200:
            sys.stderr.write((result.stderr or "")[-2000:])
            raise SystemExit(f"OpenSCAD produced nothing for {mode}")

    return trimesh.load(out)


def at(r: float, deg: float) -> tuple[float, float]:
    return r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg))


def runs(inside: np.ndarray, axis: np.ndarray) -> list[tuple[float, float]]:
    """Turn a run of inside/outside samples into solid intervals."""
    out, start = [], None
    for value, ins in zip(axis, inside):
        if ins and start is None:
            start = value
        if not ins and start is not None:
            out.append((start, value))
            start = None
    if start is not None:
        out.append((start, axis[-1]))
    return out


def probe_runs(mesh: trimesh.Trimesh, point_at, t0: float, t1: float,
               want_solid: bool = True) -> list[tuple[float, float]]:
    """Intervals of solid (or of void) along a parametrised line.

    Every boundary is then found properly by bisection instead of being
    left on whichever sample happened to fall inside.  Sampling alone puts
    a surface up to a whole step out and biases it consistently one way,
    which turned a 1.500mm tongue into 1.480mm - not enough to matter
    here, but a third of the tolerance on a recess depth, and exactly the
    sort of quiet offset that gets absorbed into a "close enough" and then
    into the model.

    All the boundaries are halved together, one contains() call per round,
    because there is no compiled ray engine in this environment and a
    single point costs almost as much as a thousand.
    """
    ts = np.arange(t0, t1, STEP)
    pts = np.array([point_at(t) for t in ts])
    inside = mesh.contains(pts)
    if not want_solid:
        inside = ~inside

    # Held as sample indices, not as positions.  A run that reaches the
    # last sample and one that happens to end exactly on it are different
    # things - the first has no boundary to refine, the second does - and
    # comparing the positions cannot tell them apart.
    spans, start = [], None
    for k, ins in enumerate(inside):
        if ins and start is None:
            start = k
        if not ins and start is not None:
            spans.append([start, k])
            start = None
    if start is not None:
        spans.append([start, len(ts)])
    if not spans:
        return []

    # Each boundary as an (outside, inside) bracket.  A run that runs off
    # the end of the window has no boundary there - it was the window that
    # stopped it, not the solid.
    out_t, in_t, slots = [], [], []
    for k, (i, j) in enumerate(spans):
        if i > 0:
            out_t.append(ts[i - 1]); in_t.append(ts[i]); slots.append((k, 0))
        if j < len(ts):
            out_t.append(ts[j]); in_t.append(ts[j - 1]); slots.append((k, 1))

    refined = [[float(ts[i]), float(ts[min(j, len(ts) - 1)])]
               for i, j in spans]

    if slots:
        out_t = np.array(out_t, dtype=float)   # known outside the solid
        in_t = np.array(in_t, dtype=float)     # known inside it
        for _ in range(12):
            mid = (out_t + in_t) / 2
            got = mesh.contains(np.array([point_at(t) for t in mid]))
            if not want_solid:
                got = ~got
            in_t = np.where(got, mid, in_t)
            out_t = np.where(got, out_t, mid)

        for (k, end), value in zip(slots, (out_t + in_t) / 2):
            refined[k][end] = float(value)

    return [tuple(span) for span in refined]


def solid_runs_z(mesh: trimesh.Trimesh, r: float, deg: float,
                 z0: float, z1: float) -> list[tuple[float, float]]:
    """Where the solid starts and stops up a vertical line at radius r."""
    x, y = at(r, deg)
    return probe_runs(mesh, lambda z: (x, y, z), z0, z1)


def solid_runs_r(mesh: trimesh.Trimesh, z: float, deg: float,
                 r0: float, r1: float) -> list[tuple[float, float]]:
    """Where the solid starts and stops along a radial line at height z."""
    ux, uy = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return probe_runs(mesh, lambda r: (r * ux, r * uy, z), r0, r1)


def void_runs_r(mesh: trimesh.Trimesh, z: float, deg: float,
                r0: float, r1: float) -> list[tuple[float, float]]:
    """The gaps between the solid runs - grooves, channels, clearances."""
    ux, uy = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return probe_runs(mesh, lambda r: (r * ux, r * uy, z), r0, r1,
                      want_solid=False)


def void_area(mesh: trimesh.Trimesh, deg: float, r0: float, r1: float,
              z0: float, z1: float, step: float = 0.05) -> float:
    """Cross-section area of the void inside a window, in mm^2.

    Counted cell by cell rather than worked out from a width and a depth,
    so a chamfer, a draft or a bite taken out of one corner is included
    instead of being averaged into a rectangle that never existed.
    """
    rs = np.arange(r0 + step / 2, r1, step)
    zs = np.arange(z0 + step / 2, z1, step)
    rg, zg = np.meshgrid(rs, zs)
    rg, zg = rg.ravel(), zg.ravel()
    ux, uy = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    pts = np.column_stack([rg * ux, rg * uy, zg])
    return float((~mesh.contains(pts)).sum() * step * step)


def top_surface(mesh: trimesh.Trimesh, radii: np.ndarray, deg: float,
                z_above: float) -> np.ndarray:
    """Height of the first solid seen looking straight down, per radius.

    NaN where the ray misses.  Cast rather than sampled so that "nothing
    there at all" reads differently from "something there, but lower than
    it should be" - a missing stop land and a sunken one fail in quite
    different ways.
    """
    ux, uy = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    origins = np.column_stack([radii * ux, radii * uy,
                               np.full(len(radii), z_above)])
    dirs = np.tile([0.0, 0.0, -1.0], (len(radii), 1))

    locs, ray_idx, _ = mesh.ray.intersects_location(
        ray_origins=origins, ray_directions=dirs, multiple_hits=True)

    best = np.full(len(radii), np.nan)
    for point, idx in zip(locs, ray_idx):
        if np.isnan(best[idx]) or point[2] > best[idx]:
            best[idx] = point[2]
    return best


def shared_volume(a: trimesh.Trimesh, b: trimesh.Trimesh):
    """How much solid the two parts try to occupy at the same time.

    Returns the volume and the overlap itself, so a failure can say where
    the parts are fighting rather than only that they are.
    """
    try:
        both = a.intersection(b)
    except Exception:
        return float("nan"), None
    if both is None or both.is_empty:
        return 0.0, None
    return abs(float(both.volume)), both


def located(overlap) -> str:
    """Name the radius and height of each place the parts really clash.

    Split into separate bodies and the slivers thrown away first.  Two
    faces that meet exactly - the rim against the underside of the lid,
    which is the whole point of the design - come out of the boolean as
    zero-thickness scraps spread right across the sealing face, and the
    bounding box of the lot reported a 0.3mm ring at r=60 as reaching
    r=68: the right complaint pointing at the wrong feature.
    """
    if overlap is None:
        return ""
    # The scraps have no volume, so trimesh divides by zero working out
    # where their mass is.  Nothing here asks.
    with np.errstate(invalid="ignore", divide="ignore"):
        pieces = [p for p in overlap.split(only_watertight=False)
                  if abs(p.volume) > 1.0]
    if not pieces:
        return ""

    out = []
    for piece in sorted(pieces, key=lambda p: -abs(p.volume))[:3]:
        # Radius from the vertices, not from the bounding box.  A ring at
        # r=60 has a box corner at r=85, and quoting that would send
        # somebody looking at the thread.
        rad = np.hypot(piece.vertices[:, 0], piece.vertices[:, 1])
        lo, hi = piece.bounds
        out.append(f"{abs(piece.volume):.0f}mm^3 at r {rad.min():.2f}.."
                   f"{rad.max():.2f}, z {lo[2]:.2f}..{hi[2]:.2f}")
    return "  The real overlap is " + "; ".join(out) + "."


def median(values: list[float]) -> float:
    return float(np.median(np.asarray(values, dtype=float)))


def main() -> int:
    openscad = find_openscad()
    TMP.mkdir(exist_ok=True)

    v = echoed_values(openscad)

    print("=== EFHW enclosure seal ===")
    print(f"  nominal groove {v['oring_groove_w']:.2f} wide x "
          f"{v['oring_groove_d']:.2f} deep at r "
          f"{v['groove_ir']:.2f}..{v['groove_or']:.2f}")
    print(f"  rim at z={v['z_rim']:.2f}, tongue to z="
          f"{v['z_tongue_top']:.2f}, stop land "
          f"{v['groove_or']:.2f}..{v['thread_minor_r']:.2f}")
    print()

    body = render(openscad, "body", TMP / "efhw_body.stl")
    lid = render(openscad, "lid_placed", TMP / "efhw_lid_placed.stl")
    gasket = render(openscad, "gasket", TMP / "efhw_gasket.stl")

    for name, mesh in (("body", body), ("lid", lid), ("gasket", gasket)):
        size = mesh.bounds[1] - mesh.bounds[0]
        print(f"  {name:7} {size[0]:6.1f} x {size[1]:6.1f} x {size[2]:6.1f} mm"
              f"  {mesh.volume / 1000:7.2f} cm^3  {mesh.body_count} body"
              f"  watertight={mesh.is_watertight}")

    problems: list[str] = []

    # ---- the renders are the variants they claim to be ------------------
    #
    # Cheap, and worth having.  The render mode is set by assigning over
    # the model's own value after the include, and that override has
    # silently failed before - every check then measured the whole
    # assembly and reported the lid's numbers as the body's.
    if body.bounds[1][2] > v["z_tongue_top"] + 0.5:
        raise SystemExit(
            f"the 'body' render reaches z={body.bounds[1][2]:.1f}, above "
            f"the tongue at {v['z_tongue_top']:.1f} - the render mode did "
            f"not take and this is the assembly.  Nothing below would mean "
            f"anything.")

    # ---- 1. the groove that came out ------------------------------------
    print()
    print("  GROOVE, MEASURED ON THE BODY")

    z_probe = v["z_rim"] - v["oring_groove_d"] / 2
    widths, inners, outers = [], [], []
    for deg in PROBE_ANGLES:
        gaps = [g for g in void_runs_r(body, z_probe, deg,
                                       v["wall_or"], v["thread_minor_r"])
                if g[1] - g[0] > 0.2]
        if len(gaps) != 1:
            problems.append(
                f"a radial cut at {deg:.0f} deg through the rim finds "
                f"{len(gaps)} voids where there should be exactly one "
                f"groove.  Something else is cutting the sealing face - "
                f"look at what body_cuts() puts near z={z_probe:.2f}.")
            continue
        lo, hi = gaps[0]
        inners.append(lo)
        outers.append(hi)
        widths.append(hi - lo)

    if not widths:
        print("    no groove found at all")
        problems.append("no O-ring groove in the rim at any probed angle")
        return report(problems)

    w_meas = median(widths)
    r_in, r_out = median(inners), median(outers)
    r_mid = (r_in + r_out) / 2

    # Depth from the top of the solid at the groove's own centreline,
    # referenced to the stop land beside it rather than to z_rim from the
    # model.  If the whole rim has moved, the squeeze has not.
    r_stop_mid = (v["groove_or"] + v["thread_minor_r"]) / 2
    floors, rims = [], []
    for deg in PROBE_ANGLES:
        below = solid_runs_z(body, r_mid, deg,
                             v["z_rim"] - v["oring_groove_d"] - 4.0,
                             v["z_rim"] + 0.5)
        land = solid_runs_z(body, r_stop_mid, deg,
                            v["z_rim"] - 4.0, v["z_rim"] + 0.5)
        if below and land:
            floors.append(below[-1][1])
            rims.append(land[-1][1])

    z_floor, z_land = median(floors), median(rims)
    d_meas = z_land - z_floor

    print(f"    width               : {w_meas:.3f} mm "
          f"(nominal {v['oring_groove_w']:.3f})")
    print(f"    depth               : {d_meas:.3f} mm "
          f"(nominal {v['oring_groove_d']:.3f})")
    print(f"    sits at r           : {r_in:.3f} .. {r_out:.3f} "
          f"(nominal {v['groove_ir']:.3f} .. {v['groove_or']:.3f})")
    print(f"    sealing face at z   : {z_land:.3f} "
          f"(nominal {v['z_rim']:.3f})")

    if abs(w_meas - v["oring_groove_w"]) > GROOVE_TOL:
        problems.append(
            f"the groove measures {w_meas:.2f}mm wide but the model cut "
            f"{v['oring_groove_w']:.2f}mm.  Something else is taking a "
            f"bite out of it - find the feature and move it, do not widen "
            f"oring_groove_w to match.")
    if abs(d_meas - v["oring_groove_d"]) > GROOVE_TOL:
        problems.append(
            f"the groove measures {d_meas:.2f}mm deep but the model cut "
            f"{v['oring_groove_d']:.2f}mm.  Depth is what sets the "
            f"squeeze, so the seal is not the one that was designed.")

    # ---- 2. squeeze, all three ways -------------------------------------
    #
    # Worked out from the depth that came out of the mesh, not from the
    # depth the model meant to cut.  If those two disagree the check above
    # has already said so; this then shows what the disagreement costs.
    print()
    print("  SQUEEZE")
    oring_sq = (v["oring_cord"] - d_meas) / v["oring_cord"]
    gasket_sq = (v["gasket_h"] - d_meas) / v["gasket_h"]

    print(f"    3mm cord O-ring     : {oring_sq * 100:5.1f} %  "
          f"({v['oring_cord']:.2f}mm cord into a {d_meas:.2f}mm groove)")
    print(f"    printed TPU gasket  : {gasket_sq * 100:5.1f} %  "
          f"({v['gasket_h']:.2f}mm section into the same groove)")
    print(f"    bare                :   n/a    labyrinth only, no squeeze")

    if not ORING_SQUEEZE[0] < oring_sq < ORING_SQUEEZE[1]:
        problems.append(
            f"O-ring squeeze is {oring_sq * 100:.1f}%, outside the "
            f"{ORING_SQUEEZE[0] * 100:.0f}-{ORING_SQUEEZE[1] * 100:.0f}% a "
            f"static face seal wants.  Change oring_groove_d - deeper "
            f"groove, less squeeze.")
    if not GASKET_SQUEEZE[0] < gasket_sq < GASKET_SQUEEZE[1]:
        problems.append(
            f"printed gasket squeeze is {gasket_sq * 100:.1f}%, outside "
            f"{GASKET_SQUEEZE[0] * 100:.0f}-{GASKET_SQUEEZE[1] * 100:.0f}%."
            f"  Change gasket_h, which is derived from oring_groove_d.")

    # ---- 3. room for the rubber to go -----------------------------------
    print()
    print("  ROOM IN THE GROOVE")
    area_meas = void_area(body, PROBE_ANGLES[0],
                          v["wall_or"], v["thread_minor_r"],
                          v["z_rim"] - v["oring_groove_d"] - 1.0,
                          v["z_rim"] - 0.02)
    cord_area = math.pi * (v["oring_cord"] / 2) ** 2
    ratio = area_meas / cord_area

    print(f"    groove section      : {area_meas:6.2f} mm^2 "
          f"(measured off the mesh)")
    print(f"    cord section        : {cord_area:6.2f} mm^2")
    print(f"    ratio               : {ratio:6.3f}  "
          f"({(ratio - 1) * 100:.1f}% spare)")

    if ratio < GROOVE_SPARE:
        problems.append(
            f"the groove is only {ratio:.2f} times the cord's own section. "
            f"The ring is incompressible and can only change shape, so "
            f"with under {(GROOVE_SPARE - 1) * 100:.0f}% spare it has "
            f"nowhere to spread and props the lid off its stop - the seal "
            f"then depends on how hard the lid was twisted.  Widen "
            f"oring_groove_w.")

    # ---- 4. the printed gasket fits the groove it is for -----------------
    print()
    print("  PRINTED GASKET")
    g_h = float(gasket.bounds[1][2] - gasket.bounds[0][2])
    # Both radii off the same radial probe.  Taking the outer one from the
    # bounding box instead would read the facet corners while the inner
    # one reads the flats, and a faceted 63mm circle differs between the
    # two by about a hundredth - enough to make a gasket that exactly
    # fills its groove look 0.02mm too wide.
    g_runs = solid_runs_r(gasket, gasket.bounds[0][2] + g_h / 2,
                          PROBE_ANGLES[0], 0.0, r_out + 4.0)
    g_ir, g_or = g_runs[0] if g_runs else (float("nan"), float("nan"))
    g_w = g_or - g_ir

    print(f"    section             : {g_w:.3f} wide x {g_h:.3f} tall")
    print(f"    sits at r           : {g_ir:.3f} .. {g_or:.3f}")
    print(f"    groove is           : {w_meas:.3f} wide x {d_meas:.3f} deep "
          f"at {r_in:.3f} .. {r_out:.3f}")

    if not gasket.is_watertight:
        problems.append(
            "the gasket render is not watertight - it would not slice, "
            "never mind seal")
    if g_w >= w_meas:
        problems.append(
            f"the gasket is {g_w:.2f}mm wide and the groove is "
            f"{w_meas:.2f}mm - it will not drop in.  Reduce gasket_w.")
    if g_h <= d_meas:
        problems.append(
            f"the gasket is {g_h:.2f}mm tall in a {d_meas:.2f}mm groove, "
            f"so it sits below the sealing face and is never touched. "
            f"Raise gasket_h.")
    if g_ir < r_in - 0.01 or g_or > r_out + 0.01:
        problems.append(
            f"the gasket spans r {g_ir:.2f}..{g_or:.2f} but the groove is "
            f"r {r_in:.2f}..{r_out:.2f} - it overhangs the land and would "
            f"be pinched on the rim instead of in the groove.  Fix "
            f"gasket_ir.")

    # ---- 5. the labyrinth, which is what seals it bare -------------------
    #
    # Probed on both parts and then proved by assembling them.  The probes
    # say what is wrong and where; the intersection says whether it is
    # wrong at all, and it cannot be talked out of an answer by a
    # mis-aimed probe.
    print()
    print("  LABYRINTH  (the bare seal)")

    r_tongue_mid = (v["interior_r"] + v["wall_or"]) / 2
    z_engage = v["z_rim"] + v["tongue_h"] / 2

    t_top = median([solid_runs_z(body, r_tongue_mid, deg,
                                 v["z_rim"] - 1.0,
                                 v["z_tongue_top"] + 2.0)[-1][1]
                    for deg in PROBE_ANGLES])

    t_runs = solid_runs_r(body, z_engage, PROBE_ANGLES[0],
                          v["interior_r"] - 3.0, v["thread_minor_r"])
    t_in, t_out = t_runs[0]

    # The lid's underside plane, taken over the groove where nothing else
    # interrupts it, and the roof of the channel above the tongue.
    lid_face = median([solid_runs_z(lid, r_mid, deg,
                                    v["z_rim"] - 1.0,
                                    v["z_tongue_top"] + 6.0)[0][0]
                       for deg in PROBE_ANGLES])
    c_roof = median([solid_runs_z(lid, r_tongue_mid, deg,
                                  v["z_rim"] - 1.0,
                                  v["z_tongue_top"] + 6.0)[0][0]
                     for deg in PROBE_ANGLES])

    c_gaps = [g for g in void_runs_r(lid, z_engage, PROBE_ANGLES[0],
                                     v["interior_r"] - 3.0,
                                     v["thread_minor_r"])
              if g[1] - g[0] > 0.2]
    c_in, c_out = c_gaps[0] if c_gaps else (float("nan"), float("nan"))

    engage = min(t_top, c_roof) - lid_face
    clr_in = t_in - c_in
    clr_out = c_out - t_out
    clr_top = c_roof - t_top

    print(f"    tongue              : r {t_in:.3f} .. {t_out:.3f}, "
          f"top at z {t_top:.3f} ({t_top - lid_face:.3f} proud of the rim)")
    print(f"    channel             : r {c_in:.3f} .. {c_out:.3f}, "
          f"roof at z {c_roof:.3f} ({c_roof - lid_face:.3f} deep)")
    print(f"    engagement          : {engage:.3f} mm")
    print(f"    clearance inboard   : {clr_in:+.3f} mm")
    print(f"    clearance outboard  : {clr_out:+.3f} mm")
    print(f"    clearance over top  : {clr_top:+.3f} mm")

    if engage < MIN_ENGAGE:
        problems.append(
            f"the tongue only enters its channel by {engage:.2f}mm, under "
            f"the {MIN_ENGAGE}mm that makes a barrier rather than a step. "
            f"Raise tongue_h.")
    for label, gap in (("inboard", clr_in), ("outboard", clr_out),
                       ("over the top", clr_top)):
        if gap < 0:
            problems.append(
                f"the tongue overlaps the wall of its channel {label} by "
                f"{-gap:.2f}mm - the lid cannot close onto its stop at "
                f"all, so every squeeze figure above is fiction.")
        elif gap < v["tongue_clr"] - 0.05:
            problems.append(
                f"only {gap:.2f}mm of clearance {label} in the labyrinth "
                f"channel, against the {v['tongue_clr']:.2f}mm asked for "
                f"by tongue_clr - it will be a press fit once printed.")

    print()
    print("    assembling the two halves ...", flush=True)
    clash, where = shared_volume(body, lid)
    print(f"    body and lid share  : {clash:.1f} mm^3")

    if math.isnan(clash):
        problems.append(
            "the boolean of body against lid failed, so the assembly was "
            "never actually proved.  Fix that before believing the probes.")
    elif clash > TOUCH_TOL:
        problems.append(
            f"body and lid try to occupy {clash:.0f}mm^3 of the same "
            f"space when assembled, so the lid never reaches its stop and "
            f"the seal is set by how hard it was twisted.{located(where)}")

    # ---- 6. the hard stop ------------------------------------------------
    print()
    print("  HARD STOP")
    radii = np.arange(v["groove_or"] - 1.0, v["thread_minor_r"] + 3.0, 0.02)
    heights = top_surface(body, radii, PROBE_ANGLES[0], v["z_tongue_top"] + 5)

    flat = np.abs(heights - z_land) <= 0.02
    land_runs = runs(flat, radii)
    on_land = [r for r in land_runs if r[0] <= r_stop_mid <= r[1]]
    land_w = (on_land[0][1] - on_land[0][0]) if on_land else 0.0

    if on_land:
        print(f"    land found at r     : {on_land[0][0]:.3f} .. "
              f"{on_land[0][1]:.3f}")
    else:
        print("    land found at r     : nothing flat at the stop radius")
    print(f"    width               : {land_w:.3f} mm "
          f"(nominal stop_w {v['stop_w']:.2f})")
    if flat.any():
        spread = float(np.nanmax(heights[flat]) - np.nanmin(heights[flat]))
        print(f"    height spread       : {spread:.3f} mm")

    if land_w < MIN_STOP_W:
        problems.append(
            f"the stop land is {land_w:.2f}mm wide, under the "
            f"{MIN_STOP_W}mm needed for the lid to land on a face rather "
            f"than an edge.  Raise stop_w.")

    return report(problems)


def report(problems: list[str]) -> int:
    print()
    print("-" * 62)
    if problems:
        print("FAIL")
        for line in problems:
            print(f"  - {line}")
        return 1

    print("PASS - the groove that came out is the groove that was drawn,")
    print("       all three seals squeeze into range, and the lid closes")
    print("       onto its stop with the labyrinth engaged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
