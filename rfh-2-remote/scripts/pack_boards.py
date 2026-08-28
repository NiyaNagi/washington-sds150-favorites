#!/usr/bin/env python3
"""Repackage a generated board into its JLCPCB upload archive.

Handles the two boards this project generates -- the cover and the back plate.
The main board is upstream's and is never repacked.

Two things this does that a manual zip would not:

  * Renames the cover's Excellon program from .TXT to .DRL. Upstream's
    convention is a .txt drill file, but a fab-side parser presented with a
    .txt alongside any readme has to guess which is the drill, and guessing
    wrong yields a board with no holes. .DRL is unambiguous.
  * Refuses to ship if any layer other than the silkscreen changed. These
    boards exist to carry artwork; if regenerating one moved a mounting hole
    or a plunger cutout, that is a bug, not an edit, and should stop the
    build.

Entry timestamps are fixed so the archives are byte-reproducible.

Usage:  python pack_boards.py [cover|bottom|all]
"""
from __future__ import annotations

import hashlib
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)

FIXED_DATE = (2026, 8, 27, 0, 0, 0)

BOARDS = {
    "cover": {
        "build": os.path.join(PROJ, "build", "cover_gerbers"),
        "loose": os.path.join(PROJ, "gerbers", "cover"),
        "zip": os.path.join(PROJ, "jlcpcb-upload", "JLCPCB-1-RFH-2-cover.zip"),
        "rename": {"RFH-2-cover.TXT": "RFH-2-cover.DRL"},
        "silk": "RFH-2-cover.GTO",
    },
    "bottom": {
        "build": os.path.join(PROJ, "build", "bottom_gerbers"),
        "loose": os.path.join(PROJ, "gerbers", "bottom"),
        "zip": os.path.join(PROJ, "jlcpcb-upload", "JLCPCB-3-RFH-2-bottom.zip"),
        "rename": {},
        # The back plate's artwork is on the bottom layer, mirrored, so it
        # reads correctly when the unit is turned over.
        "silk": "RFH-2-bottom.GBO",
    },
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pack(name: str) -> int:
    spec = BOARDS[name]
    build = spec["build"]
    if not os.path.isdir(build):
        sys.exit(f"no build output at {build} -- run the generator first")

    built: dict[str, bytes] = {}
    for filename in sorted(os.listdir(build)):
        with open(os.path.join(build, filename), "rb") as handle:
            built[spec["rename"].get(filename, filename)] = handle.read()

    with zipfile.ZipFile(spec["zip"]) as archive:
        previous = {n: archive.read(n) for n in archive.namelist()}

    if set(built) != set(previous):
        added = sorted(set(built) - set(previous))
        removed = sorted(set(previous) - set(built))
        sys.exit(f"{name}: file set changed -- added {added}, removed {removed}")

    geometry = [n for n in sorted(previous) if n != spec["silk"]]
    moved = [n for n in geometry if built[n] != previous[n]]
    if moved:
        print(f"REFUSING TO PACK {name}: non-silkscreen layers changed:")
        for filename in moved:
            print(f"  {filename}")
            print(f"    was {digest(previous[filename])[:32]}")
            print(f"    now {digest(built[filename])[:32]}")
        print("\nGeometry comes from RFH-2.brd and should not move when only")
        print("the artwork is edited. Investigate before shipping.")
        return 1

    with zipfile.ZipFile(spec["zip"], "w", zipfile.ZIP_DEFLATED) as archive:
        for filename in sorted(built):
            info = zipfile.ZipInfo(filename, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, built[filename])

    os.makedirs(spec["loose"], exist_ok=True)
    for filename, data in built.items():
        with open(os.path.join(spec["loose"], filename), "wb") as handle:
            handle.write(data)

    silk = spec["silk"]
    print(f"[{name}] geometry layers unchanged ({len(geometry)} checked)")
    print(f"[{name}] silkscreen {len(previous[silk]):>7,} -> {len(built[silk]):>7,} bytes")
    print(f"[{name}] wrote {spec['zip']}  ({os.path.getsize(spec['zip']):,} bytes)")
    return 0


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    names = list(BOARDS) if which == "all" else [which]
    for name in names:
        if name not in BOARDS:
            sys.exit(f"unknown board {name!r}; expected one of {list(BOARDS)} or 'all'")
    return max(pack(name) for name in names)


if __name__ == "__main__":
    sys.exit(main())
