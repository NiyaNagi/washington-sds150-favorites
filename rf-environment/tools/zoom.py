"""Narrow high-resolution looks at candidate frequencies.

python zoom.py <tag> <mode> <center_mhz> <span_khz> <rbw_khz> <passes> [<center> <span> ...]
Writes rf/zoom__<tag>.json with every pass and timestamps.
"""
from paths import RF, FREQ_INDEX, CATALOG, RADIO_DATA, PROGRAMMED, HOME_QTH  # noqa: F401
import json, os, sys, time
from tsa import TinySA

OUT = str(RF)


def main():
    tag, mode = sys.argv[1], sys.argv[2]
    rbw, passes = sys.argv[5], int(sys.argv[6])
    targets = [(float(sys.argv[3]), float(sys.argv[4]))]
    rest = sys.argv[7:]
    for k in range(0, len(rest), 2):
        targets.append((float(rest[k]), float(rest[k + 1])))
    t = TinySA()
    t.cmd("pause")
    t.cmd(f"mode {mode} input")
    t.cmd(f"rbw {rbw}")
    actual = t.cmd("rbw").strip().split("\n")[-1]
    t.cmd("attenuate 0")
    if mode == "low":
        t.cmd("spur on")
    res = dict(tag=tag, mode=mode, rbw=actual, targets=[])
    try:
        for c, span in targets:
            lo, hi = c * 1e6 - span * 500, c * 1e6 + span * 500
            tr = dict(center=c, span_khz=span, freqs=None, passes=[], times=[])
            for p in range(passes):
                r = t.scan(lo, hi, 290)
                tr["freqs"] = [f for f, _ in r]
                tr["passes"].append([v for _, v in r])
                tr["times"].append(time.time())
            res["targets"].append(tr)
            pk = max(range(290), key=lambda i: max(p[i] for p in tr["passes"]))
            print(f"{c:.4f} MHz span {span}k: peak {max(p[pk] for p in tr['passes']):.1f} @ {tr['freqs'][pk]/1e6:.5f}", flush=True)
    finally:
        json.dump(res, open(os.path.join(OUT, f"zoom__{tag}.json"), "w"))
        t.cmd("rbw auto"); t.cmd("attenuate auto"); t.cmd("mode low input"); t.cmd("resume")
        t.close()


if __name__ == "__main__":
    main()
