"""Autocorrelation of a detrended sweep segment to reveal periodic spectral structure.
python acorr.py rf/x.json lo_mhz hi_mhz [maxlag_khz] [pass_index|max]
"""
import json, statistics, sys

r = json.load(open(sys.argv[1]))
lo, hi = float(sys.argv[2]) * 1e6, float(sys.argv[3]) * 1e6
maxlag = float(sys.argv[4]) * 1e3 if len(sys.argv) > 4 else 200e3
which = sys.argv[5] if len(sys.argv) > 5 else "max"
F = r["freqs"]
idx = [i for i, f in enumerate(F) if lo <= f <= hi]
if which == "max":
    v = [max(p[i] for p in r["passes"]) for i in idx]
else:
    v = [r["passes"][int(which)][i] for i in idx]
# detrend with a running mean of ~41 points
w = 20
d = []
for k in range(len(v)):
    seg = v[max(0, k - w):k + w + 1]
    d.append(v[k] - sum(seg) / len(seg))
m = statistics.mean(d)
d = [x - m for x in d]
var = sum(x * x for x in d)
step = r["step"]
out = []
for lag in range(1, int(maxlag / step) + 1):
    c = sum(d[k] * d[k + lag] for k in range(len(d) - lag)) / var
    out.append((lag * step, c))
best = sorted(out, key=lambda x: -x[1])[:8]
print(f"{len(idx)} pts, step {step/1e3:g} kHz; top autocorrelation lags:")
for lag, c in best:
    print(f"  {lag/1e3:8.2f} kHz  r={c:.3f}")
