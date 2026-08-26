"""Restore non-memory settings after MCP-D75 imports/saves a repeater list."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from wasds150.export.thd75_target import restore_unowned_regions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup", required=True, type=Path, help="Exact pre-change radio .d75")
    parser.add_argument("--mcp-saved", required=True, type=Path, help="File saved after MCP repeater import")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    merged, restored = restore_unowned_regions(
        args.mcp_saved.read_bytes(), args.backup.read_bytes()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(merged)
    digest = hashlib.sha256(merged).hexdigest().upper()
    print(f"restored {restored} unrelated MCP-normalized bytes")
    print(f"wrote {len(merged):,} bytes to {args.output}")
    print(f"SHA-256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
