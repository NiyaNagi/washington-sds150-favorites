"""Zero-span time captures to characterise impulse / periodic noise.

python zerospan.py <tag> <mode> <rbw_khz> <sweeptime_s> <captures> <f_mhz> [<f_mhz> ...]
For each frequency: <captures> records of 290 samples spread over sweeptime.
Reports burst statistics and the strongest repetition frequencies (DFT of the
envelope in linear power), e.g. 60/120 Hz mains, or switching-supply rates.
"""
from paths import RF, FREQ_INDEX, CATALOG, RADIO_DATA, PROGRAMMED, HOME_QTH  # noqa: F401
import cmath, json, math, os, statistics, sys, time
from tsa import TinySA

OUT = str(RF)


def spectrum(x, dt, fmax):
    n = len(x)
    m = statistics.mean(x)
    y = [v - m for v in x]
    res = []
    df = 1 / (n * dt)
    for k in range(1, n // 2):
        f = k * df
        if f > fmax:
            break
        s = sum(y[i] * cmath.exp(-2j * math.pi * k * i / n) for i in range(n))
        res.append((f, abs(s) / n))
    return res


def main():
    tag, mode, rbw, st, caps = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), int(sys.argv[5])
    freqs = [float(a) for a in sys.argv[6:]]
    t = TinySA()
    t.cmd("pause")
    t.cmd(f"mode {mode} input")
    t.cmd(f"rbw {rbw}")
    t.cmd("attenuate 0")
    t.cmd(f"sweeptime {st}")
    res = dict(tag=tag, mode=mode, rbw=t.cmd("rbw").strip().split("\n")[-1], sweeptime=st, data=[])
    try:
        for f in freqs:
            recs = []
            for c in range(caps):
                r = t.scan(f * 1e6, f * 1e6, 290)
                recs.append([v for _, v in r])
            actual = t.cmd("sweeptime").strip().split("\n")[-1]
            allv = [v for rec in recs for v in rec]
            srt = sorted(allv)
            floor = srt[len(srt) // 2]
            p99 = srt[int(len(srt) * 0.99)]
            burst = sum(1 for v in allv if v > floor + 6) / len(allv)
            a = actual.strip()
            secs = float(a[:-2]) / 1000 if a.endswith("ms") else float(a.rstrip("s"))
            dt = secs / 290
            # average the envelope spectrum (linear power) over captures
            acc = {}
            for rec in recs:
                lin = [10 ** (v / 10) for v in rec]
                for fr, a in spectrum(lin, dt, 2000):
                    acc.setdefault(round(fr, 1), []).append(a)
            spec = sorted(((fr, statistics.mean(a)) for fr, a in acc.items()), key=lambda x: -x[1])
            meanlin = statistics.mean(10 ** (v / 10) for v in allv)
            top = [(fr, round(a / meanlin, 3)) for fr, a in spec[:5]]
            res["data"].append(dict(f=f, actual_sweeptime=actual, records=recs, floor=floor, p99=p99,
                                    max=srt[-1], burst_frac=burst, top_rates=top))
            print(f"{f:10.4f} MHz  median {floor:6.1f}  p99 {p99:6.1f}  max {srt[-1]:6.1f}  >+6dB {burst*100:5.1f}%  "
                  f"rates(Hz,rel) {top}  [{actual}]", flush=True)
    finally:
        json.dump(res, open(os.path.join(OUT, f"zs__{tag}.json"), "w"))
        t.cmd("sweeptime 0.003")
        t.cmd("rbw auto"); t.cmd("attenuate auto"); t.cmd("mode low input"); t.cmd("resume")
        t.close()


if __name__ == "__main__":
    main()
