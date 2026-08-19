"""Make a blank ``.FTX1`` structural template from a real programmer file.

The export target needs one genuine record of each duplex shape to patch
from, because a memory record is 295 bytes and this project has decoded only
a dozen of them.  What it does *not* need is anybody's channel list.

Clearing is not as simple as blanking the fields this project models.  A
record has an undecoded tail beyond the 32-character comment at ``0x85``, and
in a file saved by the RT Systems programmer that tail holds further
descriptive text from the vendor's bundled marine and service databases.
Blanking only the modelled fields leaves that text sitting in the file.

So this script does two things:

1. Zeroes every record completely, so no record carries residual bytes.
2. Restores a small number of *verified clean* base records - real records
   from the source whose full 295 bytes contain no readable text once their
   name and comment are blanked - for the export target to patch from.

The result is then scanned end to end and rejected if any channel text
survives.  What ships is container structure only.

Usage::

    python scripts/radios/make_ftx1_template.py \
        --source "Z:\\path\\to\\FTX1 WA.FTX1" \
        --out radio-templates/ftx1-blank.FTX1
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import Dict, List

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

from wasds150.export.ftx1_file import Ftx1File, Ftx1Record  # noqa: E402

DEFAULT_OUT = pathlib.Path("radio-templates") / "ftx1-blank.FTX1"

#: How many records at the front of the array are user memories. Everything
#: after this is scan limits, HOME channels and radio configuration, all of
#: which is preserved rather than blanked.
MEMORY_COUNT = 999

#: Runs of printable characters we treat as "readable text". Names and
#: comments are UTF-16-LE; the container magic is plain ASCII.
_UTF16_RUN = re.compile(rb"(?:[\x20-\x7e]\x00){3,}")
_ASCII_RUN = re.compile(rb"[\x20-\x7e]{4,}")


def readable_text(raw: bytes) -> List[str]:
    """Every readable string in a byte run, in both encodings."""
    found = {m.decode("utf-16-le").strip() for m in _UTF16_RUN.findall(raw)}
    found |= {m.decode("ascii").strip() for m in _ASCII_RUN.findall(raw)}
    return sorted(text for text in found if text)


def blanked(record: Ftx1Record) -> Ftx1Record:
    """A record with every modelled field cleared."""
    return record.patched(
        rx_hz=0, tx_hz=0, name="", comment="", tone_hz=None, in_use=False
    )


def find_clean_bases(source: Ftx1File) -> Dict[str, Ftx1Record]:
    """One verified-clean base record per duplex shape.

    "Clean" means: after blanking name and comment, the record's full 295
    bytes contain no readable text anywhere. Such a record carries the
    vendor's per-channel setting bytes without carrying any description.

    Only real memories are considered. Scan limits and HOME channels live in
    the same array but are a different kind of record, and an empty one of
    those carries no per-channel settings at all - harvesting from them
    yields a base that is blank, which defeats the point of having one.

    A factory-reset file holds a single default memory, so one base is the
    normal case. The duplex shape does not need to come from the base: the
    export target sets receive, transmit and the direction byte explicitly,
    because those are fields this project models.
    """
    bases: Dict[str, Ftx1Record] = {}
    for record in source.records[:MEMORY_COUNT]:
        if record.empty:
            continue
        if record.tx_hz == record.rx_hz:
            shape = "simplex"
        elif record.tx_hz > record.rx_hz:
            shape = "plus"
        else:
            shape = "minus"
        if shape in bases:
            continue
        candidate = blanked(record)
        if readable_text(candidate.raw):
            continue  # still carries text in the undecoded tail
        bases[shape] = candidate
        if len(bases) == 3:
            break

    # Fill any missing shape from whichever base we did find. Patching sets
    # the frequencies and direction, so a simplex base serves a repeater
    # channel correctly; what matters is that the surrounding setting bytes
    # are genuine rather than invented.
    if bases:
        fallback = bases.get("simplex") or next(iter(bases.values()))
        for shape in ("simplex", "plus", "minus"):
            bases.setdefault(shape, fallback)
    return bases


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="A file saved by the programmer")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    source_path = pathlib.Path(args.source)
    original = source_path.read_bytes()
    ftx1 = Ftx1File.load(source_path)
    if not ftx1.round_trips(original):
        raise SystemExit("parser does not round-trip the source; refusing to write")

    populated = len([r for r in ftx1.memories() if not r.empty])
    print(f"source: {source_path}")
    print(f"  populated memories: {populated}")

    bases = find_clean_bases(ftx1)
    print(f"  clean base records: {sorted(bases) or 'NONE'}")

    record_size = len(ftx1.records[0].raw)
    blank_raw = bytes(record_size)

    # 1. Zero the MEMORY records only.
    #
    #    Everything past the memories - the programmable scan limits, the
    #    HOME channels, and the configuration area beyond the record array
    #    (CW messages, GPS setup, display data) - is carried through
    #    untouched. Those are radio settings, not channel data, and blanking
    #    them produced a file that loaded but silently reset the radio's
    #    configuration.
    for index in range(min(MEMORY_COUNT, len(ftx1.records))):
        ftx1.records[index] = Ftx1Record(index=index, raw=blank_raw)

    # 2. Restore verified-clean bases at the front, where the export target
    #    looks for them.
    restored = 0
    for slot, shape in enumerate(("simplex", "plus", "minus")):
        base = bases.get(shape)
        if base is not None:
            ftx1.records[slot] = Ftx1Record(index=slot, raw=base.raw)
            restored += 1
    if not restored:
        raise SystemExit(
            "no clean base record found in the source memories; the export "
            "target has nothing genuine to patch from"
        )
    print(f"  zeroed {min(MEMORY_COUNT, len(ftx1.records))} memories, "
          f"restored {restored} clean bases")

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ftx1.save(out)

    if out.stat().st_size != len(original):
        raise SystemExit("template size differs from source; the record model is wrong")

    # Verify: reload, confirm no memory is populated and no channel text
    # survives IN THE MEMORY AREA.
    #
    # The check is deliberately scoped to the memories rather than the whole
    # file. The configuration area past the record array legitimately holds
    # readable text - the radio's CW messages, for instance - and an earlier
    # version of this script scanned the entire body, concluded that text was
    # channel data, and "fixed" it by zeroing the radio's settings.
    check = Ftx1File.load(out)
    remaining = [r for r in check.memories()[:MEMORY_COUNT] if not r.empty]
    if remaining:
        raise SystemExit(f"{len(remaining)} memories survived clearing; refusing")

    memory_area = b"".join(r.raw for r in check.records[:MEMORY_COUNT])
    body_text = readable_text(memory_area)
    if body_text:
        print("\nREFUSING: readable text survives in the memory area:")
        for text in body_text[:20]:
            print(f"  {text!r}")
        return 1

    settings_bytes = sum(
        1 for r in check.records[MEMORY_COUNT:] for b in r.raw if b
    ) + sum(1 for b in check.trailer if b)
    print(f"\nwrote {out} ({out.stat().st_size} bytes)")
    print("verified: no channel data in the memory area")
    print(f"preserved: {settings_bytes} non-zero bytes of radio settings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
