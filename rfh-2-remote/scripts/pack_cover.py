#!/usr/bin/env python3
"""Repackage the generated cover into its JLCPCB upload archive.

Two things this does that a manual zip would not:

  * Renames the Excellon program from .TXT to .DRL. Upstream's convention is a
    .txt drill file, but a fab-side parser presented with a .txt alongside any
    readme has to guess which is the drill, and guessing wrong yields a board
    with no holes. .DRL is unambiguous.
  * Refuses to ship if any layer other than the silkscreen changed. The cover
    exists to carry artwork; if regenerating it moved a mounting hole or a
    plunger cutout, that is a bug, not an edit, and should stop the build.

Entry timestamps are fixed so the archive is byte-reproducible.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BUILD = os.environ.get("RFH2_COVER_OUT", os.path.join(PROJ, "build", "cover_gerbers"))
LOOSE = os.path.join(PROJ, "gerbers", "cover")
ZIP = os.path.join(PROJ, "jlcpcb-upload", "JLCPCB-1-RFH-2-cover.zip")

FIXED_DATE = (2026, 8, 27, 0, 0, 0)

# built name -> shipped name
RENAME = {"RFH-2-cover.TXT": "RFH-2-cover.DRL"}

# Layers that carry no artwork; a change here means geometry moved.
GEOMETRY = [
    "RFH-2-cover.GKO",
    "RFH-2-cover.DRL",
    "RFH-2-cover.GTL",
    "RFH-2-cover.GBL",
    "RFH-2-cover.GTS",
    "RFH-2-cover.GBS",
    "RFH-2-cover.GBO",
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def main() -> int:
    if not os.path.isdir(BUILD):
        sys.exit(f"no build output at {BUILD} -- run gen_cover.py first")

    built: dict[str, bytes] = {}
    for name in sorted(os.listdir(BUILD)):
        with open(os.path.join(BUILD, name), "rb") as handle:
            built[RENAME.get(name, name)] = handle.read()

    with zipfile.ZipFile(ZIP) as archive:
        previous = {n: archive.read(n) for n in archive.namelist()}

    if set(built) != set(previous):
        added = sorted(set(built) - set(previous))
        removed = sorted(set(previous) - set(built))
        sys.exit(f"file set changed -- added {added}, removed {removed}")

    moved = [n for n in GEOMETRY if built[n] != previous[n]]
    if moved:
        print("REFUSING TO PACK: non-silkscreen layers changed:")
        for name in moved:
            print(f"  {name}")
            print(f"    was {digest(previous[name])[:32]}")
            print(f"    now {digest(built[name])[:32]}")
        print("\nThe cover's geometry comes from RFH-2.brd and should not move")
        print("when only the artwork is edited. Investigate before shipping.")
        return 1

    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(built):
            info = zipfile.ZipInfo(name, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, built[name])

    os.makedirs(LOOSE, exist_ok=True)
    for name, data in built.items():
        with open(os.path.join(LOOSE, name), "wb") as handle:
            handle.write(data)

    silk = "RFH-2-cover.GTO"
    print(f"geometry layers unchanged ({len(GEOMETRY)} checked)")
    print(f"silkscreen  {len(previous[silk]):>7,} -> {len(built[silk]):>7,} bytes")
    print(f"wrote       {ZIP}  ({os.path.getsize(ZIP):,} bytes)")
    print(f"refreshed   {LOOSE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
