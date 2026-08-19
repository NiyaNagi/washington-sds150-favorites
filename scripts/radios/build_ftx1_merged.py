"""Write a merged ``.FTX1`` file: the operator's own channels plus the catalog.

The operator's file already holds curated work - statewide amateur repeaters,
the full marine channel list, business itinerant channels - and carries radio
settings this project does not model.  So the merge starts from that file and
adds to it, rather than generating one from scratch.  Every record is written
by patching a real record of the same shape, so the bytes this project does
not understand keep whatever the programmer put there.

Selection is deliberately conservative about what counts as a duplicate. Two
memories are the same only if they tune identically - same receive frequency,
same transmit frequency, same access tone. Two repeaters sharing an output on
different tones are different machines and both are kept.
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import sys
from typing import Dict, List, Optional, Tuple

from wasds150.export.ftx1_file import (
    CTCSS_TONES,
    PMS_FIRST,
    PMS_PAIRS,
    Ftx1File,
    Ftx1Record,
)
from wasds150.plan.naming import NameAllocator
from wasds150.radios.bandplan import BANDS_BY_ID
from wasds150.radios.registry import FTX1
from wasds150.radios.scan_ranges import ranges_by_priority
from wasds150.radios.tones import parse_tone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from plan_ftx1_merge import candidates  # noqa: E402

DEFAULT_SOURCE = r"Z:\Texts\HAM\Radio Programming\FTX1 WA.FTX1"
DEFAULT_OUT = r"Z:\Texts\HAM\Radio Programming\FTX1 WA MERGED.FTX1"

#: The FTX-1 shows twelve characters of a memory tag.
NAME_LEN = 12
MEMORY_CAPACITY = 999


def tuning_key(rx_hz: int, tx_hz: int, tone: str) -> Tuple[int, int, str]:
    return (rx_hz, tx_hz, tone)


def tone_hz(channel) -> Optional[float]:
    """The access tone to program, if it is a standard analog tone."""
    spec = parse_tone(channel.tx_tone or channel.tone)
    if spec.kind != "ctcss" or spec.ctcss_hz is None:
        return None
    return spec.ctcss_hz if any(
        abs(spec.ctcss_hz - t) < 0.05 for t in CTCSS_TONES
    ) else None


def pick_templates(ftx1: Ftx1File) -> Dict[str, Ftx1Record]:
    """One real record of each duplex shape, to patch new channels from.

    Synthesising 295 bytes would mean guessing at every field this project has
    not decoded. Copying a record the programmer itself wrote means only the
    fields being changed are ever in question.
    """
    templates: Dict[str, Ftx1Record] = {}
    for record in ftx1.memories():
        if record.empty:
            continue
        if record.tx_hz == record.rx_hz:
            templates.setdefault("simplex", record)
        elif record.tx_hz > record.rx_hz:
            templates.setdefault("plus", record)
        else:
            templates.setdefault("minus", record)
        if len(templates) == 3:
            break
    if "simplex" not in templates:
        raise SystemExit("source file has no simplex record to use as a template")
    templates.setdefault("plus", templates["simplex"])
    templates.setdefault("minus", templates["simplex"])
    return templates


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    source = pathlib.Path(args.source)
    original = source.read_bytes()
    ftx1 = Ftx1File.load(source)
    if not ftx1.round_trips(original):
        raise SystemExit("parser does not round-trip the source; refusing to write")

    memories = ftx1.memories()
    existing = [r for r in memories if not r.empty]
    print(f"source: {source}")
    print(f"  existing memories: {len(existing)}")

    # What the radio already tunes, so the merge never adds a second copy.
    seen = {
        tuning_key(r.rx_hz, r.tx_hz, f"{r.tx_tone_hz or ''}") for r in existing
    }

    _count, rows = candidates(source)
    print(f"  catalog candidates: {len(rows)}")

    templates = pick_templates(ftx1)
    allocator = NameAllocator(NAME_LEN)
    for record in existing:
        allocator._taken.add(record.name)  # keep new names distinct from old

    additions: List[Tuple[object, object, int, int, Optional[float]]] = []
    dropped = collections.Counter()

    for favorite, channel in rows:
        if not FTX1.supports_mode(channel.mode):
            dropped["mode the radio cannot demodulate"] += 1
            continue
        rx = int(round(channel.freq_mhz * 1_000_000))
        tx = (
            int(round(channel.tx_freq_mhz * 1_000_000))
            if channel.tx_freq_mhz
            else rx
        )
        tone = tone_hz(channel)
        key = tuning_key(rx, tx, f"{tone or ''}")
        if key in seen:
            dropped["already tuned identically"] += 1
            continue
        seen.add(key)
        additions.append((favorite, channel, rx, tx, tone))

    free = MEMORY_CAPACITY - len(existing)
    print(f"  additions after dedup: {len(additions)}  (free slots {free})")
    for reason, count in dropped.most_common():
        print(f"    dropped, {reason}: {count}")
    if len(additions) > free:
        raise SystemExit(
            f"{len(additions)} additions exceed {free} free memories; trim first"
        )

    # Fill the first free memory slots, in catalog order.
    slot = next(i for i, r in enumerate(memories) if r.empty)
    written = 0
    for favorite, channel, rx, tx, tone in additions:
        while slot < MEMORY_CAPACITY and not ftx1.records[slot].empty:
            slot += 1
        if slot >= MEMORY_CAPACITY:
            raise SystemExit("ran out of memory slots")
        shape = "simplex" if tx == rx else ("plus" if tx > rx else "minus")
        name = allocator.allocate(channel.label)
        note = f"{favorite.favorite_key} {channel.label}"[:32]
        ftx1.records[slot] = templates[shape].patched(
            rx_hz=rx, tx_hz=tx, name=name, comment=note, tone_hz=tone, in_use=True
        )
        slot += 1
        written += 1

    # Programmable scan ranges.
    scan_ranges = ranges_by_priority(PMS_PAIRS)
    for pair, scan_range in enumerate(scan_ranges):
        band = BANDS_BY_ID.get(scan_range.band_id)
        note = scan_range.note[:32]
        ftx1.set_scan_limit(
            pair,
            scan_range.low_mhz,
            scan_range.high_mhz,
            label=scan_range.label[:NAME_LEN],
            note=note,
        )
    print(f"  scan ranges programmed: {len(scan_ranges)} of {PMS_PAIRS} pairs")

    total = len([r for r in ftx1.memories() if not r.empty])
    print()
    print(f"result: {total} memories of {MEMORY_CAPACITY}, {written} added")

    if args.dry_run:
        print("\nDRY RUN - nothing written.")
        return 0

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ftx1.save(out)

    written_bytes = out.read_bytes()
    if len(written_bytes) != len(original):
        raise SystemExit("output size changed; the record model is wrong")

    # Read it back and confirm the radio-visible content is what we intended.
    check = Ftx1File.load(out)
    if len([r for r in check.memories() if not r.empty]) != total:
        raise SystemExit("memory count did not survive the round trip")
    limits = [pair for pair in check.scan_limits() if not pair[0].empty]
    if len(limits) != len(scan_ranges):
        raise SystemExit("scan ranges did not survive the round trip")

    print(f"\nwrote {out}  ({len(written_bytes)} bytes, unchanged size)")
    print("verified: memory count and scan ranges read back correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
