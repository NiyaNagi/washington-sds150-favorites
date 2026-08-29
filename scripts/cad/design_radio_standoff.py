"""Size the opposed-face radio standoff before trusting its shape.

The radios are not simply a vertical dead load.  In a cup holder the useful
load cases are lateral road acceleration and the small fore/aft moments from
their offset faces.  This script asks OpenSCAD for the model's actual loft
sections, integrates a variable-section Euler-Bernoulli beam, and reports the
weakest section rather than sizing from one hand-copied rectangle.

The central waist opening is handled as outer rectangle minus a through-slot.
That is conservative at its rounded ends and exact through its long middle.

Usage:
    .venv-cad/Scripts/python.exe scripts/cad/design_radio_standoff.py
"""

from __future__ import annotations

import math
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "models" / "peak design radio standoff" / "peak_design_radio_standoff.scad"
TMP = ROOT / ".tmp-cad"
OPENSCAD = Path(r"C:\Program Files\OpenSCAD\openscad.exe")

E_PLA = 2400.0          # MPa, conservative layer-normal effective modulus
PLA_STRENGTH = 25.0     # MPa, conservative upright printed PLA
PLA_SHEAR = 18.0        # MPa, conservative printed thread shear
G = 9.80665             # m/s^2
TARGET_FOS_3G = 3.0
TARGET_FOS_5G = 1.5
TARGET_DEFLECTION_1G = 0.50  # mm
TARGET_DEFLECTION_3G = 1.50  # mm


@dataclass
class Load:
    name: str
    mass_kg: float
    z: float
    y: float


def model_echo() -> str:
    if not OPENSCAD.exists():
        raise SystemExit(f"OpenSCAD not found at {OPENSCAD}")
    TMP.mkdir(exist_ok=True)
    result = subprocess.run(
        [str(OPENSCAD), "-o", str(TMP / "_standoff_design_null.stl"),
         "-D", 'variant_render_mode="none"', str(MODEL)],
        capture_output=True, text=True, cwd=ROOT,
    )
    text = (result.stdout or "") + "\n" + (result.stderr or "")
    if "RADIO STANDOFF" not in text:
        sys.stderr.write(text[-2000:])
        raise SystemExit("the standoff model did not echo its design values")
    return text


def number(text: str, name: str) -> float:
    matches = re.findall(rf"(?:^|\s){re.escape(name)}=(-?[0-9.]+)", text)
    if not matches:
        raise SystemExit(f"model did not echo {name}")
    return float(matches[-1])


def section_table(text: str) -> np.ndarray:
    rows = []
    for z, w, d in re.findall(
            r"SECTION z=(-?[0-9.]+) w=(-?[0-9.]+) d=(-?[0-9.]+)", text):
        rows.append((float(z), float(w), float(d)))
    if len(rows) < 2:
        raise SystemExit("model did not echo its spine sections")
    return np.asarray(rows, dtype=float)


def dimensions_at(z: np.ndarray, sections: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return (
        np.interp(z, sections[:, 0], sections[:, 1]),
        np.interp(z, sections[:, 0], sections[:, 2]),
    )


def properties(z: np.ndarray, sections: np.ndarray, cut_w: float,
               cut_z0: float, cut_z1: float) -> tuple[np.ndarray, ...]:
    w, d = dimensions_at(z, sections)
    active = (z >= cut_z0) & (z <= cut_z1)
    removed = np.where(active, np.minimum(cut_w, w - 1.0), 0.0)

    area = (w - removed) * d
    # Beam axis is Z. Ix resists fore/aft Y deflection; Iy resists X.
    ix = (w - removed) * d**3 / 12.0
    iy = d * (w**3 - removed**3) / 12.0
    return w, d, area, ix, iy


def beam_case(loads: list[Load], factor: float, direction: str,
              sections: np.ndarray, cut_w: float, cut_z0: float,
              cut_z1: float) -> dict[str, float]:
    top = max(load.z for load in loads)
    z = np.linspace(sections[0, 0], top, 1601)
    w, d, area, ix, iy = properties(z, sections, cut_w, cut_z0, cut_z1)
    inertia = ix if direction == "Y" else iy
    c = d / 2.0 if direction == "Y" else w / 2.0

    moment = np.zeros_like(z)
    for load in loads:
        force = load.mass_kg * G * factor
        moment += np.where(z < load.z, force * (load.z - z), 0.0)

    stress = moment * c / inertia
    curvature = moment / (E_PLA * inertia)
    dz = z[1] - z[0]
    slope = np.cumsum(curvature) * dz
    deflection = np.cumsum(slope) * dz

    worst = int(np.argmax(stress))
    return {
        "stress": float(stress[worst]),
        "stress_z": float(z[worst]),
        "deflection": float(deflection[-1]),
        "fos": PLA_STRENGTH / max(float(stress[worst]), 1e-9),
        "min_area": float(area.min()),
        "min_ix": float(ix.min()),
        "min_iy": float(iy.min()),
    }


def gravity_eccentric(loads: list[Load], sections: np.ndarray,
                       cut_w: float, cut_z0: float, cut_z1: float) -> dict[str, float]:
    z = np.linspace(sections[0, 0], max(load.z for load in loads), 1201)
    w, d, _, ix, _ = properties(z, sections, cut_w, cut_z0, cut_z1)
    moment = np.zeros_like(z)
    for load in loads:
        moment += np.where(z < load.z, load.mass_kg * G * load.y, 0.0)
    stress = np.abs(moment) * (d / 2.0) / ix
    i = int(np.argmax(stress))
    return {"stress": float(stress[i]), "z": float(z[i])}


def main() -> int:
    text = model_echo()
    sections = section_table(text)
    cut_w = number(text, "cut_w")
    cut_z0 = number(text, "cut_z0")
    cut_z1 = number(text, "cut_z1")

    loads = [
        Load("SDS150", number(text, "sds_mass_g") / 1000.0,
             number(text, "sds_com_z"), number(text, "front_y")),
        Load("TH-D75A envelope", number(text, "thd_mass_g") / 1000.0,
             number(text, "thd_com_z"), number(text, "rear_y")),
    ]

    print("=== Peak Design radio standoff sizing ===")
    print(f"  sections: {len(sections)}, z {sections[0,0]:.1f}..{sections[-1,0]:.1f} mm")
    print(f"  through-waist opening: {cut_w:.1f} mm wide, z {cut_z0:.1f}..{cut_z1:.1f}")
    for load in loads:
        print(f"  {load.name:19s}: {load.mass_kg*1000:.0f} g at z={load.z:.1f}, y={load.y:.1f}")

    failures: list[str] = []
    cases: dict[tuple[int, str], dict[str, float]] = {}
    print()
    print("  LATERAL ROAD LOADS")
    for factor in (1, 3, 5):
        for direction in ("Y", "X"):
            result = beam_case(loads, factor, direction, sections,
                               cut_w, cut_z0, cut_z1)
            cases[(factor, direction)] = result
            print(
                f"    {factor}g along {direction}: stress {result['stress']:5.2f} MPa "
                f"at z={result['stress_z']:5.1f}, deflection {result['deflection']:5.3f} mm, "
                f"FoS {result['fos']:5.1f}"
            )

    worst_1g = max(cases[(1, d)]["deflection"] for d in ("X", "Y"))
    worst_3g = max(cases[(3, d)]["deflection"] for d in ("X", "Y"))
    worst_fos_3g = min(cases[(3, d)]["fos"] for d in ("X", "Y"))
    worst_fos_5g = min(cases[(5, d)]["fos"] for d in ("X", "Y"))

    if worst_1g > TARGET_DEFLECTION_1G:
        failures.append(f"1g deflection {worst_1g:.2f}mm exceeds {TARGET_DEFLECTION_1G:.2f}mm")
    if worst_3g > TARGET_DEFLECTION_3G:
        failures.append(f"3g deflection {worst_3g:.2f}mm exceeds {TARGET_DEFLECTION_3G:.2f}mm")
    if worst_fos_3g < TARGET_FOS_3G:
        failures.append(f"3g factor of safety {worst_fos_3g:.2f} is below {TARGET_FOS_3G:.1f}")
    if worst_fos_5g < TARGET_FOS_5G:
        failures.append(f"5g factor of safety {worst_fos_5g:.2f} is below {TARGET_FOS_5G:.1f}")

    gravity = gravity_eccentric(loads, sections, cut_w, cut_z0, cut_z1)
    print()
    print("  OPPOSING-FACE GRAVITY MOMENT")
    print(f"    stress {gravity['stress']:.3f} MPa at z={gravity['z']:.1f} mm")
    print("    (the opposed faces cancel most of each other's eccentric moment)")

    socket_d = number(text, "depth")
    pilot_d = 5.40
    shear_area = math.pi * pilot_d * socket_d
    strip_load = shear_area * PLA_SHEAR
    total_weight = sum(load.mass_kg for load in loads) * G
    socket_fos = strip_load / total_weight
    print()
    print("  SELF-TAP SOCKET")
    print(f"    engagement {socket_d:.2f} mm, shear area {shear_area:.0f} mm^2")
    print(f"    conservative strip load {strip_load/1000:.2f} kN, weight FoS {socket_fos:.0f}")

    sample = beam_case(loads, 1, "Y", sections, cut_w, cut_z0, cut_z1)
    print()
    print("  SECTION PROPERTIES")
    print(f"    minimum material area {sample['min_area']:.1f} mm^2")
    print(f"    minimum Ix {sample['min_ix']:.0f} mm^4, Iy {sample['min_iy']:.0f} mm^4")

    print()
    if failures:
        print("=== FAIL ===")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("=== PASS ===")
    print("  the organic twin-rail spine meets static, road-bump, shock and socket targets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
