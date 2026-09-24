"""Is each 2026-09-23 desk emission present on each antenna?

    .venv\\Scripts\\python.exe rf-environment\\tools\\fingerprints.py [survey_data_dir]

For every fingerprint and antenna, reports the peak of the per-point median
across passes in the fingerprint window (steady emitters only; intermittent
on-air traffic is excluded), the local floor (25th percentile of the median trace in a
wider reference window), and their difference. A fingerprint counts as
present at >= 6 dB over its floor. Levels are as measured at the tinySA; add
the feedline loss (lineloss.py) to refer them to the antenna.
"""
import json, statistics, sys
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[1] / "2026-09-23-survey" / "data"

# name, what, window (MHz), reference window (MHz), per-antenna sweep file
SWEEPS = {
    "wide": {"desk": "p2__L_wide.json", "efhw": "p3__E_wide.json", "sg7900": "p4__S_wide.json", "discone": "p6__D_wide.json"},
    "6m":   {"desk": "p2__L_6m.json", "efhw": "p3__E_lo.json", "sg7900": "p4__S_6m.json", "discone": "p6__D_6m.json"},
    "2m":   {"desk": "p2__L_2m.json", "sg7900": "p4__S_2m.json", "discone": "p6__D_2m.json"},
    "vhf":  {"desk": "p2__L_vhf.json", "sg7900": "p4__S_vhf.json", "discone": "p6__D_vhf.json"},
    "air":  {"desk": "p2__L_air.json", "sg7900": "p4__S_air.json", "discone": "p6__D_air.json"},
    "70cm": {"desk": "p1__H_70cm.json", "sg7900": "p5__SH_70cm.json", "discone": "p7__DH_70cm.json"},
    "hf":   {"desk": "p2__L_wide.json", "efhw": "p3__E_wide.json", "sg7900": "p4__S_wide.json", "discone": "p6__D_wide.json"},
}
FINGERPRINTS = [
    ("birdie 147.456", "12.288 MHz x12", "2m", (147.450, 147.462), (147.30, 147.62)),
    ("birdie 159.744", "12.288 MHz x13", "vhf", (159.735, 159.752), (159.50, 160.00)),
    ("birdie 442.368", "12.288 MHz x36", "70cm", (442.360, 442.376), (442.20, 442.34)),
    ("carrier 49.152", "12.288 MHz x4", "wide", (49.125, 49.175), (48.6, 49.9)),
    ("6m comb", "68.69 kHz SMPS (p95 vs p20 of 50-54 MHz)", "6m", None, None),
    ("cluster 120", "12 MHz x10 on airband", "air", (119.95, 120.45), (125.0, 127.0)),
    ("cluster 132", "12 MHz x11 on airband", "air", (132.0, 132.8), (125.0, 127.0)),
    ("cluster 144.4", "12 MHz x12, bottom of 2m", "2m", (144.30, 144.50), (146.0, 146.4)),
    ("cluster 240", "12 MHz x20 (strongest)", "wide", (239.95, 240.30), (236.0, 238.0)),
    ("carrier 250.0", "25 MHz x10", "wide", (249.95, 250.05), (246.0, 249.0)),
    ("carrier 258.05", "12.288 MHz x21", "wide", (258.00, 258.10), (255.0, 257.5)),
    ("HF hump 5 MHz", "32.7 kHz SMPS, 120 Hz bursts", "hf", (4.8, 5.3), (3.9, 4.4)),
    ("HF hump 16.7", "steady 16-17 MHz emitter", "hf", (16.2, 17.0), (13.0, 13.5)),
]


def load(data, name):
    p = data / name
    return json.load(open(p)) if p.exists() else None


def measure(rec, win, ref, hump=False):
    F = rec["freqs"]
    P = rec["passes"]
    wi = [i for i, f in enumerate(F) if win[0] * 1e6 <= f <= win[1] * 1e6]
    ri = [i for i, f in enumerate(F) if ref[0] * 1e6 <= f <= ref[1] * 1e6]
    if not wi or not ri:
        return None
    med = lambda i: statistics.median(p[i] for p in P)
    if hump:  # broadband: compare medians, not peaks
        pk = statistics.median(med(i) for i in wi)
    else:
        # the median across sweeps keeps steady emitters and drops on-air traffic
        # (max-hold let APRS bursts on 144.390 pose as the 144.4 MHz desk cluster)
        pk = max(med(i) for i in wi)
    fl = sorted(med(i) for i in ri)[len(ri) // 4]
    return pk, fl


def comb(rec):
    F = rec["freqs"]
    idx = [i for i, f in enumerate(F) if 50e6 <= f <= 54e6]
    v = sorted(statistics.median(p[i] for p in rec["passes"]) for i in idx)
    return v[int(len(v) * 0.95)], v[int(len(v) * 0.2)]


# Steady, distant reference transmitters every antenna hears. An emission's level minus the reference's cancels
# each antenna's gain: if (emission - reference) is much higher at the desk than outdoors, the source is near the desk.
REFERENCES = {
    "FM 97.3 (West Tiger)": ("wide", (97.2, 97.4)),
    "NOAA 162.55 (Cougar Mtn)": ("vhf", (162.52, 162.58)),
}
FP_REF = {"birdie 159.744": "NOAA 162.55 (Cougar Mtn)"}  # everything else uses FM 97.3


def ref_level(data, ant, ref):
    sweep, win = REFERENCES[ref]
    fn = SWEEPS[sweep].get(ant) or SWEEPS["wide"].get(ant)
    rec = load(data, fn) if fn else None
    if rec is None:
        return None
    F = rec["freqs"]
    idx = [i for i, f in enumerate(F) if win[0] * 1e6 <= f <= win[1] * 1e6]
    return max(statistics.median(p[i] for p in rec["passes"]) for i in idx) if idx else None


def main(data=None, quiet=False):
    data = data or (Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT)
    ants = ["desk", "efhw", "sg7900", "discone"]
    out = []
    say = (lambda *a: None) if quiet else print
    say(f"{'fingerprint':16s}" + "".join(f"{a:>18s}" for a in ants))
    for name, what, sweep, win, ref in FINGERPRINTS:
        cells, row = [], dict(name=name, what=what, ant={})
        refname = FP_REF.get(name, "FM 97.3 (West Tiger)")
        for a in ants:
            fn = SWEEPS[sweep].get(a)
            rec = load(data, fn) if fn else None
            if rec is None:
                cells.append(f"{'—':>18s}")
                continue
            m = comb(rec) if win is None else measure(rec, win, ref, hump=name.startswith("HF"))
            if m is None:
                cells.append(f"{'—':>18s}")
                continue
            pk, fl = m
            d = pk - fl
            rl = ref_level(data, a, refname)
            row["ant"][a] = dict(peak=pk, floor=fl, over=d, present=d >= 6, ref=rl,
                                 rel=(pk - rl) if (rl is not None and d >= 6) else None)
            cells.append(f"{pk:7.1f} ({d:+5.1f}){'*' if d >= 6 else ' '}")
        row["ref"] = refname
        out.append(row)
        say(f"{name:16s}" + "".join(f"{c:>18s}" for c in cells))
    say("peak dBm at the tinySA (dB over local floor); * = present (>= 6 dB)")
    say("\nrelative to a distant reference on the same antenna (emission minus reference, dB); only where present")
    say(f"{'fingerprint':16s}{'reference':>26s}" + "".join(f"{a:>10s}" for a in ants))
    for row in out:
        if row["name"].startswith("HF"):
            continue  # a VHF reference says nothing about an antenna's HF gain; compare HF humps by absolute level
        vals = [row["ant"].get(a, {}).get("rel") for a in ants]
        say(f"{row['name']:16s}{row['ref']:>26s}" + "".join(f"{v:10.1f}" if v is not None else f"{'—':>10s}" for v in vals))
    say("reference levels: " + "; ".join(
        f"{r}: " + ", ".join(f"{a} {ref_level(data, a, r):.1f}" for a in ants if ref_level(data, a, r) is not None)
        for r in REFERENCES))
    return out


if __name__ == "__main__":
    main()
