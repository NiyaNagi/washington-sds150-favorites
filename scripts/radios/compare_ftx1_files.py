"""Compare two ``.FTX1`` files and report what the second one loses.

Written to answer one question honestly: if the catalog-driven plan replaced
the hand-merged file on the radio, what would stop being reachable?

Comparison is by *tuning*, not by name. Two memories are the same channel if
they receive on the same frequency; names and comments differ freely between
a hand-built file and a generated one and that difference is not a loss.
Repeater shift and access tone are reported separately, because a memory
that tunes the same but cannot key the repeater is a partial loss worth
seeing.
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import sys
from typing import Dict, List, Tuple

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

from wasds150.export.ftx1_file import Ftx1File  # noqa: E402


def band_of(mhz: float) -> str:
    for low, high, name in (
        (0.0, 2.0, "LF/MF/160m"),
        (2.0, 30.0, "HF"),
        (30.0, 54.0, "VHF low / 6m"),
        (54.0, 108.0, "FM broadcast"),
        (108.0, 137.0, "Airband"),
        (137.0, 144.0, "VHF gov"),
        (144.0, 148.0, "2m"),
        (148.0, 156.0, "VHF land mobile"),
        (156.0, 163.0, "Marine"),
        (163.0, 174.0, "VHF high"),
        (400.0, 430.0, "UHF gov"),
        (430.0, 450.0, "70cm"),
        (450.0, 470.0, "UHF business / GMRS"),
    ):
        if low <= mhz < high:
            return name
    return "other"


def index(path: pathlib.Path) -> Tuple[Dict[int, list], Ftx1File]:
    ftx1 = Ftx1File.load(path)
    by_rx: Dict[int, list] = collections.defaultdict(list)
    for record in ftx1.memories():
        if not record.empty:
            by_rx[record.rx_hz].append(record)
    return by_rx, ftx1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, help="The file to compare against")
    parser.add_argument("--candidate", required=True, help="The generated file")
    parser.add_argument("--show", type=int, default=25, help="Rows per section")
    args = parser.parse_args(argv)

    ref_path = pathlib.Path(args.reference)
    cand_path = pathlib.Path(args.candidate)
    ref, ref_file = index(ref_path)
    cand, cand_file = index(cand_path)

    ref_count = sum(len(v) for v in ref.values())
    cand_count = sum(len(v) for v in cand.values())
    print(f"reference : {ref_path.name}  {ref_count} memories, {len(ref)} distinct frequencies")
    print(f"candidate : {cand_path.name}  {cand_count} memories, {len(cand)} distinct frequencies")

    missing = sorted(set(ref) - set(cand))
    added = sorted(set(cand) - set(ref))
    shared = sorted(set(ref) & set(cand))

    print(f"\nshared frequencies  : {len(shared)}")
    print(f"only in reference   : {len(missing)}   <-- would be lost")
    print(f"only in candidate   : {len(added)}   <-- newly gained")

    if missing:
        by_band = collections.Counter(band_of(hz / 1e6) for hz in missing)
        print("\nLOST, by band:")
        for name, count in by_band.most_common():
            print(f"  {name:<24} {count:>4}")
        print(f"\nLOST, first {args.show}:")
        for hz in missing[: args.show]:
            record = ref[hz][0]
            print(f"  {hz / 1e6:>10.4f}  {record.name:<13} {record.comment[:40]}")

    if added:
        by_band = collections.Counter(band_of(hz / 1e6) for hz in added)
        print("\nGAINED, by band:")
        for name, count in by_band.most_common():
            print(f"  {name:<24} {count:>4}")

    # Of the shared frequencies, does the candidate keep the repeater shift
    # and tone? A memory that tunes but cannot key is a partial loss.
    #
    # Compare against *every* candidate record on that frequency, not just the
    # first. Two repeaters often share an output on different tones, and a
    # first-record-only check reports a false loss whenever the candidate
    # happens to order them differently from the reference.
    lost_shift = []
    lost_tone = []
    for hz in shared:
        refs = ref[hz]
        cands = cand[hz]
        if any(r.tx_hz != r.rx_hz for r in refs) and not any(
            c.tx_hz != c.rx_hz for c in cands
        ):
            lost_shift.append((hz, refs[0]))
        ref_tones = {r.tx_tone_hz for r in refs if r.tx_tone_hz}
        cand_tones = {c.tx_tone_hz for c in cands if c.tx_tone_hz}
        if ref_tones and not (ref_tones & cand_tones):
            lost_tone.append((hz, refs[0]))

    print(f"\nshared but lost repeater shift : {len(lost_shift)}")
    for hz, record in lost_shift[: args.show]:
        print(f"  {hz / 1e6:>10.4f}  {record.name:<13} shift {(record.tx_hz - record.rx_hz) / 1e6:+.4f}")
    print(f"shared but lost access tone    : {len(lost_tone)}")
    for hz, record in lost_tone[: args.show]:
        print(f"  {hz / 1e6:>10.4f}  {record.name:<13} tone {record.tx_tone_hz}")

    ref_pairs = len([p for p in ref_file.scan_limits() if not p[0].empty])
    cand_pairs = len([p for p in cand_file.scan_limits() if not p[0].empty])
    print(f"\nscan pairs: reference {ref_pairs}, candidate {cand_pairs}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
