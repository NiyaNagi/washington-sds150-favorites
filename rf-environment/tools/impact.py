"""Count each radio's programmed receive channels that sit on a measured RFI zone.

    .venv\\Scripts\\python.exe rf-environment\\tools\\programmed.py   # refresh programmed.json first
    .venv\\Scripts\\python.exe rf-environment\\tools\\impact.py

Zones come from the 2026-09-23 survey. A channel counts as hit when it is
within the zone (or, for a birdie, within 7.5 kHz of the carrier: inside a
12.5 kHz or 25 kHz FM channel filter).
"""
import json
from paths import PROGRAMMED

ZONES = [
    # id, lo MHz, hi MHz, kind, where it is heard
    ("birdie 147.456 (12.288 MHz x12)", 147.4485, 147.4635, "birdie", "desk"),
    ("birdie 442.368 (12.288 MHz x36)", 442.3605, 442.3755, "birdie", "desk"),
    ("birdie 159.744 (12.288 MHz x13)", 159.7365, 159.7515, "birdie", "desk"),
    ("birdie 49.152 (12.288 MHz x4)", 49.1445, 49.1595, "birdie", "desk"),
    ("6m SMPS comb (68.7 kHz lines)", 50.0, 54.0, "comb", "desk"),
    ("airband hash 119.9-120.4", 119.85, 120.45, "hash", "desk"),
    ("airband hash 132.0-132.8", 131.95, 132.8, "hash", "desk"),
    ("2m floor +21 dB", 144.0, 148.0, "floor", "desk"),
    ("VHF-high floor +18 dB (150-174)", 150.0, 174.0, "floor", "desk"),
    ("HF 60m hash (32.7 kHz SMPS)", 5.33, 5.41, "hf", "outdoor antenna"),
    ("HF 30m hash (32.7 kHz SMPS)", 10.1, 10.15, "hf", "outdoor antenna"),
    ("HF 17m 16-17 MHz hump skirt", 18.068, 18.168, "hf", "outdoor antenna"),
]


def main():
    prog = json.load(open(PROGRAMMED))
    out = {}
    for zid, lo, hi, kind, where in ZONES:
        row = {}
        for radio, fs in prog.items():
            hits = [f for f in fs if lo <= f <= hi]
            if hits:
                row[radio] = hits
        out[zid] = dict(kind=kind, where=where, hits=row)
        summary = ", ".join(f"{r} {len(h)}" for r, h in row.items()) or "none"
        print(f"{zid:38s} [{where}] {summary}")
    return out


if __name__ == "__main__":
    main()
