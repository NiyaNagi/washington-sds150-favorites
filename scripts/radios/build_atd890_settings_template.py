"""Build the AT-D890UV Optional Settings / hot key template from two Export Alls.

Usage::

    python scripts/radios/build_atd890_settings_template.py \
        --fresh radio-backups/at-d890uv/fixtures/fresh \
        --configured radio-backups/at-d890uv/fixtures/configured

``fresh`` is Export All of File > New; ``configured`` is Export All after the
settings table in docs/at-d890uv-programming.md was applied. Writes
src/wasds150/data/atd890_settings_template.json (Radio ID and call-sign cells
blanked), which every later bundle export replays.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from wasds150.export.atd890_settings_template import TEMPLATE_PATH, diff_export_all


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fresh", required=True, type=Path)
    parser.add_argument("--configured", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=TEMPLATE_PATH)
    args = parser.parse_args(argv)
    try:
        template = diff_export_all(args.fresh, args.configured)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    template.save(args.out)
    for entry in template.files:
        print(f"{entry.name}: {len(entry.changed)} changed cell(s), {len(entry.identity)} identity cell(s) blanked")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
