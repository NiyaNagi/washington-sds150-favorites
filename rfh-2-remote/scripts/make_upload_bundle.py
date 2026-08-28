#!/usr/bin/env python3
"""Build the single convenience bundle of everything needed to order boards.

JLCPCB accepts one board design per upload, so the bundle is a carrier for the
three per-board archives, not something to upload directly. It is rebuilt from
the tracked archives rather than assembled by hand so it cannot go stale
silently -- run this after regenerating any board.

Entries are written with a fixed timestamp so the bundle is byte-reproducible.
"""
from __future__ import annotations

import hashlib
import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
UPLOAD = os.path.join(PROJ, "jlcpcb-upload")
BUNDLE = os.path.join(PROJ, "RFH-2-JLCPCB-all-boards.zip")

FIXED_DATE = (2026, 8, 27, 0, 0, 0)

MEMBERS = [
    ("JLCPCB-1-RFH-2-cover.zip", os.path.join(UPLOAD, "JLCPCB-1-RFH-2-cover.zip")),
    ("JLCPCB-2-RFH-2-mainboard.zip", os.path.join(UPLOAD, "JLCPCB-2-RFH-2-mainboard.zip")),
    ("JLCPCB-3-RFH-2-bottom.zip", os.path.join(UPLOAD, "JLCPCB-3-RFH-2-bottom.zip")),
    ("ORDERING.md", os.path.join(PROJ, "ORDERING.md")),
]

READ_ME_FIRST = """RFH-2 remote - PCB fabrication bundle
=====================================

DO NOT UPLOAD THIS FILE TO JLCPCB.

JLCPCB accepts one board design per upload. This archive is a carrier for the
three board archives inside it. Upload each of them separately, as three
orders:

  JLCPCB-1-RFH-2-cover.zip       front cover / faceplate
  JLCPCB-2-RFH-2-mainboard.zip   keypad PCB (PY2RAF, rev C, unmodified)
  JLCPCB-3-RFH-2-bottom.zip      back plate with operating reference

Fab options for all three: 2 layer, 1.6 mm FR4, 1 oz copper, HASL, any mask
colour, white silkscreen. Defaults are fine for everything else. Per-board
detail is in ORDERING.md.

Two things that look like faults but are not:

1. The cover and back plate have no copper at all. Their copper and paste
   layers are intentionally empty, so a blank copper layer in the DFM preview
   is correct rather than a missing file.

2. The mainboard drill file is named drills.xln, which is what upstream ships.
   Do not rename it. Renaming it to .DRL caused a parser to report zero holes
   on a board that has 122.

Before ordering the cover, settle the standoff height -- it does not change
any gerber but it decides whether the buttons reach through the faceplate.
See ASSEMBLY.md in the repository.

Boards only. Components, screws and standoffs are not part of a PCB order;
see bom/ in the repository.

Source, BOM and build notes:
https://github.com/NiyaNagi/washington-sds150-favorites/tree/main/rfh-2-remote

Keypad design: PY2RAF, github.com/rfrht/RFH-2, GPL-3.0.
"""


def main() -> None:
    missing = [name for name, path in MEMBERS if not os.path.exists(path)]
    if missing:
        raise SystemExit(f"missing input(s): {', '.join(missing)}")

    with zipfile.ZipFile(BUNDLE, "w", zipfile.ZIP_DEFLATED) as bundle:
        info = zipfile.ZipInfo("READ-ME-FIRST.txt", date_time=FIXED_DATE)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        bundle.writestr(info, READ_ME_FIRST)

        for arcname, path in MEMBERS:
            with open(path, "rb") as handle:
                data = handle.read()
            info = zipfile.ZipInfo(arcname, date_time=FIXED_DATE)
            # The inner archives are already deflated; storing them avoids a
            # pointless second pass and keeps their bytes recoverable as-is.
            info.compress_type = (
                zipfile.ZIP_STORED if arcname.endswith(".zip") else zipfile.ZIP_DEFLATED
            )
            info.external_attr = 0o644 << 16
            bundle.writestr(info, data)

    with open(BUNDLE, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest().upper()

    with zipfile.ZipFile(BUNDLE) as check:
        bad = check.testzip()
        if bad is not None:
            raise SystemExit(f"bundle is corrupt at {bad}")
        for arcname, path in MEMBERS:
            if check.read(arcname) != open(path, "rb").read():
                raise SystemExit(f"bundle member differs from source: {arcname}")
            print(f"  verified  {arcname}")

    print(f"\nwrote   {BUNDLE}")
    print(f"size    {os.path.getsize(BUNDLE):,} bytes")
    print(f"sha256  {digest}")


if __name__ == "__main__":
    main()
