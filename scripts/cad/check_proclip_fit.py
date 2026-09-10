"""Verify the SDS150 gravity keyhole on the ProClip plates.

Same expectations as the Peak Design standoff, because it is the same
keyhole with the same fit - only the flat-plate bridge allowance differs.
There is no latch, so:

* the head drops through the entry hole without touching;
* the stud runs the whole slot down without touching;
* it sits free at the locked end;
* pulling straight off the face is blocked by a substantial ledge;
* an oversized stud is caught by the same harness.

The stud and the plate are rendered as separate solids.  Generating a
void and its mating part from one boolean hides the same error in both.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/check_proclip_fit.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models" / "proclip mounts"
MODEL = MODELS / "proclip_radio_mount.scad"
STANDOFF = (ROOT / "models" / "peak design radio standoff"
            / "peak_design_radio_standoff.scad")
TMP = ROOT / ".tmp-cad"
OPENSCAD = Path(r"C:\Program Files\OpenSCAD\openscad.exe")

CASES = [("sds", "landscape"), ("sds", "portrait"),
         ("combined", "landscape"), ("combined", "portrait")]

TOUCH_TOL = 8.0
BLOCK_MIN = 100.0     # ledge material a pulled stud must run into
CONTROL_MIN = 50.0


def echo(path: Path, **defines: str) -> str:
    args = [str(OPENSCAD), "-o", str(TMP / "_pcfit_null.stl"),
            "-D", 'variant_render_mode="none"']
    for key, val in defines.items():
        args.extend(["-D", f'{key}="{val}"'])
    args.append(str(path))
    result = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
    return (result.stdout or "") + "\n" + (result.stderr or "")


def value(text: str, name: str) -> float:
    found = re.findall(rf"(?:^|\s){re.escape(name)}=(-?[0-9.]+)", text)
    if not found:
        raise SystemExit(f"model did not echo {name}")
    return float(found[-1])


def render(tag: str, mode: str, variant: str, orientation: str,
           **values: float) -> trimesh.Trimesh:
    out = TMP / f"pcfit_{tag}.stl"
    out.unlink(missing_ok=True)
    assigns = [f'variant_render_mode = "{mode}";',
               f'variant = "{variant}";',
               f'amps_orientation = "{orientation}";']
    assigns.extend(f"{key} = {val};" for key, val in values.items())
    wrapper = MODELS / f".pcfit_{tag}.scad"
    wrapper.write_text(
        "include <proclip_radio_mount.scad>\n" + "\n".join(assigns) + "\n",
        encoding="utf-8")
    try:
        result = subprocess.run([str(OPENSCAD), "-o", str(out), str(wrapper)],
                                capture_output=True, text=True, cwd=ROOT)
    finally:
        wrapper.unlink(missing_ok=True)
    if not out.exists() or out.stat().st_size < 200:
        sys.stderr.write(((result.stdout or "") + (result.stderr or ""))[-2000:])
        raise SystemExit(f"OpenSCAD produced no {tag}")
    return trimesh.load(out)


def shared(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    try:
        both = a.intersection(b)
    except Exception as exc:
        raise SystemExit(f"boolean intersection failed: {exc}") from exc
    if both is None or both.is_empty:
        return 0.0
    return abs(float(both.volume))


def main() -> int:
    if not OPENSCAD.exists():
        raise SystemExit(f"OpenSCAD not found at {OPENSCAD}")
    TMP.mkdir(exist_ok=True)

    text = echo(MODEL, variant="sds", amps_orientation="landscape")
    travel = value(text, "travel")
    minimum = value(text, "min")
    ledge_t = value(text, "ledge_t")
    entry_d = value(text, "entry_d")
    axial_free = 4.5 - ledge_t     # stud neck height less the ledge

    print("=== SDS150 gravity keyhole on the ProClip plates ===")
    print(f"  travel {travel:.2f} mm against a mathematical minimum of "
          f"{minimum:.3f} mm")
    print(f"  ledge {ledge_t:.3f} mm, intentional axial freedom "
          f"{axial_free:.3f} mm")
    print()

    failures: list[str] = []

    # The keyhole is shared with the Peak Design standoff.  If the two ever
    # disagree the coupons stop transferring, so check it rather than
    # assume it - this is the exact class of bug the project keeps hitting.
    print("  AGREEMENT WITH THE PEAK DESIGN STANDOFF")
    so = echo(STANDOFF)
    so_ledge = value(so, "ledge_t")
    so_entry = value(so, "entry_d")
    so_travel = value(so, "travel")
    print(f"    ledge   standoff {so_ledge:.3f} vs proclip {ledge_t:.3f}")
    print(f"    entry   standoff {so_entry:.3f} vs proclip {entry_d:.3f}")
    print(f"    travel  standoff {so_travel:.2f} vs proclip {travel:.2f}")
    for name, a, b in (("ledge", so_ledge, ledge_t),
                       ("entry hole", so_entry, entry_d),
                       ("travel", so_travel, travel)):
        if abs(a - b) > 0.001:
            failures.append(
                f"the {name} has drifted from the standoff "
                f"({a:.3f} vs {b:.3f}); printed coupons no longer transfer")
    print()

    for variant, orientation in CASES:
        tag = f"{variant}_{orientation}"
        print(f"  {variant.upper()} / {orientation}")
        body = render(f"body_{tag}", "plate", variant, orientation)

        worst = 0.0
        worst_pos = travel
        for i in range(11):
            pos = travel * (10 - i) / 10.0
            stud = render(f"t{i}_{tag}", "sds_check", variant, orientation,
                          check_pos=pos, check_lift=0.0, check_extra=0.0)
            volume = shared(body, stud)
            if volume > worst:
                worst, worst_pos = volume, pos
        print(f"    worst of 11 drop positions: {worst:8.2f} mm^3 "
              f"at {worst_pos:.2f} mm")
        if worst > TOUCH_TOL:
            failures.append(
                f"{tag}: the stud intersects {worst:.1f}mm^3 at slot "
                f"position {worst_pos:.2f}; it will not drop freely")

        seated = render(f"seat_{tag}", "sds_check", variant, orientation,
                        check_pos=0.0, check_lift=0.0, check_extra=0.0)
        seated_v = shared(body, seated)
        print(f"    seated                    : {seated_v:8.2f} mm^3")
        if seated_v > TOUCH_TOL:
            failures.append(
                f"{tag}: the seated stud intersects {seated_v:.1f}mm^3")

        pull = axial_free + 1.5
        pulled = render(f"pull_{tag}", "sds_check", variant, orientation,
                        check_pos=0.0, check_lift=pull, check_extra=0.0)
        pull_v = shared(body, pulled)
        print(f"    pulled {pull:.3f} mm outward : {pull_v:8.2f} mm^3")
        if pull_v < BLOCK_MIN:
            failures.append(
                f"{tag}: pull-out meets only {pull_v:.1f}mm^3 of ledge; the "
                "head is not substantially captured")

        fat = render(f"fat_{tag}", "sds_check", variant, orientation,
                     check_pos=travel / 2, check_lift=0.0, check_extra=3.0)
        fat_v = shared(body, fat)
        print(f"    (fault) stud +3.0 mm      : {fat_v:8.2f} mm^3")
        if fat_v < CONTROL_MIN:
            failures.append(
                f"{tag}: an oversized stud produced only {fat_v:.1f}mm^3; "
                "the harness cannot detect a fit fault")
        print()

    if failures:
        print("=== FAIL ===")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("=== PASS ===")
    print("  the SDS150 drops freely, seats without interference, and its")
    print("  head is captured; the fit still matches the standoff's coupons")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
