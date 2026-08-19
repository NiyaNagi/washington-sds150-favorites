"""Read an RT Systems ``.FTX1`` memory file.

RT Systems does not document its file format, and the layout differs per
radio model.  This module derives the structure from a file saved by the
installed FTX-1 programmer rather than guessing at it, and prints what it
finds so the parsing can be checked by eye against the programmer's own
display.

Read-only. Nothing here writes an RT Systems file.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

PRINTABLE = re.compile(rb"[ -~]{4,}")


def hexdump(data: bytes, start: int, length: int) -> None:
    for offset in range(start, min(start + length, len(data)), 16):
        row = data[offset : offset + 16]
        hex_part = " ".join(f"{b:02X}" for b in row)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        print(f"{offset:06X}  {hex_part:<47}  {ascii_part}")


def find_strings(data: bytes, min_len: int = 4):
    """Yield (offset, text) for ASCII and UTF-16LE runs."""
    for match in re.finditer(rb"[ -~]{%d,}" % min_len, data):
        yield match.start(), match.group().decode("ascii", "replace"), "ascii"
    for match in re.finditer(rb"(?:[ -~]\x00){%d,}" % min_len, data):
        text = match.group().decode("utf-16-le", "replace")
        yield match.start(), text, "utf16"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    parser.add_argument("--head", type=int, default=512, help="Header bytes to dump")
    parser.add_argument("--strings", action="store_true")
    parser.add_argument("--min-len", type=int, default=4)
    parser.add_argument("--grep", help="Only show strings matching this regex")
    parser.add_argument("--at", type=lambda v: int(v, 0), help="Hexdump at this offset")
    parser.add_argument("--length", type=int, default=512)
    args = parser.parse_args(argv)

    data = Path(args.path).read_bytes()
    print(f"file:  {args.path}")
    print(f"size:  {len(data)} bytes")
    print(f"magic: {data[:16]!r}")
    print()

    if args.at is not None:
        hexdump(data, args.at, args.length)
        return 0

    if args.strings:
        pattern = re.compile(args.grep, re.IGNORECASE) if args.grep else None
        seen = 0
        for offset, text, kind in sorted(find_strings(data, args.min_len)):
            if pattern and not pattern.search(text):
                continue
            print(f"{offset:06X} [{kind}] {text}")
            seen += 1
            if seen > 4000:
                print("... truncated")
                break
        return 0

    print("--- header ---")
    hexdump(data, 0, args.head)

    print()
    print("--- byte histogram of the top values ---")
    for value, count in Counter(data).most_common(8):
        print(f"  0x{value:02X}  {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
