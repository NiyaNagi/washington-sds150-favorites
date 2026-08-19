"""Write a probe ``.FTX1`` file to confirm where PMS pairs live.

The Advance Manual says the 50 Programmable Memory Scan pairs sit "after the
last memory channel (M-999)", which puts them at record slots 999 to 1098.
The HOME channels found at slots 1189-1194 hold exactly the documented
defaults, which supports the model but does not prove the PMS location.

This writes one recognisable marker into each candidate region so the answer
can be read straight off the programmer's screen.  Nothing is guessed at in
the real merge until this comes back confirmed.

The source file is never modified; output goes to a new path.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from wasds150.export.ftx1_file import Ftx1File

DEFAULT_SOURCE = r"Z:\Texts\HAM\Radio Programming\FTX1 WA.FTX1"

#: Deliberately absurd frequencies, so a marker cannot be confused with real
#: data and is obvious wherever it surfaces in the programmer.
MARKERS = (
    (553, 28_123_400, "ZZMEM553", "probe: first free regular memory"),
    (999, 14_000_000, "ZZPMS01L", "probe: expect P-01L, 20m lower"),
    (1000, 14_350_000, "ZZPMS01U", "probe: expect P-01U, 20m upper"),
    (1002, 7_000_000, "ZZPMS02L", "probe: expect P-02L, 40m lower"),
    (1003, 7_300_000, "ZZPMS02U", "probe: expect P-02U, 40m upper"),
    (1099, 21_123_400, "ZZR1099", "probe: region after 50 PMS pairs"),
    (1150, 24_123_400, "ZZR1150", "probe: region before HOME"),
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--out", default="wasds150-output/radios/FTX1-PMS-PROBE.FTX1")
    args = parser.parse_args(argv)

    source = pathlib.Path(args.source)
    original = source.read_bytes()
    ftx1 = Ftx1File.load(source)
    if not ftx1.round_trips(original):
        raise SystemExit("parser does not round-trip this file; refusing to write")

    print(f"source: {source}  ({len(ftx1.records)} record slots)")
    for index, hz, name, comment in MARKERS:
        record = ftx1.records[index]
        if not record.empty:
            raise SystemExit(
                f"slot {index} is not empty ({record.name} {record.rx_mhz:.4f}); "
                "refusing to overwrite real data"
            )
        ftx1.records[index] = record.patched(
            rx_hz=hz, tx_hz=hz, name=name, comment=comment
        )
        print(f"  slot {index:5} <- {name:<9} {hz / 1e6:>10.4f} MHz")

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ftx1.save(out)

    written = out.read_bytes()
    if len(written) != len(original):
        raise SystemExit("output size changed; the record model is wrong")
    reread = Ftx1File.load(out)
    for index, hz, name, _comment in MARKERS:
        if reread.records[index].rx_hz != hz or reread.records[index].name != name:
            raise SystemExit(f"slot {index} did not read back correctly")

    print(f"\nwrote {out}  ({len(written)} bytes, unchanged size)")
    print("\nOpen this in RT Systems YPS-FTX1 and report where each marker appears:")
    print("  ZZMEM553  -> expected on the Memories tab")
    print("  ZZPMS01L/U, ZZPMS02L/U -> expected on the PMS tab as P-01L/U, P-02L/U")
    print("  ZZR1099, ZZR1150 -> unknown region; note which tab shows them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
