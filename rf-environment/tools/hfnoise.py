"""HF external-noise estimate per band vs ITU-R P.372 man-made noise categories.

python hfnoise.py rf/p3__E_hf.json rf/p1__Lopen_hf.json
Floor = 20th percentile (over the band) of the per-point minimum across passes,
so carriers and intermittent signals are excluded. The instrument's own noise
(open-port baseline) is subtracted in linear power. Fa = N[dBm/Hz] + 174.
No antenna-efficiency / feedline correction is applied, so Fa is a LOWER bound.
"""
import json, math, re, sys

BANDS = [("160m", 1.8, 2.0), ("80m", 3.5, 4.0), ("60m", 5.33, 5.41), ("40m", 7.0, 7.3),
         ("30m", 10.1, 10.15), ("20m", 14.0, 14.35), ("17m", 18.068, 18.168), ("15m", 21.0, 21.45),
         ("12m", 24.89, 24.99), ("CB", 26.965, 27.405), ("10m", 28.0, 29.7)]
ITU = [("city", 76.8, 27.7), ("residential", 72.5, 27.7), ("rural", 67.2, 27.7), ("quiet rural", 53.6, 28.6)]
GAL = (52.0, 23.0)


def rbw_hz(s):
    m = re.match(r"([\d.]+)\s*kHz", s)
    return float(m.group(1)) * 1e3


def band_floor(rec, lo, hi):
    idx = [i for i, f in enumerate(rec["freqs"]) if lo * 1e6 <= f <= hi * 1e6]
    mins = sorted(min(p[i] for p in rec["passes"]) for i in idx)
    return mins[int(len(mins) * 0.2)], len(idx)


ant = json.load(open(sys.argv[1]))
base = json.load(open(sys.argv[2]))
rbw = rbw_hz(ant["rbw_actual"])
print(f"RBW {rbw/1e3:.1f} kHz; Fa is a lower bound (no antenna/feedline loss correction)")
print(f"{'band':6s} {'ant dBm':>8s} {'inst dBm':>8s} {'ext dBm':>8s} {'dBm/Hz':>8s} {'Fa dB':>6s}  " +
      "  ".join(f"{n[:5]:>5s}" for n, _, _ in ITU) + "  gal   verdict")
for name, lo, hi in BANDS:
    a, n = band_floor(ant, lo, hi)
    b, _ = band_floor(base, lo, hi)
    pa, pb = 10 ** (a / 10), 10 ** (b / 10)
    if pa <= pb * 1.26:  # <1 dB above instrument
        print(f"{name:6s} {a:8.1f} {b:8.1f}    below instrument floor")
        continue
    ext = 10 * math.log10(pa - pb)
    nhz = ext - 10 * math.log10(rbw)
    fa = nhz + 174
    fc = math.sqrt(lo * hi)
    ref = [c - d * math.log10(fc) for _, c, d in ITU]
    gal = GAL[0] - GAL[1] * math.log10(fc)
    # verdict: nearest category at or below the measurement
    above = [(ITU[k][0], fa - ref[k]) for k in range(len(ITU))]
    cat = next((nm for nm, dlt in above if dlt >= -3), "below quiet rural")
    print(f"{name:6s} {a:8.1f} {b:8.1f} {ext:8.1f} {nhz:8.1f} {fa:6.1f}  " +
          "  ".join(f"{r:5.1f}" for r in ref) + f"  {gal:4.1f}  ~{cat} ({fa - ref[1]:+.1f} dB vs residential)")
