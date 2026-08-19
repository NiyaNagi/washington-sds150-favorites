"""Summarize what is actually inside a .FTX1 file, grouped by band/service."""
from __future__ import annotations

import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

from wasds150.export.ftx1_file import Ftx1File  # noqa: E402


def band_of(mhz: float) -> str:
    for low, high, name in (
        (0.0, 0.5, "LF/MF"),
        (0.5, 1.8, "AM broadcast"),
        (1.8, 2.0, "160m"),
        (2.0, 3.5, "SW 120/90m"),
        (3.5, 4.0, "80m"),
        (4.0, 7.0, "SW 75/60m"),
        (7.0, 7.3, "40m"),
        (7.3, 10.1, "SW 41/31m"),
        (10.1, 10.15, "30m"),
        (10.15, 14.0, "SW 25m"),
        (14.0, 14.35, "20m"),
        (14.35, 18.068, "SW 19/16m"),
        (18.068, 18.168, "17m"),
        (18.168, 21.0, "SW 15m"),
        (21.0, 21.45, "15m"),
        (21.45, 24.89, "SW 13m"),
        (24.89, 24.99, "12m"),
        (24.99, 28.0, "SW 11m"),
        (28.0, 29.7, "10m"),
        (29.7, 50.0, "VHF low"),
        (50.0, 54.0, "6m"),
        (54.0, 108.0, "FM bcast/air"),
        (108.0, 137.0, "Airband"),
        (137.0, 144.0, "VHF gov"),
        (144.0, 148.0, "2m"),
        (148.0, 156.0, "VHF land mobile"),
        (156.0, 163.0, "Marine"),
        (163.0, 174.0, "VHF high"),
        (400.0, 420.0, "UHF gov"),
        (420.0, 450.0, "70cm"),
        (450.0, 470.0, "UHF business/GMRS"),
    ):
        if low <= mhz < high:
            return name
    return "other"


def main() -> int:
    path = pathlib.Path(sys.argv[1])
    ftx1 = Ftx1File.load(path)
    memories = [r for r in ftx1.memories() if not r.empty]

    print(f"file      : {path}")
    print(f"memories  : {len(memories)} of 999 populated")

    bands = collections.Counter(band_of(r.rx_mhz) for r in memories)
    print("\nby band:")
    for name, count in sorted(bands.items(), key=lambda kv: -kv[1]):
        print(f"  {name:22} {count:4}")

    dup = sum(1 for r in memories if r.tx_hz and r.tx_hz != r.rx_hz)
    toned = sum(1 for r in memories if r.tx_tone_hz)
    print(f"\nwith repeater shift : {dup}")
    print(f"with CTCSS tone     : {toned}")

    print("\nfirst 15 memories:")
    for r in memories[:15]:
        print(f"  {r.index + 1:4} {r.name:<13} {r.rx_mhz:>10.4f}  {r.describe()[:60]}")

    pairs = ftx1.scan_limits()
    used = [(lo, hi) for lo, hi in pairs if not lo.empty]
    print(f"\nscan pairs populated: {len(used)} of {len(pairs)}")
    for lo, hi in used[:10]:
        print(f"  {lo.name:<13} {lo.rx_mhz:>10.4f} - {hi.rx_mhz:>10.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
