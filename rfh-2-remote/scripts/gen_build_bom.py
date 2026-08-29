#!/usr/bin/env python3
"""Generate a build-quantity BOM from the canonical grouped BOM.

Defaults target the requested production batch:
  - 5 boards
  - 3 spare switches total
  - 2 spare resistors per resistor value line item

Input:
  bom/RFH-2-bom.csv

Output:
  bom/RFH-2-bom-5boards-spares.csv
"""
from __future__ import annotations

import argparse
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BOM_DIR = os.path.join(PROJ, "bom")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boards", type=int, default=5, help="How many full kits")
    parser.add_argument(
        "--switch-spares",
        type=int,
        default=3,
        help="Extra switches added once across the whole build",
    )
    parser.add_argument(
        "--resistor-spares",
        type=int,
        default=2,
        help="Extra pieces added to each resistor line item",
    )
    parser.add_argument(
        "--input",
        default=os.path.join(BOM_DIR, "RFH-2-bom.csv"),
        help="Grouped BOM CSV to scale",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(BOM_DIR, "RFH-2-bom-5boards-spares.csv"),
        help="Output CSV path",
    )
    args = parser.parse_args()
    if args.boards < 1:
        raise SystemExit("--boards must be >= 1")
    if args.switch_spares < 0 or args.resistor_spares < 0:
        raise SystemExit("spare counts must be >= 0")
    return args


def main() -> None:
    args = parse_args()
    with open(args.input, newline="", encoding="utf-8") as handle:
        grouped = list(csv.DictReader(handle))

    out_rows: list[dict[str, str | int]] = []
    for row in grouped:
        qty_per_board = int(row["Qty"])
        category = row["Category"]
        if category == "Test pad":
            continue
        base_qty = qty_per_board * args.boards
        spare_qty = 0
        if category == "Switch":
            spare_qty = args.switch_spares
        elif category == "Resistor":
            spare_qty = args.resistor_spares

        out_rows.append(
            {
                "TotalQty": base_qty + spare_qty,
                "Boards": args.boards,
                "QtyPerBoard": qty_per_board,
                "BuildQty": base_qty,
                "SpareQty": spare_qty,
                "Category": category,
                "Value": row["Value"],
                "References": row["References"],
                "Footprint": row["Footprint"],
                "Description": row["Description"],
            }
        )

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "TotalQty",
                "Boards",
                "QtyPerBoard",
                "BuildQty",
                "SpareQty",
                "Category",
                "Value",
                "References",
                "Footprint",
                "Description",
            ],
        )
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"input         : {args.input}")
    print(f"boards        : {args.boards}")
    print(f"switch spares : {args.switch_spares}")
    print(f"res spares    : {args.resistor_spares}")
    print(f"rows          : {len(out_rows)}")
    print(f"wrote         : {args.output}")


if __name__ == "__main__":
    main()