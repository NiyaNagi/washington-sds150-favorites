"""Fit a harmonic series n*F to the peaks of each pass (F = switching/clock frequency).

python harmfit.py rf/x.json Fmin_khz Fmax_khz [thr_db] [lo_mhz hi_mhz]
"""
import json, sys
from analyze import rolling_floor


def peaks(freqs, vals, thr):
    fl = rolling_floor(vals, 101)
    return [freqs[i] for i in range(1, len(vals) - 1)
            if vals[i] - fl[i] > thr and vals[i] >= vals[i - 1] and vals[i] >= vals[i + 1]]


def fit(pk, fmin, fmax, tol):
    best = (0, None)
    F = fmin
    while F <= fmax:
        hit = sum(1 for f in pk if abs(f - round(f / F) * F) <= tol)
        if hit > best[0]:
            best = (hit, F)
        F += 1.0  # 1 Hz grid
    return best


rec = json.load(open(sys.argv[1]))
fmin, fmax = float(sys.argv[2]) * 1e3, float(sys.argv[3]) * 1e3
thr = float(sys.argv[4]) if len(sys.argv) > 4 else 6
lo = float(sys.argv[5]) * 1e6 if len(sys.argv) > 5 else rec["start"]
hi = float(sys.argv[6]) * 1e6 if len(sys.argv) > 6 else rec["stop"]
idx = [i for i, f in enumerate(rec["freqs"]) if lo <= f <= hi]
fr = [rec["freqs"][i] for i in idx]
tol = rec["step"] * 0.6
for k, p in enumerate(rec["passes"]):
    v = [p[i] for i in idx]
    pk = peaks(fr, v, thr)
    n, F = fit(pk, fmin, fmax, tol)
    exp = (hi - lo) / F if F else 0
    print(f"pass {k}: {len(pk)} peaks; best F = {F/1e3:.3f} kHz explains {n} ({n/max(1,len(pk))*100:.0f}% of peaks, "
          f"{n/max(1,exp)*100:.0f}% of the {exp:.0f} expected harmonics); harmonic # ~{lo/F:.0f}-{hi/F:.0f}")
