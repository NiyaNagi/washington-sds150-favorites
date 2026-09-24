"""Multi-pass tinySA survey. Usage: python survey.py <phase> [only-name ...]

Each sweep writes rf/<phase>__<name>.json with every pass kept, so
continuous carriers (present every pass) can be told from intermittent ones.
"""
from paths import RF, FREQ_INDEX, CATALOG, RADIO_DATA, PROGRAMMED, HOME_QTH  # noqa: F401
import json, os, sys, time
from tsa import TinySA

OUT = str(RF)

# (name, mode, start_hz, stop_hz, rbw_khz, step_hz, passes)
PHASES = {
    # antenna on HIGH, LOW port open
    "p1": [
        ("H_wide",   "high", 240e6, 500e6, 30, 25e3, 4),
        ("H_70cm",   "high", 420e6, 450e6, 10, 6.25e3, 3),
        ("H_uhf",    "high", 450e6, 470e6, 10, 6.25e3, 3),
        ("Lopen_vlf",  "low", 0.0, 1.0e6, 10, 2.5e3, 2),
        ("Lopen_wide", "low", 0.1e6, 350e6, 30, 25e3, 2),
        ("Lopen_hf",   "low", 0.1e6, 30e6, 10, 5e3, 1),
        ("Lopen_6m",   "low", 50e6, 54e6, 10, 5e3, 1),
        ("Lopen_air",  "low", 108e6, 137e6, 10, 8.33e3, 1),
        ("Lopen_2m",   "low", 144e6, 148e6, 10, 5e3, 1),
        ("Lopen_vhf",  "low", 148e6, 174e6, 10, 6.25e3, 1),
        ("Lopen_220",  "low", 219e6, 225e6, 10, 5e3, 1),
    ],
    # antenna on LOW, HIGH port open
    "p2": [
        ("L_vlf",   "low", 0.0, 1.0e6, 10, 2.5e3, 3),
        ("L_wide",  "low", 0.1e6, 350e6, 30, 25e3, 4),
        ("L_hf",    "low", 0.1e6, 30e6, 10, 5e3, 3),
        ("L_6m",    "low", 50e6, 54e6, 10, 5e3, 4),
        ("L_air",   "low", 108e6, 137e6, 10, 8.33e3, 3),
        ("L_2m",    "low", 144e6, 148e6, 10, 5e3, 5),
        ("L_vhf",   "low", 148e6, 174e6, 10, 6.25e3, 3),
        ("L_220",   "low", 219e6, 225e6, 10, 5e3, 4),
        ("Hopen_wide", "high", 240e6, 500e6, 30, 25e3, 2),
        ("Hopen_70cm", "high", 420e6, 470e6, 10, 6.25e3, 1),
    ],
    # EFHW feedline on LOW, HIGH port open
    "p3": [
        ("E_vlf",  "low", 0.0, 1.0e6, 10, 2.5e3, 3),
        ("E_hf",   "low", 0.1e6, 30e6, 10, 5e3, 4),
        ("E_hf_att10", "low", 0.1e6, 30e6, 10, 5e3, 1, 10),
        ("E_hf3k", "low", 1.8e6, 30e6, 3, 2.5e3, 1),
        ("E_lo",   "low", 30e6, 60e6, 10, 5e3, 3),
        ("E_wide", "low", 0.1e6, 350e6, 30, 25e3, 2),
    ],
}


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with open(os.path.join(OUT, "survey.log"), "a") as f:
        f.write(line + "\n")


def scan_exact(t, name, chunk):
    """Scan exactly these points; retry, then split the chunk if lines go missing."""
    for attempt in range(2):
        r = t.scan(chunk[0], chunk[-1], len(chunk))
        if len(r) == len(chunk):
            return [v for _, v in r]
        time.sleep(0.3)
        t.s.reset_input_buffer()
    # The firmware silently omits a few frequencies (e.g. 344.65 MHz in LOW).
    # Keep what came back and fill each gap from its nearest measured neighbour.
    got = {int(round(f)): v for f, v in r}
    keys = sorted(got)
    miss = [f for f in chunk if int(round(f)) not in got]
    SKIPPED.extend(miss)
    log(f"{name}: firmware omitted {len(miss)} pts near {miss[0]/1e6:.3f} MHz; filled from neighbours")
    out = []
    for f in chunk:
        k = int(round(f))
        if k in got:
            out.append(got[k])
        else:
            out.append(got[min(keys, key=lambda q: abs(q - k))])
    return out


SKIPPED = []


def run_sweep(t, phase, name, mode, start, stop, rbw, step, passes, att=0):
    t.cmd(f"mode {mode} input")
    actual_rbw = t.cmd(f"rbw {rbw}").strip() or t.cmd("rbw").strip().split("\n")[-1]
    actual_rbw = t.cmd("rbw").strip().split("\n")[-1]
    t.cmd(f"attenuate {att}")
    if mode == "low":
        t.cmd("spur on")
    n = int(round((stop - start) / step)) + 1
    freqs = [start + i * step for i in range(n)]
    rec = dict(phase=phase, name=name, mode=mode, start=start, stop=stop,
               rbw_req_khz=rbw, rbw_actual=actual_rbw, step=step, att=att,
               freqs=freqs, passes=[], pass_times=[])
    path = os.path.join(OUT, f"{phase}__{name}.json")
    for p in range(passes):
        t0 = time.time()
        vals = []
        for c in range(0, n, 290):
            chunk = freqs[c:c + 290]
            if len(chunk) == 1:
                chunk = [chunk[0] - step, chunk[0]]
                r = t.scan(chunk[0], chunk[-1], 2)
                vals.append(r[-1][1])
                continue
            vals.extend(scan_exact(t, name, chunk))
        rec["passes"].append(vals)
        rec["pass_times"].append([t0, time.time()])
        with open(path, "w") as f:
            json.dump(rec, f)
        log(f"{name} pass {p+1}/{passes} {n} pts {time.time()-t0:.0f}s rbw={actual_rbw}")


def main():
    phase = sys.argv[1]
    only = set(sys.argv[2:])
    t = TinySA()
    t.cmd("pause")
    log(f"start {phase} version={t.cmd('version').strip()}")
    try:
        for sw in PHASES[phase]:
            if only and sw[0] not in only:
                continue
            run_sweep(t, phase, *sw)
    finally:
        t.cmd("attenuate auto")
        t.cmd("rbw auto")
        t.cmd("mode low input")
        t.cmd("resume")
        t.close()
    log(f"done {phase}")


if __name__ == "__main__":
    main()
