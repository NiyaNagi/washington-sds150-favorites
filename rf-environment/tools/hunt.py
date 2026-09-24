"""Live RFI-hunt monitor for a basic tinySA.

    .venv-chirp\\Scripts\\python.exe rf-environment\\tools\\hunt.py --setup hf
    .venv-chirp\\Scripts\\python.exe rf-environment\\tools\\hunt.py --setup desk

Measures each fingerprint from the 2026-09-23 survey every few seconds, takes
the first --baseline cycles as the reference, then prints every later cycle as
a change from it. A drop of 6 dB or more is flagged DOWN: whatever you switched
off just before that line is (part of) that source. Every cycle is appended to
a CSV under .wasds150-home/rf-environment/ so the session can be reviewed.

Setups (see RFI-HUNT.md):
  hf    EFHW feedline on the LOW port.   HF noise fingerprints.
  desk  Smiley whip (69 cm) on the LOW port, on the desk.   VHF desk fingerprints.
  both  EFHW on LOW + whip on the HIGH port.   HF + the 240-300 MHz desk clocks.

Type a note and press Enter at any time (e.g. "monitor off"); it is written to
the CSV and echoed on the next line. Ctrl+C ends the run and restores the tinySA.
"""
import argparse, csv, math, os, queue, statistics, sys, threading, time
from paths import WORK
from tsa import TinySA

# name, port, kind, params, what it is
FP = {
    # HF (EFHW on LOW)
    "hf_hash_5M":  ("low", "zs", dict(f=5.15e6, rbw=30), "32.7 kHz SMPS hash, 120 Hz bursts (60m/80m)"),
    "hf_hash_10M": ("low", "zs", dict(f=10.75e6, rbw=30), "same source, 10.7 MHz hump (30m)"),
    "hf_hump_17M": ("low", "band", dict(lo=16.2e6, hi=17.0e6, rbw=10, stat="med"), "steady 16-17 MHz hump (17m)"),
    "hf_ref_13M":  ("low", "band", dict(lo=12.9e6, hi=13.5e6, rbw=10, stat="med"), "HF reference floor"),
    # desk VHF (whip on LOW)
    "birdie_147":  ("low", "peak", dict(lo=147.43e6, hi=147.48e6, rbw=3), "12.288 MHz x12 birdie on 147.450/147.4625"),
    "birdie_159":  ("low", "peak", dict(lo=159.72e6, hi=159.77e6, rbw=3), "12.288 MHz x13"),
    "comb_6m":     ("low", "comb", dict(lo=50.0e6, hi=51.0e6, rbw=10), "68.7 kHz SMPS comb across 6m"),
    "floor_2m":    ("low", "band", dict(lo=146.0e6, hi=146.4e6, rbw=10, stat="p20"), "2m noise floor"),
    "floor_lowvhf": ("low", "band", dict(lo=64e6, hi=80e6, rbw=30, stat="p20"), "60-86 MHz hash floor"),
    "hash_120M":   ("low", "band", dict(lo=119.8e6, hi=120.5e6, rbw=10, stat="max"), "12 MHz cluster on Sea-Tac tower/approach"),
    "hash_132M":   ("low", "band", dict(lo=132.0e6, hi=132.8e6, rbw=10, stat="max"), "12 MHz cluster on 132 MHz airband"),
    # desk clocks (whip on HIGH)
    "clk_240M":    ("high", "peak", dict(lo=239.95e6, hi=240.25e6, rbw=30), "12 MHz x20 (USB-like)"),
    "clk_250M":    ("high", "peak", dict(lo=249.9e6, hi=250.1e6, rbw=30), "25 MHz x10"),
    "clk_258M":    ("high", "peak", dict(lo=257.95e6, hi=258.15e6, rbw=10), "12.288 MHz x21"),
    "floor_290M":  ("high", "band", dict(lo=285e6, hi=295e6, rbw=30, stat="p20"), "240-340 MHz hash floor"),
}
SETUPS = {
    "hf": ["hf_hash_5M", "hf_hash_10M", "hf_hump_17M", "hf_ref_13M"],
    "desk": ["birdie_147", "birdie_159", "comb_6m", "floor_2m", "floor_lowvhf", "hash_120M", "hash_132M"],
    "both": ["hf_hash_5M", "hf_hash_10M", "hf_hump_17M", "hf_ref_13M", "clk_240M", "clk_250M", "clk_258M", "floor_290M"],
}


class Meter:
    def __init__(self, t):
        self.t = t
        self.state = {}

    def _set(self, mode, rbw):
        if self.state.get("mode") != mode:
            self.t.cmd(f"mode {mode} input")
            if mode == "low":
                self.t.cmd("spur on")
            self.t.cmd("attenuate 0")
            self.state = {"mode": mode}
        if self.state.get("rbw") != rbw:
            self.t.cmd(f"rbw {rbw}")
            self.state["rbw"] = rbw

    def measure(self, port, kind, p):
        self._set(port, p["rbw"])
        if kind == "zs":
            self.t.cmd("sweeptime 0.2")
            v = [x[1] for x in self.t.scan(p["f"], p["f"], 290)]
            self.t.cmd("sweeptime 0.003")
            med = statistics.median(v)
            burst = sum(1 for x in v if x > med + 6) / len(v)
            return med, f"bursts {burst*100:4.1f}%"
        if kind == "peak":
            v = [x[1] for x in self.t.scan(p["lo"], p["hi"], 101)]
            return max(v), ""
        if kind == "band":
            v = sorted(x[1] for x in self.t.scan(p["lo"], p["hi"], 290))
            s = p["stat"]
            val = v[len(v) // 2] if s == "med" else v[int(len(v) * 0.2)] if s == "p20" else v[-1]
            return val, ""
        if kind == "comb":
            v = sorted(x[1] for x in self.t.scan(p["lo"], p["hi"], 290))
            # comb strength = lines (p95) above the gaps (p20)
            return v[int(len(v) * 0.95)], f"lines {v[int(len(v)*0.95)] - v[int(len(v)*0.2)]:4.1f} dB over gaps"
        raise ValueError(kind)


def notes_reader(q):
    for line in sys.stdin:
        q.put(line.strip())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--setup", choices=SETUPS, required=True)
    ap.add_argument("--baseline", type=int, default=3, help="cycles averaged as the reference")
    ap.add_argument("--port", default="COM17")
    a = ap.parse_args()
    names = SETUPS[a.setup]
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / f"hunt-{a.setup}-{time.strftime('%Y%m%d-%H%M%S')}.csv"
    t = TinySA(a.port)
    t.cmd("pause")
    m = Meter(t)
    q = queue.Queue()
    threading.Thread(target=notes_reader, args=(q,), daemon=True).start()
    ref = {}
    hist = {n: [] for n in names}
    print(f"setup {a.setup}: {len(names)} fingerprints; logging to {path}")
    for n in names:
        print(f"  {n:13s} {FP[n][3]}")
    print(f"taking {a.baseline} baseline cycles with everything ON ...")
    cycle = 0
    try:
        with open(path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["time", "cycle", "note"] + names)
            while True:
                note = ""
                while not q.empty():
                    note = (note + " | " + q.get()).strip(" |")
                row, cells = {}, []
                for n in names:
                    port, kind, p, _ = FP[n]
                    val, extra = m.measure(port, kind, p)
                    row[n] = val
                    hist[n].append(val)
                cycle += 1
                w.writerow([time.strftime("%H:%M:%S"), cycle, note] + [f"{row[n]:.1f}" for n in names])
                fh.flush()
                if cycle == a.baseline:
                    ref = {n: statistics.mean(hist[n]) for n in names}
                    print("baseline: " + "  ".join(f"{n}={ref[n]:.1f}" for n in names))
                    print("now switch things off one at a time; type what you changed and press Enter.")
                    continue
                if not ref:
                    continue
                for n in names:
                    d = row[n] - ref[n]
                    flag = " DOWN" if d <= -6 else (" up" if d >= 6 else "")
                    cells.append(f"{n} {row[n]:6.1f} ({d:+5.1f}){flag}")
                if note:
                    print(f"--- note: {note}")
                print(time.strftime("%H:%M:%S ") + " | ".join(cells), flush=True)
    except KeyboardInterrupt:
        print(f"\nstopped; log in {path}")
    finally:
        t.cmd("sweeptime 0.003")
        t.cmd("attenuate auto"); t.cmd("rbw auto"); t.cmd("mode low input"); t.cmd("resume")
        t.close()


if __name__ == "__main__":
    main()
