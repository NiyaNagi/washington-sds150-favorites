"""Compare a generated AT-D890UV CPS bundle with a read-back Export All.

Usage::

    python scripts/radios/diff_atd890_export.py \
        --bundle wasds150-output/radios/at-d890uv-fleet \
        --readback radio-backups/at-d890uv/2026-09-12-readback

Exits 0 when the read-back matches (member order aside), 1 when it does not,
2 on bad arguments. Always prints the SHA-256 of the bundle and of each file
in it: record those in docs/at-d890uv-programming.md when a round trip is
clean, alongside flipping the profile to verified=True.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from wasds150.export.atd890_diff import compare_bundle
from wasds150.util.hashing import sha256_of_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bundle", required=True, type=Path, help="Generated bundle folder")
    parser.add_argument("--readback", required=True, type=Path, help="CPS Export All folder after reading the radio")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--ignore", action="append", default=[], metavar="FILE:COLUMN",
        help="Also ignore this column, e.g. Channel.CSV:Transmit Power (repeatable)",
    )
    args = parser.parse_args(argv)

    ignores = []
    for item in args.ignore:
        file_name, sep, column = item.partition(":")
        if not sep or not file_name or not column:
            print(f"error: --ignore expects FILE:COLUMN, got {item!r}", file=sys.stderr)
            return 2
        ignores.append((file_name, column))
    for folder in (args.bundle, args.readback):
        if not folder.is_dir():
            print(f"error: {folder} is not a folder", file=sys.stderr)
            return 2

    diff = compare_bundle(args.bundle, args.readback, ignore=ignores)
    hashes = {"bundle": sha256_of_path(args.bundle)}
    hashes.update({p.name: sha256_of_path(p) for p in sorted(args.bundle.iterdir()) if p.is_file()})
    if args.json:
        print(json.dumps({**diff.to_dict(), "sha256": hashes}, indent=2))
    else:
        print(diff.summary())
        print()
        for name, digest in hashes.items():
            print(f"{digest}  {name}")
    return 0 if diff.clean else 1


if __name__ == "__main__":
    sys.exit(main())
