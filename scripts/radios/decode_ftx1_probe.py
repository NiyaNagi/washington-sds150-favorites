"""Decode record fields from a probe file saved by the RT Systems programmer.

Takes a file produced by ``make_ftx1_probe.py`` and edited in the programmer,
where every memory is on one frequency and differs by exactly one column.
Any byte that changes between two rows is caused by that column, so the field
offset and its encoding fall straight out of the comparison.

Usage::

    python scripts/radios/decode_ftx1_probe.py "Z:/path/ftx1-modes.FTX1"
    python scripts/radios/decode_ftx1_probe.py "Z:/path/ftx1-fields.FTX1"
"""
from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

from wasds150.export.ftx1_file import Ftx1File  # noqa: E402

#: Regions the probe deliberately varies, which therefore say nothing about
#: the field under test.
NAME_SPAN = (0x0F, 0x0F + 24)
COMMENT_START = 0x85

HEADER_LEN = 0x5E
RECORD_LEN = 295


def ignored(offset: int, record_len: int) -> bool:
    if NAME_SPAN[0] <= offset < NAME_SPAN[1]:
        return True
    return offset >= COMMENT_START


def _where(offset: int) -> str:
    """Describe a file offset as a record and offset within it."""
    if offset < HEADER_LEN:
        return f"header +0x{offset:02X}"
    index, within = divmod(offset - HEADER_LEN, RECORD_LEN)
    return f"record {index:4d} +0x{within:03X}"


def compare_whole_file(path: pathlib.Path, reference: pathlib.Path) -> int:
    """Every byte that differs between two files, anywhere.

    The record-by-record decode below only sees inside a record. A field the
    programmer keeps elsewhere - a membership table, a name list - would move
    bytes this finds and that one cannot.
    """
    left, right = reference.read_bytes(), path.read_bytes()
    if len(left) != len(right):
        print(f"sizes differ: {reference.name} {len(left)}, {path.name} {len(right)}")
    diffs = [i for i in range(min(len(left), len(right))) if left[i] != right[i]]
    print(f"{reference.name} -> {path.name}: {len(diffs)} differing bytes")
    if not diffs:
        print()
        print("Nothing changed anywhere in the file. Either the edit was not")
        print("saved, or the programmer does not store this for the FTX-1.")
        return 1
    print()
    outside = [i for i in diffs if i >= HEADER_LEN + RECORD_LEN * 999 or i < HEADER_LEN]
    for offset in diffs:
        print(f"  0x{offset:06X}  {_where(offset):<22} "
              f"{left[offset]:02X} -> {right[offset]:02X}")
    if outside:
        print()
        print(f"{len(outside)} of them lie outside the 999 memory records.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="The edited probe file")
    parser.add_argument(
        "--baseline",
        type=int,
        default=0,
        help="Row index to treat as the unchanged reference (default: first)",
    )
    parser.add_argument(
        "--against",
        help="A second .FTX1 to diff the whole file against, byte for byte, "
             "for a field that may not live inside a memory record",
    )
    args = parser.parse_args(argv)

    path = pathlib.Path(args.path)
    if args.against:
        reference = pathlib.Path(args.against)
        if not reference.is_file():
            raise SystemExit(f"reference not found at {reference}")
        return compare_whole_file(path, reference)
    ftx1 = Ftx1File.load(path)
    records = [r for r in ftx1.records[:999] if not r.empty]
    if len(records) < 2:
        raise SystemExit(f"{path} holds {len(records)} memories; need at least 2")

    reclen = len(records[0].raw)
    base = records[args.baseline]

    print(f"{path.name}: {len(records)} probe memories")
    print(f"baseline row: {base.name!r}")
    print()

    # Which offsets move at all? Those are the fields these rows exercise.
    moving = sorted(
        off
        for off in range(reclen)
        if not ignored(off, reclen) and len({r.raw[off] for r in records}) > 1
    )
    if not moving:
        print("No bytes differ outside name/comment.")
        print("The file looks unedited - the columns still need changing in the")
        print("programmer before this can decode anything.")
        return 1

    print(f"offsets that vary across the probe rows: {[hex(o) for o in moving]}")
    print()

    for off in moving:
        print(f"--- offset 0x{off:03X} ---")
        for r in records:
            if r.raw[off] != base.raw[off] or r is base:
                marker = "  (baseline)" if r is base else ""
                print(f"    {r.name:<14} 0x{off:03X} = {r.raw[off]:02X} "
                      f"({r.raw[off]:>3}){marker}")
        print()

    print("=" * 70)
    print("SUMMARY - one line per row, showing every byte that moved")
    print("=" * 70)
    header = "row".ljust(15) + "  ".join(f"0x{o:03X}" for o in moving)
    print(header)
    for r in records:
        cells = "   ".join(f"{r.raw[o]:02X} " for o in moving)
        flag = "" if r is base else ""
        print(f"{r.name:<15}{cells}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
