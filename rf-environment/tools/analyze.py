"""Find emissions in survey sweeps. Usage: python analyze.py rf/p1__H_wide.json [--thr 6] [--baseline rf/xx.json]"""
from paths import RF, FREQ_INDEX, CATALOG, RADIO_DATA, PROGRAMMED, HOME_QTH  # noqa: F401
import argparse, bisect, json, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))

BANDS = [
    (0.1e6, 0.53e6, "LF/MF beacons"), (0.53e6, 1.7e6, "AM broadcast"),
    (1.8e6, 2.0e6, "160m ham"), (3.5e6, 4.0e6, "80m ham"), (5.33e6, 5.41e6, "60m ham"),
    (7.0e6, 7.3e6, "40m ham"), (10.1e6, 10.15e6, "30m ham"), (14.0e6, 14.35e6, "20m ham"),
    (18.068e6, 18.168e6, "17m ham"), (21.0e6, 21.45e6, "15m ham"), (24.89e6, 24.99e6, "12m ham"),
    (26.965e6, 27.405e6, "CB"), (28.0e6, 29.7e6, "10m ham"), (50e6, 54e6, "6m ham"),
    (54e6, 88e6, "VHF-lo TV RF2-6 / LMR"), (88e6, 108e6, "FM broadcast"), (108e6, 118e6, "Air nav (VOR/ILS)"),
    (118e6, 137e6, "Air voice"), (137e6, 138e6, "Wx sat"), (138e6, 144e6, "Federal/military"),
    (144e6, 148e6, "2m ham"), (148e6, 150.8e6, "Federal/military"), (151.82e6, 154.6e6, "VHF LMR (MURS 151.82-154.6 edges)"),
    (150.8e6, 162.0e6, "VHF LMR / public safety"), (162.4e6, 162.55e6, "NOAA WX"), (162e6, 174e6, "Federal / VHF LMR"),
    (174e6, 216e6, "VHF TV RF7-13"), (216e6, 222e6, "AMTS/LMR"), (222e6, 225e6, "1.25m ham"),
    (225e6, 400e6, "Military air"), (400e6, 420e6, "Federal"), (420e6, 450e6, "70cm ham"),
    (433.05e6, 434.79e6, "433 ISM (fobs, wx stations)"),
    (450e6, 462.5e6, "UHF LMR"), (462.55e6, 462.725e6, "GMRS/FRS main"), (467.5625e6, 467.725e6, "FRS/GMRS inputs"),
    (467.725e6, 470e6, "UHF LMR"), (470e6, 608e6, "UHF TV RF14-36"), (608e6, 614e6, "Radio astronomy/WMTS"),
    (617e6, 652e6, "LTE B71 downlink (T-Mobile)"), (652e6, 663e6, "B71 guard"), (663e6, 698e6, "LTE B71 uplink (phones)"),
    (699e6, 716e6, "LTE B12/17 uplink"), (716e6, 728e6, "LTE D/E block"), (729e6, 746e6, "LTE B12/17 downlink"),
    (746e6, 756e6, "LTE B13 downlink (Verizon)"), (758e6, 768e6, "LTE B14 downlink (FirstNet)"),
    (769e6, 775e6, "700 public safety (base)"), (777e6, 787e6, "LTE B13 uplink"), (788e6, 798e6, "LTE B14 uplink"),
    (799e6, 805e6, "700 public safety (mobile)"), (806e6, 824e6, "800 PS/SMR mobile"), (824e6, 849e6, "B5 uplink (phones)"),
    (851e6, 869e6, "800 PS/SMR base"), (869e6, 894e6, "B5/B26 downlink"), (896e6, 902e6, "900 SMR/broadband"),
    (902e6, 928e6, "33cm ham / 915 ISM (AMI meters, LoRa)"), (928e6, 929e6, "Fixed/MAS"), (929e6, 932e6, "Paging"),
    (932e6, 960e6, "Fixed/STL/paging/B8"),
]


def bands_for(f):
    return [b[2] for b in BANDS if b[0] <= f <= b[1]] or ["-"]


def load_index():
    p = str(FREQ_INDEX)
    rows = json.load(open(p))
    return rows, [r["f"] for r in rows]


def catalog_hits(idx, keys, fmhz, tol_mhz, n=3):
    rows = idx
    lo = bisect.bisect_left(keys, fmhz - tol_mhz)
    hi = bisect.bisect_right(keys, fmhz + tol_mhz)
    hits = rows[lo:hi]
    # prefer nearest, located, closest
    hits.sort(key=lambda r: (abs(r["f"] - fmhz), r["d"] if r["d"] is not None else 999))
    return hits[:n]


def rolling_floor(trace, win):
    n = len(trace)
    out = []
    half = win // 2
    for i in range(n):
        seg = sorted(trace[max(0, i - half):min(n, i + half + 1)])
        out.append(seg[len(seg) // 4])  # lower quartile
    return out


def analyze(rec, thr=6.0, baseline=None):
    fr = rec["freqs"]
    P = rec["passes"]
    n = len(fr)
    mx = [max(p[i] for p in P) for i in range(n)]
    mn = [min(p[i] for p in P) for i in range(n)]
    md = [statistics.median(p[i] for p in P) for i in range(n)]
    win = max(51, min(401, n // 20 * 2 + 1))
    floor = rolling_floor(md, win)
    above = [mx[i] - floor[i] > thr for i in range(n)]
    ems = []
    i = 0
    while i < n:
        if not above[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and above[j + 1]:
            j += 1
        k = max(range(i, j + 1), key=lambda q: mx[q])
        fl = floor[k]
        pers = sum(1 for p in P if p[k] - fl > thr) / len(P)
        ems.append(dict(f=fr[k], lo=fr[i], hi=fr[j], width=fr[j] - fr[i] + rec["step"],
                        peak=mx[k], minv=mn[k], med=md[k], floor=fl, snr=mx[k] - fl, pers=pers,
                        spread=mx[k] - mn[k]))
        i = j + 1
    if baseline:
        bf, bmx = baseline["freqs"], [max(p[q] for p in baseline["passes"]) for q in range(len(baseline["freqs"]))]
        bfl = rolling_floor([statistics.median(p[q] for p in baseline["passes"]) for q in range(len(bf))], 101)
        for e in ems:
            q = bisect.bisect_left(bf, e["f"])
            cand = [c for c in (q - 2, q - 1, q, q + 1, q + 2) if 0 <= c < len(bf) and abs(bf[c] - e["f"]) <= max(rec["step"], baseline["step"]) * 1.5]
            if cand:
                c = max(cand, key=lambda c: bmx[c])
                e["base_snr"] = bmx[c] - bfl[c]
    return ems, dict(mx=mx, mn=mn, md=md, floor=floor)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--thr", type=float, default=6.0)
    ap.add_argument("--baseline")
    ap.add_argument("--min-snr", type=float, default=0)
    ap.add_argument("--top", type=int, default=0)
    a = ap.parse_args()
    rec = json.load(open(a.path))
    base = json.load(open(a.baseline)) if a.baseline else None
    ems, tr = analyze(rec, a.thr, base)
    idx, keys = load_index()
    fl = sorted(tr["floor"])
    print(f"# {rec['name']} {rec['mode']} {rec['start']/1e6:.3f}-{rec['stop']/1e6:.3f} MHz  rbw={rec['rbw_actual']} step={rec['step']/1e3:g}k passes={len(rec['passes'])}")
    print(f"# floor median {fl[len(fl)//2]:.1f} dBm (range {fl[0]:.1f}..{fl[-1]:.1f}); {len(ems)} emissions > floor+{a.thr}")
    sel = [e for e in ems if e["snr"] >= a.min_snr]
    if a.top:
        sel = sorted(sel, key=lambda e: -e["snr"])[:a.top]
        sel.sort(key=lambda e: e["f"])
    for e in sel:
        tol = max(rec["step"], 12.5e3) / 1e6
        hits = catalog_hits(idx, keys, e["f"] / 1e6, tol) if e["width"] < 200e3 else []
        hs = "; ".join(f"{h['f']:.4f} {h['label'][:60]}" + (f" ({h['d']}mi)" if h['d'] is not None else "") for h in hits)
        b = f" base{e['base_snr']:+.0f}" if "base_snr" in e else ""
        print(f"{e['f']/1e6:10.4f} MHz  pk {e['peak']:6.1f}  snr {e['snr']:5.1f}  w {e['width']/1e3:7.1f}k  pers {e['pers']:.2f}  spr {e['spread']:4.1f}{b}  [{', '.join(bands_for(e['f']))}]  {hs}")


if __name__ == "__main__":
    main()
