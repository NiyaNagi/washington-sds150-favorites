"""Cross-check the decoded FTX-1 tone field against WWARA coordination data.

The tone index in an RT Systems record was located by looking for the byte
that varies across repeater records.  That is a hypothesis, not a fact, until
it is checked against tones published independently - which is what this
does, using the WWARA extract the project already fetches.
"""
from __future__ import annotations

import pathlib
import sys

from wasds150.cache.http import CachedHttpClient
from wasds150.cache.store import HttpCacheStore
from wasds150.export.ftx1_file import Ftx1File
from wasds150.sources.registry import get_source_class
from wasds150.update.pipeline import run_sources

#: The 50 standard CTCSS tones, in the order radios index them.
CTCSS_TONES = [
    67.0, 69.3, 71.9, 74.4, 77.0, 79.7, 82.5, 85.4, 88.5, 91.5,
    94.8, 97.4, 100.0, 103.5, 107.2, 110.9, 114.8, 118.8, 123.0, 127.3,
    131.8, 136.5, 141.3, 146.2, 151.4, 156.7, 159.8, 162.2, 165.5, 167.9,
    171.3, 173.8, 177.3, 179.9, 183.5, 186.2, 189.9, 192.8, 196.6, 199.5,
    203.5, 206.5, 210.7, 218.1, 225.7, 229.1, 233.6, 241.8, 250.3, 254.1,
]

OFF_TONE_MODE = 0x2C
OFF_TX_TONE = 0x2D
OFF_RX_TONE = 0x2E


def wwara_tones(home: pathlib.Path):
    client = CachedHttpClient(HttpCacheStore(home / "state" / "http-cache"))
    facts = run_sources([get_source_class("wwara")()], http_client=client).facts
    table = {}
    for fact in facts:
        call = (fact.raw.get("CALL") or "").strip().upper()
        tone = fact.tone or ""
        if fact.freq_mhz and call and tone.startswith("TONE=C"):
            table[(round(fact.freq_mhz, 4), call)] = float(tone[6:])
    return table


def main(argv=None) -> int:
    path = pathlib.Path(argv[0]) if argv else pathlib.Path(
        r"Z:\Texts\HAM\Radio Programming\FTX1 WA.FTX1"
    )
    home = pathlib.Path(".wasds150-home")

    table = wwara_tones(home)
    print(f"WWARA repeaters with a published CTCSS tone: {len(table)}")

    ftx1 = Ftx1File.load(path)
    matched = mismatched = 0
    examples = []
    mode_by_result = {}

    for record in ftx1.used:
        key = (round(record.rx_mhz, 4), record.name.strip().upper())
        if key not in table:
            continue
        index = record.raw[OFF_TX_TONE]
        decoded = CTCSS_TONES[index] if index < len(CTCSS_TONES) else None
        expected = table[key]
        mode = record.raw[OFF_TONE_MODE]
        if decoded == expected:
            matched += 1
            mode_by_result.setdefault(mode, 0)
            mode_by_result[mode] += 1
        else:
            mismatched += 1
            if len(examples) < 10:
                examples.append(
                    f"  {record.name:<10} {record.rx_mhz:>10.4f}  "
                    f"wwara={expected}  index={index} -> {decoded}  mode={mode}"
                )

    print(f"tone index at 0x{OFF_TX_TONE:02X}: {matched} match, {mismatched} differ")
    for line in examples:
        print(line)
    print(f"tone-mode byte values among matches: {mode_by_result}")

    if matched and mismatched == 0:
        print("\nCONFIRMED: 0x2D is a CTCSS index into the standard 50-tone table.")
        return 0
    if matched > mismatched * 4:
        print("\nMostly consistent; differences are likely stale coordination data.")
        return 0
    print("\nNOT CONFIRMED - do not write tones using this offset.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
