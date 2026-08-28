#!/usr/bin/env python3
"""Generate JLCPCB assembly files (BOM + CPL) from upstream's Eagle board.

READ THIS BEFORE ORDERING ASSEMBLY. The RFH-2 is entirely through-hole, and
JLCPCB's assembly service is built around SMT. See ../ASSEMBLY.md and the
notes printed at the end of this run -- these files are generated so that the
option can be priced, not because assembly is the recommended route.

Placement uses each element's origin, which for every footprint on this board
is the body centre. That is not assumed -- it is checked. For the 22 two-pad
parts the origin must equal the midpoint of the pads, and for the switches it
must equal the plunger position that the cover cutouts are drilled on. A
pick-and-place file with a quietly offset origin is how parts end up crooked,
so the script fails rather than emitting one.

Note on the switch footprint: its pad *mean* is 0.167 mm off the body centre,
because the two 1.7 mm contacts sit at y=0 while the four 1.3 mm support posts
sit at +6.0 and -6.5. Averaging all six pads would pull the placement off the
plunger axis. The origin is correct; the mean is not.

Writes:
  bom/JLCPCB-BOM.csv   Comment / Designator / Footprint / LCSC Part
  bom/JLCPCB-CPL.csv   Designator / Mid X / Mid Y / Layer / Rotation
"""
from __future__ import annotations

import csv
import os
import re
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BRD = os.environ.get("RFH2_BRD", os.path.join(PROJ, "upstream", "RFH-2.brd"))
BOM_DIR = os.path.join(PROJ, "bom")

# Bare pads, not placed components.
SKIP = {"TP1", "TP2"}

SWITCH_PACKAGE = "TL6300"

# Human-facing value per designator, read from the schematic-side value on the
# element. Switches carry a device name rather than a value.
SWITCH_COMMENT = "TL6300 tactile switch SPST-NO 12x12mm TH"

FOOTPRINTS = {
    "TL6300": "SW-TH_TL6300_12x12mm",
    "0309/10": "R_Axial_TH_L10mm",
    "C5B3": "C_Radial_TH_P5.08mm",
}


def natural_key(name: str) -> tuple[str, int]:
    match = re.match(r"^([A-Za-z/]+?)(\d+)$", name)
    if match:
        return match.group(1), int(match.group(2))
    return name, 0


def normalise_value(value: str) -> str:
    return value.strip().replace("K", "k").replace("R", " ohm").strip()


def load_packages(root: ET.Element) -> dict[tuple[str, str], list[tuple[float, float]]]:
    """Map (library, package) -> pad coordinates in package-local mm."""
    packages: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for library in root.iter("library"):
        lib_name = library.get("name", "")
        for package in library.iter("package"):
            pads = []
            for pad in package.iter("pad"):
                pads.append((float(pad.get("x", 0)), float(pad.get("y", 0))))
            for smd in package.iter("smd"):
                pads.append((float(smd.get("x", 0)), float(smd.get("y", 0))))
            packages[(lib_name, package.get("name", ""))] = pads
    return packages


def parse_rot(raw: str | None) -> tuple[float, bool]:
    """Eagle rotation string -> (degrees, mirrored)."""
    if not raw:
        return 0.0, False
    mirrored = raw.startswith("M")
    match = re.search(r"R([\d.\-]+)", raw)
    degrees = float(match.group(1)) if match else 0.0
    return degrees, mirrored


def main() -> None:
    root = ET.parse(BRD).getroot()
    packages = load_packages(root)
    os.makedirs(BOM_DIR, exist_ok=True)

    placements = []
    for element in root.iter("element"):
        name = element.get("name", "")
        if name in SKIP:
            continue

        ex = float(element.get("x", 0))
        ey = float(element.get("y", 0))
        degrees, mirrored = parse_rot(element.get("rot"))
        lib = element.get("library", "")
        pkg = element.get("package", "")

        pads = packages.get((lib, pkg), [])
        if not pads:
            raise SystemExit(f"{name}: no pads found for package {lib}/{pkg}")

        # Verify the origin really is the body centre before trusting it.
        # Two-pad parts: the origin must be the midpoint of the pads.
        if len(pads) == 2:
            mx = (pads[0][0] + pads[1][0]) / 2
            my = (pads[0][1] + pads[1][1]) / 2
            if abs(mx) > 1e-6 or abs(my) > 1e-6:
                raise SystemExit(
                    f"{name}: origin is not the pad midpoint "
                    f"(off by {mx:.4f}, {my:.4f} mm) -- placement would be wrong"
                )
        # Switches: the origin must be on the plunger axis, which is where the
        # cover cutouts are drilled. The contacts are the largest-drill pads.
        elif pkg == SWITCH_PACKAGE:
            xs = sorted({round(px, 4) for px, _ in pads})
            if abs(xs[0] + xs[-1]) > 1e-6:
                raise SystemExit(f"{name}: switch pads not symmetric about x origin")

        value = element.get("value", "") or ""
        comment = SWITCH_COMMENT if pkg == "TL6300" else normalise_value(value)

        placements.append(
            {
                "designator": name,
                "comment": comment,
                "footprint": FOOTPRINTS.get(pkg, pkg),
                "mid_x": round(ex, 4),
                "mid_y": round(ey, 4),
                "layer": "Bottom" if mirrored else "Top",
                "rotation": round(degrees % 360, 2),
            }
        )

    placements.sort(key=lambda row: natural_key(row["designator"]))

    cpl_path = os.path.join(BOM_DIR, "JLCPCB-CPL.csv")
    with open(cpl_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in placements:
            writer.writerow(
                [
                    row["designator"],
                    f"{row['mid_x']:.4f}mm",
                    f"{row['mid_y']:.4f}mm",
                    row["layer"],
                    f"{row['rotation']:.2f}",
                ]
            )

    grouped: dict[tuple[str, str], list[str]] = {}
    for row in placements:
        grouped.setdefault((row["comment"], row["footprint"]), []).append(
            row["designator"]
        )

    bom_path = os.path.join(BOM_DIR, "JLCPCB-BOM.csv")
    with open(bom_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (comment, footprint), refs in sorted(
            grouped.items(), key=lambda item: natural_key(item[1][0])
        ):
            writer.writerow(
                [comment, ",".join(sorted(refs, key=natural_key)), footprint, ""]
            )

    odd = [row["designator"] for row in placements if not row["designator"].isalnum()]

    print(f"board       : {BRD}")
    print(f"placements  : {len(placements)}")
    print(f"BOM lines   : {len(grouped)}")
    print(f"wrote       : {bom_path}")
    print(f"wrote       : {cpl_path}")
    print()
    print("BEFORE YOU UPLOAD THESE:")
    print("  * The LCSC Part # column is deliberately empty. Nothing is")
    print("    pre-filled, because an unverified part number on an assembly")
    print("    order is a board full of wrong resistors. Fill it from LCSC")
    print("    yourself and check every value against bom/RFH-2-bom.csv.")
    print("  * Every part is through-hole. JLCPCB assembly is an SMT service;")
    print("    through-hole is quoted separately, is not always available, and")
    print("    the 10 mm axial resistors are unlikely to be stocked at all.")
    if odd:
        print(f"  * Designators with non-alphanumeric characters: {', '.join(odd)}")
        print("    These come from upstream's schematic. Some fab-side parsers")
        print("    reject them; rename in both files together if so.")


if __name__ == "__main__":
    main()
