"""Persistent narrow carriers inside ham bands, with catalog/programmed overlap."""
from paths import RF, FREQ_INDEX, CATALOG, RADIO_DATA, PROGRAMMED, HOME_QTH  # noqa: F401
import json, sys
from analyze import analyze, BANDS, bands_for

HAM = [b for b in BANDS if "ham" in b[2] or b[2] == "CB"]
rec = json.load(open(sys.argv[1]))
thr = float(sys.argv[2]) if len(sys.argv) > 2 else 8
minpers = float(sys.argv[3]) if len(sys.argv) > 3 else 0.75
prog = json.load(open(PROGRAMMED))
ems, tr = analyze(rec, thr)
for e in ems:
    if e["pers"] < minpers or e["width"] > 20e3:
        continue
    if not any(lo <= e["f"] <= hi for lo, hi, _ in HAM):
        continue
    near = sorted({r for r, fs in prog.items() for f in fs if abs(f * 1e6 - e["f"]) <= 5e3})
    print(f"{e['f']/1e6:10.4f} MHz pk {e['peak']:6.1f} snr {e['snr']:5.1f} pers {e['pers']:.2f} spr {e['spread']:4.1f} "
          f"[{', '.join(bands_for(e['f']))}] {'programmed: ' + ','.join(near) if near else ''}")
