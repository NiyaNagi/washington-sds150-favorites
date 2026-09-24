"""Attenuator test: is a raised floor / emission external or generated in the tinySA?

External signals keep the same displayed dBm when input attenuation is added
(until they hit the instrument floor, which rises by the attenuation).
Overload/intermod products made inside the analyzer drop by >= the attenuation.
"""
from paths import RF, FREQ_INDEX, CATALOG, RADIO_DATA, PROGRAMMED, HOME_QTH  # noqa: F401
import json, os, statistics
from tsa import TinySA

OUT = str(RF)
RANGES = [
    ("hf 14-30", 14e6, 30e6, 100),
    ("6m", 50e6, 54e6, 10),
    ("lowvhf 60-86", 60e6, 86e6, 30),
    ("2m", 144e6, 148e6, 10),
    ("air 118-137", 118e6, 137e6, 30),
    ("vhf 150-174", 150e6, 174e6, 30),
    ("240-310", 240e6, 310e6, 30),
]
PTS = [(147.455e6, 10), (49.15e6, 10), (250.0e6, 30), (240.1e6, 30), (120.0e6, 30), (144.375e6, 30)]

t = TinySA()
t.cmd("pause"); t.cmd("mode low input"); t.cmd("spur on")
res = {}
for name, lo, hi, rbw in RANGES:
    t.cmd(f"rbw {rbw}")
    row = {}
    for att in (0, 10, 20):
        t.cmd(f"attenuate {att}")
        r = t.scan(lo, hi, 290)
        v = sorted(x[1] for x in r)
        row[att] = (v[len(v) // 2], v[int(len(v) * 0.9)], v[-1])
    res[name] = row
    print(f"{name:14s} rbw{rbw:>3}: " + "  ".join(f"att{a:2d} med {m:6.1f} p90 {p:6.1f} max {x:6.1f}" for a, (m, p, x) in row.items()), flush=True)
for f, rbw in PTS:
    t.cmd(f"rbw {rbw}")
    row = {}
    for att in (0, 10, 20):
        t.cmd(f"attenuate {att}")
        r = t.scan(f - 100e3, f + 100e3, 81)
        row[att] = max(x[1] for x in r)
    print(f"point {f/1e6:9.3f} MHz rbw{rbw}: " + "  ".join(f"att{a} {v:6.1f}" for a, v in row.items()), flush=True)
    res[f"pt{f}"] = row
json.dump(res, open(os.path.join(OUT, "atten_test_smiley.json"), "w"))
t.cmd("attenuate auto"); t.cmd("rbw auto"); t.cmd("resume")
t.close()
