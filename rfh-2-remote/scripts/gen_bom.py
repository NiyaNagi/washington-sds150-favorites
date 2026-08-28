#!/usr/bin/env python3
"""Generate the RFH-2 BOM from upstream's Eagle schematic.

The resistor ladder is the whole design: every button is identified by the
voltage its resistor divides down to, so a wrong value is a wrong button, not
a tolerance problem. Nothing here is hand-typed -- values and reference
designators are read out of `upstream/RFH-2.sch` so they cannot drift.

Writes:
  bom/RFH-2-bom.csv           one row per placed part, grouped by value
  bom/RFH-2-bom-flat.csv      one row per reference designator
"""
from __future__ import annotations

import csv
import os
import re
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
SCH = os.environ.get("RFH2_SCH", os.path.join(PROJ, "upstream", "RFH-2.sch"))
BOM_DIR = os.path.join(PROJ, "bom")

# Parts that appear in the schematic but are not purchased items.
NON_PARTS = {"FRAME1", "GND1"}

# Bare copper features on the board, not stocked components.
TEST_PADS = {"TP1", "TP2"}

SWITCH_DEVICESET = "TL6300-SPST"

DESCRIPTIONS = {
    "R": "Resistor, 1/4 W, 1% metal film, axial, 10 mm lead pitch",
    "C": "Capacitor, 22 nF 50 V film/ceramic, radial, 5 mm lead pitch",
}


def natural_key(name: str) -> tuple[str, int]:
    match = re.match(r"^([A-Za-z/]+?)(\d+)$", name)
    if match:
        return match.group(1), int(match.group(2))
    return name, 0


def normalise_value(value: str) -> str:
    """Upstream writes 12k on R16 and 12K on R19. Same part."""
    return value.strip().replace("K", "k").replace("R", " ohm").strip()


def ohms(value: str) -> float:
    match = re.match(r"^(\d+)(?:(k)(\d*)| ohm)?$", normalise_value(value))
    if not match:
        return float("inf")
    whole, kilo, frac = match.groups()
    result = float(whole)
    if kilo:
        result *= 1000
        if frac:
            result += float(frac) * 10 ** (3 - len(frac))
    return result


def load_parts() -> list[dict[str, str]]:
    root = ET.parse(SCH).getroot()
    parts = root.find(".//parts")
    if parts is None:
        raise SystemExit(f"no <parts> section in {SCH}")

    rows = []
    for part in parts.findall("part"):
        name = part.get("name", "")
        if name in NON_PARTS:
            continue
        rows.append(
            {
                "ref": name,
                "value": part.get("value", "") or "",
                "deviceset": part.get("deviceset", ""),
                "package": part.get("device", ""),
            }
        )
    rows.sort(key=lambda row: natural_key(row["ref"]))
    return rows


def classify(row: dict[str, str]) -> tuple[str, str, str]:
    """Return (category, value, description) for a schematic part."""
    ref = row["ref"]
    if row["deviceset"] == SWITCH_DEVICESET:
        return (
            "Switch",
            "TL6300 series",
            "Tactile switch, SPST-NO momentary, 12 x 12 mm, through hole, "
            "7.3 mm plunger (DigiKey EG6117-ND per upstream README)",
        )
    if ref in TEST_PADS:
        return ("Test pad", "-", "Bare PCB pad, no part to buy")
    prefix = re.match(r"^([A-Za-z]+)", ref)
    key = prefix.group(1) if prefix else ""
    if key == "R":
        return ("Resistor", normalise_value(row["value"]), DESCRIPTIONS["R"])
    if key == "C":
        return ("Capacitor", row["value"], DESCRIPTIONS["C"])
    return ("Other", row["value"], row["deviceset"])


def main() -> None:
    rows = load_parts()
    os.makedirs(BOM_DIR, exist_ok=True)

    flat = []
    for row in rows:
        category, value, description = classify(row)
        flat.append(
            {
                "Reference": row["ref"],
                "Category": category,
                "Value": value,
                "Footprint": row["package"] or row["deviceset"],
                "Description": description,
            }
        )

    flat_path = os.path.join(BOM_DIR, "RFH-2-bom-flat.csv")
    with open(flat_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["Reference", "Category", "Value", "Footprint", "Description"],
        )
        writer.writeheader()
        writer.writerows(flat)

    grouped: dict[tuple[str, str, str, str], list[str]] = {}
    for entry in flat:
        key = (
            entry["Category"],
            entry["Value"],
            entry["Footprint"],
            entry["Description"],
        )
        grouped.setdefault(key, []).append(entry["Reference"])

    def group_sort(item: tuple[tuple[str, str, str, str], list[str]]) -> tuple:
        (category, value, _, _), refs = item
        order = {"Switch": 0, "Resistor": 1, "Capacitor": 2}.get(category, 3)
        return (order, ohms(value) if category == "Resistor" else 0, value, refs[0])

    grouped_path = os.path.join(BOM_DIR, "RFH-2-bom.csv")
    with open(grouped_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["Qty", "Category", "Value", "References", "Footprint", "Description"]
        )
        for (category, value, footprint, description), refs in sorted(
            grouped.items(), key=group_sort
        ):
            writer.writerow(
                [
                    len(refs),
                    category,
                    value,
                    " ".join(sorted(refs, key=natural_key)),
                    footprint,
                    description,
                ]
            )

    placed = [entry for entry in flat if entry["Category"] != "Test pad"]
    print(f"schematic     : {SCH}")
    print(f"placed parts  : {len(placed)}")
    print(f"line items    : {len(grouped)}")
    print(f"wrote         : {grouped_path}")
    print(f"wrote         : {flat_path}")


if __name__ == "__main__":
    main()
