"""Find evenly spaced combs among persistent narrow emissions.

python comb.py rf/x.json [--thr 6] [--minpers 0.6] [--maxwidth 60e3] [--exclude lo-hi,...]
A comb is a spacing D and offset o such that many peaks sit at o + k*D.
o == 0 means a harmonic series of a D-Hz fundamental (clock / oscillator);
o != 0 with a small D is typical of switch-mode supplies.
"""
import argparse, json
from analyze import analyze


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--thr", type=float, default=6)
    ap.add_argument("--minpers", type=float, default=0.6)
    ap.add_argument("--maxwidth", type=float, default=60e3)
    ap.add_argument("--exclude", default="")
    ap.add_argument("--mind", type=float, default=0)
    a = ap.parse_args()
    rec = json.load(open(a.path))
    ems, _ = analyze(rec, a.thr)
    excl = [tuple(float(x) * 1e6 for x in r.split("-")) for r in a.exclude.split(",") if r]
    pk = [e for e in ems if e["pers"] >= a.minpers and e["width"] <= a.maxwidth
          and not any(lo <= e["f"] <= hi for lo, hi in excl)]
    fs = sorted(e["f"] for e in pk)
    step = rec["step"]
    tol = step * 1.01
    print(f"{len(fs)} persistent narrow peaks considered")
    cands = set()
    for i in range(len(fs)):
        for j in range(i + 1, min(len(fs), i + 25)):
            d = fs[j] - fs[i]
            if d > max(a.mind, 3 * step):
                for m in (1, 2, 3):
                    cands.add(round(d / m / step) * step)
    results = []
    for d in cands:
        if d <= max(a.mind, 3 * step):
            continue
        # best offset: histogram of f mod d
        buckets = {}
        for f in fs:
            r = f % d
            key = round(r / step)
            buckets.setdefault(key, []).append(f)
        best = []
        for key, members in buckets.items():
            grp = [f for f in fs if min(abs((f % d) - key * step), d - abs((f % d) - key * step)) <= tol]
            if len(grp) > len(best):
                best, off = grp, key * step
        span = (max(best) - min(best)) / d + 1 if best else 0
        if len(best) >= 4:
            results.append((len(best) / max(span, 1), len(best), d, off, best))
    # rank by member count, favour dense combs (fill ratio)
    results.sort(key=lambda r: (-(r[1] * min(1, r[0] * 1.5)), r[2]))
    shown = []
    for fill, n, d, off, mem in results:
        if any(abs(d - s) < step * 1.5 or (d / s) % 1 < 0.02 for s in shown):
            continue
        shown.append(d)
        print(f"spacing {d/1e3:9.2f} kHz offset {off/1e3:8.2f} kHz: {n} peaks, fill {fill:.2f}  "
              f"{', '.join(f'{m/1e6:.3f}' for m in mem[:12])}{' ...' if n > 12 else ''}")
        if len(shown) >= 10:
            break


if __name__ == "__main__":
    main()
