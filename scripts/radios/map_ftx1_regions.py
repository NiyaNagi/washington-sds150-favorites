"""Map the record regions in an RT Systems ``.FTX1`` file.

The programmer presents four tables - Memories, Limit Memories, Home and
60 Meter Memories - and each is a run of 295-byte records somewhere in the
file.  The runs are not contiguous and do not all share the same alignment,
so the only reliable way to find one is to look for its data.

This works by treating every byte offset as a candidate record start and
asking whether the first eight bytes decode as a plausible receive/transmit
frequency pair, then grouping the hits into runs with a constant stride.
"""
from __future__ import annotations

import argparse
import pathlib
import struct
import sys
from typing import List, Tuple

RECORD_LEN = 295
HEADER_LEN = 0x5F

#: The FTX-1 tunes 30 kHz to 470 MHz. Anything outside that is not a
#: frequency, whatever else it may be.
MIN_HZ = 30_000
MAX_HZ = 470_000_000


def looks_like_record(data: bytes, offset: int) -> bool:
    if offset + 8 > len(data):
        return False
    rx, tx = struct.unpack_from("<II", data, offset)
    if not (MIN_HZ <= rx <= MAX_HZ):
        return False
    if tx != 0 and not (MIN_HZ <= tx <= MAX_HZ):
        return False
    # Real channels are on sensible raster steps; random bytes are not.
    return rx % 100 == 0


def find_runs(data: bytes, min_len: int = 3) -> List[Tuple[int, int, int]]:
    """Return ``(start_offset, count, stride)`` for every run found."""
    hits = [o for o in range(0, len(data) - 8) if looks_like_record(data, o)]
    hit_set = set(hits)
    runs: List[Tuple[int, int, int]] = []
    consumed = set()

    for start in hits:
        if start in consumed:
            continue
        count = 1
        offset = start
        while offset + RECORD_LEN in hit_set:
            offset += RECORD_LEN
            count += 1
        if count >= min_len:
            runs.append((start, count, RECORD_LEN))
            for i in range(count):
                consumed.add(start + i * RECORD_LEN)
    return runs


def describe(data: bytes, offset: int) -> str:
    rx, tx = struct.unpack_from("<II", data, offset)
    name = data[offset + 0x0E : offset + 0x0E + 24].decode("utf-16-le", "replace")
    name = name.split("\x00", 1)[0]
    return f"{rx / 1e6:>11.6f} / {tx / 1e6:<11.6f} {name!r}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    parser.add_argument("--min-run", type=int, default=3)
    args = parser.parse_args(argv)

    data = pathlib.Path(args.path).read_bytes()
    print(f"file {args.path}: {len(data)} bytes, header {HEADER_LEN}")
    print()

    runs = find_runs(data, args.min_run)
    runs.sort(key=lambda r: -r[1])

    print(f"{'start':>10} {'rel':>10} {'aligned?':>10} {'count':>6}  first record")
    for start, count, _stride in runs[:20]:
        rel = start - HEADER_LEN
        aligned = f"slot {rel // RECORD_LEN}" if rel % RECORD_LEN == 0 else f"+{rel % RECORD_LEN}"
        print(f"{start:>10} {rel:>10} {aligned:>10} {count:>6}  {describe(data, start)}")

    print()
    print("Runs in file order:")
    for start, count, _stride in sorted(runs, key=lambda r: r[0]):
        if count < 4:
            continue
        end = start + count * RECORD_LEN
        print(f"  0x{start:06X}..0x{end:06X}  {count:>4} records")
        print(f"      first {describe(data, start)}")
        print(f"      last  {describe(data, start + (count - 1) * RECORD_LEN)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
