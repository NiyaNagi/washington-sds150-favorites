"""Decide what to merge into the FTX-1 from the catalog, and what to leave out.

The radio holds 999 memories and the obvious merge overflows that, so the
question is not *whether* to cut but *what*.  This scores the candidates the
way the radio does: a channel it cannot demodulate is worth nothing at all,
and a data-only channel is worth nothing to a human listener, so those go
before anything that would actually make a sound.
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import sys
from typing import List, Tuple

from wasds150.catalog.baseline import load_baseline
from wasds150.export.ftx1_file import Ftx1File
from wasds150.generate.pipeline import apply_profile
from wasds150.models.catalog import Catalog
from wasds150.models.profile import Profile
from wasds150.plan.resolve import iter_catalog_channels
from wasds150.radios.registry import FTX1

DEFAULT_SOURCE = r"Z:\Texts\HAM\Radio Programming\FTX1 WA.FTX1"

#: Lists the operator chose to leave out: a different trip, or seasonal.
DROP_LISTS = frozenset({"FL73", "UL00", "UL01", "UL02", "UL03"})

#: Digital modes worth programming only if you decode them with software.
DROP_LABELS = ("WSPR", "FT4", "SSTV")

#: Channels that carry no voice. A receiver will show a signal and play
#: noise, which is worse than an empty slot.
DATA_ONLY = (
    "AIS", "DSC", "PAGING", "POCSAG", "TELEMETRY", "SCADA", "MDC",
    "PACKET", "APRS",
)


def candidates(source: pathlib.Path) -> Tuple[int, List[Tuple[object, object]]]:
    ftx1 = Ftx1File.load(source)
    existing = [r for r in ftx1.records[:999] if not r.empty]
    have = {(round(r.rx_mhz, 4), r.name.strip().upper()) for r in existing}
    have_freq = {round(r.rx_mhz, 4) for r in existing}

    catalog = load_baseline()
    generated = apply_profile(
        catalog, Profile(based_on_catalog_hash=catalog.content_hash())
    )
    effective = Catalog(favorites=generated.enabled_favorites)

    rows: List[Tuple[object, object]] = []
    seen = set()
    for favorite, _system, _dept, channel in iter_catalog_channels(effective):
        if not channel.freq_mhz or not FTX1.can_receive(channel.freq_mhz):
            continue
        if favorite.favorite_key == "FTX01" or favorite.favorite_key in DROP_LISTS:
            continue
        key = (round(channel.freq_mhz, 4), channel.label.strip().upper())
        if key in have or key in seen:
            continue
        # The band plan intentionally repeats frequencies the file already
        # has, under names that say what they are for.
        if round(channel.freq_mhz, 4) in have_freq and favorite.favorite_key != "HAM01":
            continue
        if any(tag in channel.label.upper() for tag in DROP_LABELS):
            continue
        seen.add(key)
        rows.append((favorite, channel))
    return len(existing), rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    args = parser.parse_args(argv)

    existing, rows = candidates(pathlib.Path(args.source))
    print(f"already in the file : {existing}")
    print(f"candidates to add   : {len(rows)}")
    print(f"total               : {existing + len(rows)} of 999")
    print()

    undemodulable = [(f, c) for f, c in rows if not FTX1.supports_mode(c.mode)]
    print(f"A) modes the FTX-1 cannot demodulate: {len(undemodulable)}")
    for mode, count in collections.Counter(
        (c.mode or "unset") for _f, c in undemodulable
    ).most_common():
        print(f"     {mode:<8} {count}")
    for _f, channel in undemodulable[:8]:
        print(f"     {channel.freq_mhz:>10.4f}  {channel.mode:<6} {channel.label[:36]}")
    print()

    undemod_ids = {id(c) for _f, c in undemodulable}
    data_only = [
        (f, c)
        for f, c in rows
        if id(c) not in undemod_ids
        and any(tag in f"{c.label} {c.notes}".upper() for tag in DATA_ONLY)
    ]
    print(f"B) data only, no voice: {len(data_only)}")
    for _f, channel in data_only[:10]:
        print(f"     {channel.freq_mhz:>10.4f}  {channel.label[:44]}")
    print()

    removable = len(undemodulable) + len(data_only)
    total = existing + len(rows) - removable
    print(f"removable without touching eastern Washington: {removable}")
    print(f"resulting total: {total} of 999", end="  ")
    print("FITS" if total <= 999 else f"still over by {total - 999}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
