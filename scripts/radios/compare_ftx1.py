"""Compare an RT Systems FTX-1 file against the wasds150 catalog.

Answers two questions, in both directions:

* what is in the FTX-1 file that the catalog does not know about, and
* what is in the catalog that the file does not contain.

Frequencies are compared to four decimal places (100 Hz), which is finer than
any channel spacing in use and coarse enough to absorb rounding.
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import sys

from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.export.ftx1_file import Ftx1File
from wasds150.generate.pipeline import apply_profile
from wasds150.models.catalog import Catalog
from wasds150.plan.resolve import iter_catalog_channels
from wasds150.radios.registry import FTX1

DEFAULT_FTX1 = r"Z:\Texts\HAM\Radio Programming\FTX1 WA.FTX1"


def band_of(mhz: float) -> str:
    for low, high, name in (
        (0.1, 0.6, "LF/MW"),
        (1.8, 2.0, "160m"),
        (3.5, 4.0, "80m"),
        (5.3, 5.5, "60m"),
        (7.0, 7.3, "40m"),
        (10.1, 10.15, "30m"),
        (14.0, 14.35, "20m"),
        (18.0, 18.2, "17m"),
        (21.0, 21.45, "15m"),
        (24.8, 25.0, "12m"),
        (26.0, 27.5, "CB"),
        (28.0, 29.7, "10m"),
        (50.0, 54.0, "6m"),
        (76.0, 108.0, "FM bcast"),
        (108.0, 137.0, "airband"),
        (137.0, 144.0, "VHF low"),
        (144.0, 148.0, "2m"),
        (148.0, 156.0, "VHF mid"),
        (156.0, 163.0, "marine/WX"),
        (163.0, 174.0, "VHF high"),
        (216.0, 225.0, "1.25m"),
        (400.0, 420.0, "UHF fed"),
        (420.0, 450.0, "70cm"),
        (450.0, 470.0, "UHF business"),
    ):
        if low <= mhz <= high:
            return name
    return "other"


def load_catalog(home: pathlib.Path) -> Catalog:
    ctx = build_context(AppConfig(home=home))
    generated = apply_profile(ctx.catalog, ctx.load_profile())
    return Catalog(favorites=generated.enabled_favorites)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ftx1", default=DEFAULT_FTX1)
    parser.add_argument("--home", default=".wasds150-home")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)

    ftx1 = Ftx1File.load(pathlib.Path(args.ftx1))
    memories = [r for r in ftx1.records[:999] if not r.empty]

    catalog = load_catalog(pathlib.Path(args.home))
    mine = collections.defaultdict(list)
    for favorite, _system, department, channel in iter_catalog_channels(catalog):
        if channel.freq_mhz:
            mine[round(channel.freq_mhz, 4)].append(
                (favorite.favorite_key, department.label, channel.label)
            )

    print(f"FTX-1 file:    {len(memories)} memory channels of 999")
    print(f"wasds150:      {len(mine)} unique frequencies")
    print()

    gap = [r for r in memories if round(r.rx_mhz, 4) not in mine]
    print(f"=== In the FTX-1 file but NOT in the catalog: {len(gap)} ===")
    for name, count in collections.Counter(band_of(r.rx_mhz) for r in gap).most_common():
        print(f"  {name:<14} {count}")
    print()
    for record in gap[: args.limit]:
        shift = record.tx_mhz - record.rx_mhz
        print(
            f"  {record.name:<12} {record.rx_mhz:>10.4f} {shift:+8.4f}  "
            f"{record.comment[:40]}"
        )
    if len(gap) > args.limit:
        print(f"  ... and {len(gap) - args.limit} more")
    print()

    have = {round(r.rx_mhz, 4) for r in memories}
    reverse = sorted(set(mine) - have)
    usable = [m for m in reverse if FTX1.can_receive(m)]
    print(f"=== In the catalog but NOT in the FTX-1 file: {len(reverse)} ===")
    print(f"    of which the FTX-1 can receive: {len(usable)}")
    for name, count in collections.Counter(band_of(m) for m in usable).most_common():
        print(f"  {name:<14} {count}")
    print()
    sources = collections.Counter(mine[m][0][0] for m in usable)
    print("  by catalog list:")
    for key, count in sources.most_common(15):
        print(f"    {key:<10} {count}")
    print()
    print(f"  capacity if all merged: {len(memories) + len(usable)} of 999")
    return 0


if __name__ == "__main__":
    sys.exit(main())
