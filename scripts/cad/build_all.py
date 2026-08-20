"""Run the whole verification and export pipeline in one pass.

Order matters: nothing is exported until the geometry checks pass, so a
broken model cannot silently overwrite good STLs.

Visor mount:
  1. slot travel   - is the keyhole long enough that the head clears the
                     entry hole, and how close is it to the ceiling?
  2. lever freedom - is the compliant arm actually free to move, or fused
                     to the block?
  3. fit checks    - does the latch capture the stud, in all variants?
  4. export        - STL and 3MF for every variant, plus test coupons
  5. inspect       - watertight, single body, no thin walls
  6. printability  - what would print unsupported
  7. previews      - shaded PNG of each variant

Peak Design bracket, which shares the keyhole via models/sds150_stud.scad:
  8. latch sizing  - flexure strain, press force, holding force
  9. latch stroke  - can the latch actually complete its travel, or does
                     it bind?  Measured against the body as a separate
                     solid, since the relief and the latch are generated
                     from one outline and would hide a shared error.
 10. fit checks    - captures the stud, and RELEASES it when pressed
 11. export        - STL and 3MF in each socket style, plus a coupon
 12. interference  - every feature against every other, probed on the
                     exported solid.  Catches the near-misses that the
                     single-purpose checks each look past.
 13. inspect       - watertight, single body, no thin walls
 14. printability  - unsupported regions, classified as bridge, chamfer
                     or genuine island

EFHW antenna enclosure, which shares nothing with the two mounts except
the method - it is a screw-lid cylinder built on models/thread_lib.scad:
 15. thread sizing - extrusions per crest, overhang angle, helix angle
 16. thread fit    - male and female screwed together as SEPARATE solids,
                     including a deliberately miscoupled control, since a
                     pair generated from one profile hides its own errors
 17. lettering     - stroke widths, and whether the counters in A and D
                     survive being fattened
 18. cable slots   - a coax laid in from above, lowered down the slot,
                     and the lid screwed down on top of it
 19. export        - body, lid and both coupons, in STL and 3MF
 20. solid audit   - the labyrinth, the weep holes, the carabiner ears
                     and the floor's fall, probed on the exported mesh
 21. inspect       - watertight, single body, no thin walls

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/build_all.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / ".venv-cad" / "Scripts" / "python.exe"
HERE = Path(__file__).resolve().parent

VARIANTS = [
    "lengthwise",
    "crosswise",
    "lengthwise_lever",
    "crosswise_lever",
]

# Tripod socket styles the Peak Design bracket is exported in.
PD_STYLES = ["self_tap", "insert", "nut"]

# The enclosure's four printable parts.  The coupons are first because
# that is the order they should be printed in - they are the thread and
# the knurl with the middle taken out, twenty minutes against five hours.
ENCLOSURE_FILES = [
    "efhw_coupon_body.stl",
    "efhw_coupon_lid.stl",
    "efhw_enclosure_body.stl",
    "efhw_enclosure_lid.stl",
]


def run(label: str, args: list[str], required: bool = True) -> bool:
    """Run one step, streaming a short summary of its output."""
    print(f"\n{'=' * 68}\n{label}\n{'=' * 68}", flush=True)
    started = time.monotonic()

    result = subprocess.run(
        [str(PYTHON), "-W", "ignore", *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    elapsed = time.monotonic() - started

    print(result.stdout.rstrip())
    if result.returncode != 0:
        tail = (result.stderr or "").strip().splitlines()[-15:]
        for line in tail:
            print(f"  {line}")

    status = "OK" if result.returncode == 0 else "FAILED"
    print(f"\n[{status}] {label}  ({elapsed:.0f}s)", flush=True)

    if result.returncode != 0 and required:
        print("\nstopping: a required step failed, nothing was exported")
        sys.exit(1)
    return result.returncode == 0


def main() -> None:
    started = time.monotonic()

    run("1. slot travel", [str(HERE / "max_travel.py")])
    run("2. lever freedom", [str(HERE / "check_lever_free.py")])
    run("3. fit checks", [str(HERE / "fit_check.py")])
    run("4. export", [str(HERE / "export_models.py")])

    print(f"\n{'=' * 68}\n5. inspect exports\n{'=' * 68}", flush=True)
    all_clean = True
    for variant in VARIANTS:
        for name in (f"sds150_visor_mount_{variant}.stl", f"coupon_{variant}.stl"):
            path = ROOT / "models" / name
            result = subprocess.run(
                [str(PYTHON), "-W", "ignore", str(HERE / "inspect_stl.py"), str(path)],
                capture_output=True, text=True, cwd=ROOT,
            )
            summary = [
                line.strip() for line in result.stdout.splitlines()
                if any(k in line for k in ("min =", "bodies=", "PROBLEM", "no problems"))
            ]
            flag = "OK " if result.returncode == 0 else "BAD"
            print(f"  [{flag}] {name}")
            for line in summary:
                print(f"         {line}")
            all_clean &= result.returncode == 0

    print(f"\n{'=' * 68}\n6. printability\n{'=' * 68}", flush=True)
    for variant in VARIANTS:
        path = ROOT / "models" / f"sds150_visor_mount_{variant}.stl"
        result = subprocess.run(
            [str(PYTHON), "-W", "ignore", str(HERE / "check_printable.py"), str(path)],
            capture_output=True, text=True, cwd=ROOT,
        )
        # Exports are already rotated, so the first orientation listed is
        # the one the file will actually be sliced in.
        for line in result.stdout.splitlines():
            if "as modelled" in line or "===" in line:
                print(f"  {line.strip()}")

    print(f"\n{'=' * 68}\n7. previews\n{'=' * 68}", flush=True)
    for variant in VARIANTS:
        stl = ROOT / "models" / f"sds150_visor_mount_{variant}.stl"
        png = ROOT / "models" / f"preview_{variant}.png"
        subprocess.run(
            [str(PYTHON), "-W", "ignore", str(HERE / "render_stl.py"),
             str(stl), str(png)],
            capture_output=True, text=True, cwd=ROOT,
        )
        print(f"  wrote {png.name}")

    # ------------------------------------------------------------------
    #  Peak Design bracket
    # ------------------------------------------------------------------
    # Same keyhole, shared through models/sds150_stud.scad, but a very
    # different body: a flat plate with a tripod socket and a latch that
    # flexes sideways instead of downward.

    run("8. bracket latch sizing", [str(HERE / "design_finger.py")])
    run("9. bracket latch stroke", [str(HERE / "check_pd_sweep.py")])
    run("10. bracket fit checks", [str(HERE / "pd_fit_check.py")])
    run("11. bracket export", [str(HERE / "export_pd_bracket.py")])

    print(f"\n{'=' * 68}\n12. bracket interference audit\n{'=' * 68}",
          flush=True)
    bracket_files = [f"sds150_pd_bracket_{s}.stl" for s in PD_STYLES]

    for name in bracket_files:
        path = ROOT / "models" / name
        result = subprocess.run(
            [str(PYTHON), "-W", "ignore",
             str(HERE / "audit_pd_bracket.py"), str(path)],
            capture_output=True, text=True, cwd=ROOT,
        )
        flag = "OK " if result.returncode == 0 else "BAD"
        print(f"  [{flag}] {name}")
        for line in result.stdout.splitlines():
            if any(k in line for k in ("gap between", "floor under",
                                       "material between", "supported",
                                       "PASS", "FAIL", "  - ")):
                print(f"         {line.strip()}")
        all_clean &= result.returncode == 0

    # The ledge around the entry hole is the thinnest place in the part and
    # the most visible.  Measured on the mesh rather than asserted in the
    # model, because it was the model's own arithmetic that got it wrong -
    # the latch relief swung across and scalloped it to 0.2mm.
    print(f"\n{'=' * 68}\n12b. bracket entry-hole ledge\n{'=' * 68}",
          flush=True)
    for name in bracket_files:
        path = ROOT / "models" / name
        result = subprocess.run(
            [str(PYTHON), "-W", "ignore",
             str(HERE / "check_entry_wall.py"), str(path)],
            capture_output=True, text=True, cwd=ROOT,
        )
        flag = "OK " if result.returncode == 0 else "BAD"
        print(f"  [{flag}] {name}")
        for line in result.stdout.splitlines():
            if any(k in line for k in ("thinnest", "PASS", "FAIL")):
                print(f"         {line.strip()}")
        all_clean &= result.returncode == 0

    print(f"\n{'=' * 68}\n13. inspect bracket exports\n{'=' * 68}",
          flush=True)
    for name in bracket_files:
        path = ROOT / "models" / name
        result = subprocess.run(
            [str(PYTHON), "-W", "ignore", str(HERE / "inspect_stl.py"), str(path)],
            capture_output=True, text=True, cwd=ROOT,
        )
        summary = [
            line.strip() for line in result.stdout.splitlines()
            if any(k in line for k in ("min =", "bodies=", "PROBLEM", "no problems"))
        ]
        flag = "OK " if result.returncode == 0 else "BAD"
        print(f"  [{flag}] {name}")
        for line in summary:
            print(f"         {line}")
        all_clean &= result.returncode == 0

    print(f"\n{'=' * 68}\n14. bracket printability\n{'=' * 68}", flush=True)
    # A raw floating-area figure is misleading here: the bracket has a
    # large chamfer and a wide bridge over the head channel, both of which
    # print fine.  This step classifies each region instead, and only
    # fails on one that genuinely cannot be printed without support -
    # which for a printed-in-place latch would weld it solid.
    for name in bracket_files:
        path = ROOT / "models" / name
        result = subprocess.run(
            [str(PYTHON), "-W", "ignore",
             str(HERE / "check_pd_printable.py"), str(path)],
            capture_output=True, text=True, cwd=ROOT,
        )
        flag = "OK " if result.returncode == 0 else "BAD"
        print(f"  [{flag}] {name}")
        for line in result.stdout.splitlines():
            if any(k in line for k in ("ISLAND", "PASS", "FAIL", "  - ")):
                print(f"         {line.strip()}")
        all_clean &= result.returncode == 0

    # ------------------------------------------------------------------
    #  EFHW antenna enclosure
    # ------------------------------------------------------------------
    # Nothing in common with the mounts but the method.  The thread comes
    # from models/thread_lib.scad, which is generic, so these steps prove
    # the library as much as they prove the enclosure.
    #
    # Sizing before fit before export, for the same reason as above: a
    # thread that is wrong analytically cannot be made right by a
    # clearance, and there is no point rendering for five minutes to find
    # that out.

    run("15. thread sizing", [str(HERE / "design_thread.py")])
    run("16. thread fit", [str(HERE / "check_thread_fit.py")])
    run("17. lid lettering", [str(HERE / "check_text.py")])
    run("18. cable slots", [str(HERE / "check_cable_slot.py")])
    run("19. enclosure export", [str(HERE / "export_enclosure.py")])
    run("20. enclosure solid audit", [str(HERE / "check_enclosure.py")])

    print(f"\n{'=' * 68}\n21. inspect enclosure exports\n{'=' * 68}",
          flush=True)
    for name in ENCLOSURE_FILES:
        path = ROOT / "models" / name
        result = subprocess.run(
            [str(PYTHON), "-W", "ignore", str(HERE / "inspect_stl.py"), str(path)],
            capture_output=True, text=True, cwd=ROOT,
        )
        summary = [
            line.strip() for line in result.stdout.splitlines()
            if any(k in line for k in ("min =", "bodies=", "PROBLEM", "no problems"))
        ]
        flag = "OK " if result.returncode == 0 else "BAD"
        print(f"  [{flag}] {name}")
        for line in summary:
            print(f"         {line}")
        all_clean &= result.returncode == 0

    total = time.monotonic() - started
    print(f"\n{'=' * 68}")
    if all_clean:
        print(f"ALL STEPS PASSED  ({total:.0f}s total)")
    else:
        print(f"exports written but some have geometry problems  ({total:.0f}s)")
        sys.exit(1)


if __name__ == "__main__":
    main()
