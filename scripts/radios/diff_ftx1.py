"""Byte-diff two ``.FTX1`` files.

The RT Systems format is undocumented, so the reliable way to learn where a
field lives is to change exactly one thing in the programmer, save, and see
which bytes moved.  This reports the changed runs and, where the offsets fall
on the 295-byte record grid, which record and field they belong to.
"""
from __future__ import annotations

import argparse
import pathlib
import struct
import sys
from typing import List, Tuple

RECORD_LEN = 295
MEMORY_BASE = 0x5F

KNOWN_FIELDS = {
    0x00: "rx_hz (uint32 LE)",
    0x04: "tx_hz (uint32 LE)",
    0x0E: "name (utf-16-le)",
    0x2C: "tone mode",
    0x2D: "tx tone index",
    0x2E: "rx tone index",
    0x84: "comment (utf-16-le)",
}


def changed_runs(a: bytes, b: bytes, gap: int = 8) -> List[Tuple[int, int]]:
    """Offsets that differ, coalesced into runs separated by < ``gap`` bytes."""
    diffs = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
    if not diffs:
        return []
    runs = []
    start = prev = diffs[0]
    for offset in diffs[1:]:
        if offset - prev > gap:
            runs.append((start, prev))
            start = offset
        prev = offset
    runs.append((start, prev))
    return runs


def field_at(rel: int) -> str:
    within = rel % RECORD_LEN
    for offset, name in sorted(KNOWN_FIELDS.items(), reverse=True):
        if within >= offset:
            return f"+0x{within:02X} ({name})" if within == offset else f"+0x{within:02X} (inside {name})"
    return f"+0x{within:02X}"


def show(data: bytes, offset: int, length: int = 32) -> str:
    chunk = data[offset : offset + length]
    return " ".join(f"{b:02X}" for b in chunk)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--context", type=int, default=24)
    args = parser.parse_args(argv)

    a = pathlib.Path(args.before).read_bytes()
    b = pathlib.Path(args.after).read_bytes()

    print(f"before: {args.before}  {len(a)} bytes")
    print(f"after : {args.after}  {len(b)} bytes")
    if len(a) != len(b):
        print("!! sizes differ")
    print()

    runs = changed_runs(a, b)
    print(f"{len(runs)} changed run(s)")
    print()

    for start, end in runs:
        span = end - start + 1
        rel = start - MEMORY_BASE
        slot = rel // RECORD_LEN
        aligned = rel % RECORD_LEN
        print(f"0x{start:06X}..0x{end:06X}  ({span} bytes)")
        print(f"    rel to memory base : {rel}")
        print(f"    if on the 295 grid : slot {slot}, {field_at(rel)}")
        print(f"    before: {show(a, start, args.context)}")
        print(f"    after : {show(b, start, args.context)}")
        # If this looks like a frequency field, decode it.
        if span >= 4:
            try:
                before_hz = struct.unpack_from("<I", a, start)[0]
                after_hz = struct.unpack_from("<I", b, start)[0]
                if 30_000 <= after_hz <= 470_000_000:
                    print(
                        f"    as uint32 LE MHz   : {before_hz / 1e6:.6f} -> {after_hz / 1e6:.6f}"
                    )
            except struct.error:
                pass
        print()

    if runs:
        first = runs[0][0]
        print("If the first run is a record's rx_hz, that record starts at "
              f"0x{first:06X} and the region base is 0x{first:06X} minus "
              "n*295 for whichever record index the programmer showed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
