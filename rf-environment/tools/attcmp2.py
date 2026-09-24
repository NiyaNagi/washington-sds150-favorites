"""Fair att0 vs att10: last att0 pass vs the att10 pass, per 1 MHz block (median and p90)."""
import json, statistics, sys

a = json.load(open(sys.argv[1]))
b = json.load(open(sys.argv[2]))
pa = a["passes"][-1]
pb = b["passes"][0]
F = a["freqs"]
blk = 1e6
f = 0.0
print("block MHz    att0 med  att10 med  diff |  att0 p90  att10 p90  diff")
while f < 30e6:
    idx = [i for i, x in enumerate(F) if f <= x < f + blk]
    if idx:
        va = sorted(pa[i] for i in idx)
        vb = sorted(pb[i] for i in idx)
        m = lambda v, q: v[int(len(v) * q)]
        print(f"{f/1e6:4.0f}-{(f+blk)/1e6:<4.0f}  {m(va,.5):8.1f} {m(vb,.5):9.1f} {m(va,.5)-m(vb,.5):5.1f} | {m(va,.9):8.1f} {m(vb,.9):9.1f} {m(va,.9)-m(vb,.9):5.1f}")
    f += blk
