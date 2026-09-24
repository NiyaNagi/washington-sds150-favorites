"""Print a coarse text view of a sweep segment: per block min/median/max over passes.
python fine.py rf/x.json lo_mhz hi_mhz block_khz [baseline.json]
"""
import json, sys, statistics

r = json.load(open(sys.argv[1]))
lo, hi, blk = float(sys.argv[2]) * 1e6, float(sys.argv[3]) * 1e6, float(sys.argv[4]) * 1e3
base = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else None
F, P = r["freqs"], r["passes"]
f = lo
while f < hi:
    idx = [i for i, x in enumerate(F) if f <= x < f + blk]
    if idx:
        mx = max(max(p[i] for p in P) for i in idx)
        mn = statistics.median(min(p[i] for p in P) for i in idx)
        md = statistics.median(statistics.median(p[i] for p in P) for i in idx)
        bs = ""
        if base:
            bi = [i for i, x in enumerate(base["freqs"]) if f <= x < f + blk]
            if bi:
                bs = f" base {statistics.median(base['passes'][0][i] for i in bi):6.1f}"
        bar = "#" * max(0, int((md + 115) / 2))
        print(f"{f/1e6:9.3f} med {md:6.1f} minmed {mn:6.1f} max {mx:6.1f}{bs} {bar}")
    f += blk
